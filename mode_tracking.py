import config_classes
import modetrack as mt

import socket_communicators as sc
import data_processors as procs
import time
import os
import color_printer as cp
import atexit

class ModeTrackBody(config_classes.ConfigTypes):

    def __init__(self, config_path):
        super(ModeTrackBody, self).__init__(config_path)
        
        self.print_green = cp.ColorPrinter("Green")
        self.print_purple = cp.ColorPrinter("Purple")
        self.print_blue = cp.ColorPrinter("Blue")
        self.print_red = cp.ColorPrinter("Red")
        
        nwa_sock = self.data_dict['nwa']
        
        nwa_points = self.data_dict['nwa_points']
        nwa_span = self.data_dict['nwa_span']
        nwa_power = self.data_dict['nwa_power']
        
        sa_sock = self.data_dict['sa']
        switch_sock = self.data_dict['switch']
        step_addr = self.addr_dict['step']
        
        self.nwa_comm = sc.NetworkAnalyzerComm(nwa_sock, nwa_points, nwa_span, nwa_power)
        self.sa_comm = sc.SignalAnalyzerComm(sa_sock)
        self.switch_comm = sc.SwitchComm(switch_sock)
        self.step_comm = sc.StepperMotorComm(step_addr)
        
        self.fitter = procs.LorentzianFitter()
        self.plotter = procs.Plotter()
        
        self.m_track = mt.ModeTrack()
        self.convertor = procs.Convertor()

        self.freq_window = self.data_dict['freq_window']  # Frequency window used for identify peaks specified in MHz
        self.sa_span = self.data_dict['sa_span']  # MHz
        self.sa_averages = self.data_dict['sa_averages']  # total number of averages to take, Max is
        self.fft_length = self.data_dict['fft_length']  # Number of IQ points to generate spectrum, Max is

        self.fitted_q = 0.0
        self.fitted_center_freq = 0.0
        self.fitted_height = 0.0

        # container for formatted data triples
        self.formatted_points = []
        # position of the mode of desire in frequency space
        self.mode_of_desire = 0.0
        self.iteration = 0

    def retract_cavity(self):
        
        tune_length = float(self.data_dict['len_of_tune'])
        self.step_comm.reset_cavity(tune_length)

    def prequel(self):
        self.switch_comm.switch_to_network_analyzer()


    def get_data_nwa(self):
        total_data_str = ''
        total_data_str.extend(self.nwa_comm.collect_data(self.nominal_centers))
        
        return total_data_str


    def format_points(self, raw_nwa_data):

        total_iterations = self.num_of_iters
        start_length = float(self.data_dict['start_length'])
        current_iteration = float(self.iteration)
        tune_length = float(self.data_dict['len_of_tune'])
        
        max_frequency = self.nominal_centers[-1] + self.nwa_span / 2
        min_frequency = self.nominal_centers[0] - self.nwa_span / 2

        cavity_length = start_length + (current_iteration * tune_length / (total_iterations))
        self.print_yellow("Current cavity length: " + str(cavity_length))

#         del self.formatted_points[:]

        return self.formatter.make_plot_points(self.raw_data, \
                                                                 self.cavity_length, \
                                                                  min_frequency, \
                                                                   max_frequency)

#         del self.raw_nwa_data[:]

    def set_bg_data(self, blank_data):
        
        bg_str = ''
        for triple in blank_data:
            temp_str = str(triple)
            # Create translation table.
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            temp_str = temp_str.translate(trans_table)
            bg_str += temp_str + "\n"
        
        # need to remove list item in list since it will be a blank line
        self.green_printer("Background data sent to sub-process.")
        self.m_track.SetBackground(bg_str[:-1])

    def find_minima_peak(self, formatted_points):
        data_str = ''
        
        for triple in formatted_points:
            temp_str = str(triple)
            # Create translation table.
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            temp_str = temp_str.translate(trans_table)
            data_str += temp_str + "\n"
        
        return self.m_track.GetPeaksBiLat(data_str[:-1], 0)

    def next_iteration(self):

        len_of_tune = self.data_dict['len_of_tune']
        revs = int(self.data_dict['revs_per_iter'])

        self.iteration += 1

        iters = self.iteration
        num_of_iters = self.num_of_iters

        self.step_comm.walk_loop(len_of_tune, revs, iters, num_of_iters)
        
    def __recenter_peak(self, power_list):
        
        total_iterations = self.num_of_iters
        start_length = float(self.data_dict['start_length'])
        current_iteration = float(self.iteration)
        tune_length = float(self.data_dict['len_of_tune'])
        
        cavity_length = start_length + (current_iteration * tune_length / (total_iterations))
        trans_window_str = self.convertor.power_list_to_str(power_list, self.mode_of_desire, self.freq_window, cavity_length)
        
        return self.m_track.GetMaxPeak(trans_window_str[:-1])

    def check_peak(self, mode_of_desire):
        
        nwa_span = self.nwa_span
        freq_window = self.freq_window

        if (mode_of_desire == 0.0):
            self.print_red("Mode of desire not found.")
            return

        self.print_purple("Checking peak.")
        
        #since we identified the position of our mode using reflection measurements
        #we need to switch to transmission to find the 'real' position of the mode
        self.switch_comm.switch_to_transmission()

