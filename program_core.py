import config_classes

import socket_communicators as sc
import data_processors as procs
import color_printer as cp

import time

class ProgramCore(config_classes.ConfigTypes):

    def __init__(self, config_path):
        super(ProgramCore, self).__init__(config_path)
        
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
        
        self.initial_length = float(self.data_dict['intial_length'])
        
        self.nwa_span = int(self.data_dict['nwa_span'])
            
        self.iteration = 0

    def retract_cavity(self):
        
        tune_length = float(self.data_dict['len_of_tune'])
        self.step_comm.reset_cavity(tune_length)
        
    def __move_to_start_cavity_length(self):
        current_length = float(self.ardu_comm.get_cavity_length())
        self.step_comm.set_to_initial_length(self.start_length, current_length)
        
    def __move_to_initial_cavity_length(self):
        current_length = float(self.ardu_comm.get_cavity_length())
        self.step_comm.set_to_initial_length(self.initial_length, current_length)
        
    def rapid_traverse(self):
        self.__move_to_initial_cavity_length()
        
    def prequel_transmission(self):
        self.switch_comm.switch_to_network_analyzer()
        self.switch_comm.switch_to_transmission()
        self.__move_to_start_cavity_length()
         
    def prequel_reflection(self):
        self.switch_comm.switch_to_network_analyzer()
        self.switch_comm.switch_to_reflection()
        self.__move_to_start_cavity_length()


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

        return self.convertor.make_plot_points(raw_data, cavity_length, min_frequency, max_frequency)
    
    def print_status_info(self):
        cavity_length = self.ardu_comm.get_cavity_length()
        self.print_blue("Current cavity length: " + str(cavity_length))
        
        time_stamp = time.strftime("%H:%M:%S")
        self.print_blue("Current time: " + str(time_stamp))

    def next_iteration(self):

        len_of_tune = self.data_dict['len_of_tune']
        revs = float(self.data_dict['revs_per_iter'])

        self.iteration += 1

        iters = self.iteration
        num_of_iters = self.num_of_iters
        
        self.step_comm.walk_loop(len_of_tune, revs, iters, num_of_iters)
