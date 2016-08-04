import config_classes

import socket_communicators as sc
import data_processors as procs
import os
import color_printer as cp
import atexit
import subprocess

class ModeMapBody(config_classes.ConfigTypes):

    def __init__(self, config_path, map_type):
        super(ModeMapBody, self).__init__(config_path, map_type)
        
        self.print_green = cp.ColorPrinter("Green")
        self.print_purple = cp.ColorPrinter("Purple")
        self.print_blue = cp.ColorPrinter("Blue")
        self.print_red = cp.ColorPrinter("Red")
        self.print_yellow = cp.ColorPrinter("Yellow")
        
        nwa_sock = self.sock_dict['nwa']
        
        nwa_points = self.data_dict['nwa_points']
        nwa_span = self.data_dict['nwa_span']
        nwa_power = self.data_dict['nwa_power']
        
        sa_sock = self.sock_dict['sa']
        switch_sock = self.sock_dict['switch']
        ardu_sock = self.sock_dict['ardu']
        step_addr = self.addr_dict['step']
        
        self.nwa_comm = sc.NetworkAnalyzerComm(nwa_sock, nwa_points, nwa_span, nwa_power)
        self.sa_comm = sc.SignalAnalyzerComm(sa_sock)
        self.switch_comm = sc.SwitchComm(switch_sock)
        self.ardu_comm = sc.ArduComm(ardu_sock)
        self.step_comm = sc.StepperMotorComm(step_addr)
        
        self.convertor = procs.Convertor()

        self.nominal_centers = self.data_dict['nominal_centers']
        self.num_of_iters = int(self.data_dict['num_of_iters'])
        self.start_length = float(self.data_dict['start_length'])
        self.nwa_span = int(self.data_dict['nwa_span'])

        if (map_type == "R"):
            self.file_name = self.data_dict['file_nameR']
        else:
            self.file_name = self.data_dict['file_name']
            
        self.iteration = 0

    def retract_cavity(self):
        
        tune_length = float(self.data_dict['len_of_tune'])
        self.step_comm.reset_cavity(tune_length)
        
    def __move_to_initial_cavity_length(self):
        current_length = float(self.ardu_comm.get_cavity_length())
        self.step_comm.set_to_initial_length(self.start_length, current_length)

    def prequel_transmission(self):
        self.switch_comm.switch_to_network_analyzer()
        self.switch_comm.switch_to_transmission()
        self.__move_to_initial_cavity_length()
         
    def prequel_reflection(self):
        self.switch_comm.switch_to_network_analyzer()
        self.switch_comm.switch_to_reflection()
        self.__move_to_initial_cavity_length()


    def get_data_nwa(self):
        total_data_list = []
        total_data_list.extend(self.nwa_comm.collect_data(self.nominal_centers))
        
        return total_data_list


    def format_points(self, raw_data):

        nwa_span = float(self.data_dict['nwa_span'])
        last_center = float(self.nominal_centers[-1])
        first_center = float(self.nominal_centers[0])
        
        max_frequency = last_center + nwa_span / 2
        min_frequency = first_center - nwa_span / 2

        cavity_length = self.ardu_comm.get_cavity_length()
        self.print_yellow("Current cavity length: " + str(cavity_length))

        return self.convertor.make_plot_points(raw_data, cavity_length, min_frequency, max_frequency)

    def next_iteration(self):

        len_of_tune = self.data_dict['len_of_tune']
        revs = int(self.data_dict['revs_per_iter'])

        self.iteration += 1

        iters = self.iteration
        num_of_iters = self.num_of_iters
        
        self.step_comm.walk_loop(len_of_tune, revs, iters, num_of_iters)
        
class ModeMapProgram(ModeMapBody):

    def __init__(self, config_path, map_type):
        super(ModeMapProgram, self).__init__(config_path, map_type)
        self.map_type = map_type
        
        atexit.register(self.panic_cleanup)
    
    def transfer_mode_map(self):
        
        path = self.file_name
        
        command = "./data/transfer_mode_map.sh " + path
        subprocess.Popen(command, shell=True)
        
    def transfer_power_spec(self, power_spec):
        
        power_list = self.convertor.str_list_to_power_list(power_spec)
        
        path = os.path.join(os.getcwd() + '/data/current_power_spectrum.csv')
        out_file = open(path, 'w+')
        
        out_str = ''
        for power in power_list:
            out_str += str(power) + "\n"
            
        print(out_str, end="", file=out_file)

        out_file.close() 
        
        command = "./data/transfer_power_spec.sh " + path
        subprocess.Popen(command, shell=True)
        
        
    def save_data(self, formatted_data):
        
        path = self.file_name
        
        out_file = open(path, 'a')
        
        for item in formatted_data:
            out_str = str(item)
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            out_str = out_str.translate(trans_table)
        
            print(out_str, end="\n", file=out_file)
        
        out_str = "Wrote data to " + path
        
        out_file.close()      
        
    def get_nwa_data(self):
        nwa_data = self.get_data_nwa()
        self.transfer_power_spec(nwa_data)
        
        formatted_points = self.format_points(nwa_data)
        self.save_data(formatted_points)
        self.transfer_mode_map()    

    def program(self):

        if ( self.map_type == 'R'):
            self.prequel_reflection()
        else:
            self.prequel_transmission()

        for x in range(0, self.num_of_iters):
            
            self.get_nwa_data()
            self.next_iteration()

        self.close_all()

    def panic_cleanup(self):

        current_iteration = self.iteration
        revs_per_iters = int(self.data_dict['revs_per_iter'])
        self.step_comm.panic_reset_cavity(current_iteration, revs_per_iters)
        self.close_all()