#         funcs.set_freq_window(nwa_sock, self.mode_of_desire , freq_window)
#         initial_trans_window = funcs.take_data_single(nwa_sock)
#         initial_trans_window = funcs.str_to_power_list(initial_trans_window)
        
        self.nwa_comm.set_freq_window(mode_of_desire , freq_window)
        initial_window = self.nwa_comm.take_data_single()
        initial_window = self.convertor.str_list_to_power_list(initial_window)
        
        self.plotter(initial_window, self.mode_of_desire, freq_window)

#         funcs.plot_freq_window(initial_trans_window, self.mode_of_desire, freq_window)

        new_mode_of_desire = self.__recenter_peak(initial_window)

        final_window = self.nwa_comm.take_data_single()
        final_window = self.convertor.str_list_to_power_list(final_window)
        
        self.plotter(initial_window, self.mode_of_desire, freq_window)

#         funcs.plot_freq_window(final_trans_window, self.mode_of_desire, freq_window)

        self.fitter(final_window, mode_of_desire, freq_window)

#         funcs.fit_lorentzian(final_trans_window, self.mode_of_desire, freq_window)

        self.nwa_comm.set_freq_window(new_mode_of_desire , nwa_span)
#         funcs.set_freq_window(nwa_sock, self.mode_of_desire , nwa_span)

        # return to reflection measurements
        self.switch_comm.switch_to_reflection()
        
        return new_mode_of_desire
    
    def get_data_sa(self, mode_of_desire):
        
        self.sa_comm.set_signal_analyzer(mode_of_desire, fft_length = 1024, freq_span = 10, num_averages = 25)
        return self.sa_comm.take_data_signal_analyzer()
        

class ModeTrackProgram(ModeTrackBody):

    def __init__(self, config_path):
        super(ModeTrackProgram, self).__init__(config_path)
        atexit.register(self.panic_cleanup)
        
    def find_mode_of_desire_reflection(self):
        nwa_data = self.get_data_nwa()
        formatted_points = self.format_points(nwa_data)
        mode_of_desire = self.find_minima_peak(formatted_points)
        
        if (mode_of_desire <= 0):
            return -1
        else:
            return mode_of_desire
        
    def find_mode_of_desire_transmission(self, mode_of_desire):
        mode_of_desire = self.check_peak(mode_of_desire)
        
        if (mode_of_desire <= 0):
            return -1
        else:
            return mode_of_desire
        
    def take_data(self, mode_of_desire):
        sa_data = self.get_data_sa(mode_of_desire)
        return self.format_points(sa_data)
        
    def set_background(self):
        nwa_data = self.get_data_nwa()
        formatted_points = self.format_points(nwa_data)
        self.set_bg_data(formatted_points)
        
    def generate_save_file_name(self, idx):
        # Generate file name time-stamp in the form dd.mm.yyyy
        time_stamp = time.strftime("%d.%m.%Y")
        # concatenate the base save-file path with the date-time string to form the name of all necessary .csv files
        save_path = self.data_dict['save_file_path']
        return os.path.join(save_path, time_stamp + str(idx) + 'SA.csv')
        
    def save_data(self, formatted_data, idx):
        
        path = self.generate_save_file_name(idx)
        
        out_file=open(path,'a')
        
        for item in formatted_data:
            out_str=str(item)
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            out_str = out_str.translate(trans_table)
        
            print(out_str, end="\n", file=out_file)
        
        out_str="Wrote data to "+path
        
        out_file.close()
        

    def program(self):

        self.prequel()
        self.set_background()
        self.next_iteration()

        #start indexing at one since we used our first iteration to capture
        #background data
        for x in range(1, self.num_of_iters):
            
            mode_of_desire = self.find_mode_of_desire_reflection()
            break if (mode_of_desire <= 0 ) else pass
            mode_of_desire = self.find_mode_of_desire_transmission(mode_of_desire)
            break if (mode_of_desire <= 0 ) else pass
            
            data = self.get_data_sa(mode_of_desire)
            self.save_data(data, x)
            
            # subprocess.Popen("~/workspace/Electric-Tiger/Python_Files/MM-plot.m",shell=True)

            self.next_iteration()

        self.retract_cavity()
        self.close_all()

    def panic_cleanup(self):

        self.panic_reset_cavity()
        self.close_all()
