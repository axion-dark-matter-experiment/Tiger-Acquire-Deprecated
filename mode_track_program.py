import program_core as core

import atexit
import subprocess
import os
import data_processors as procs
import modetrack as mt
import time

class ModeTracker(core.ProgramCore):
    
    def __init__(self, config_path):
        super(ModeTracker, self).__init__(config_path)
        
        self.fitter = procs.LorentzianFitter()
        self.plotter = procs.Plotter()
        
        self.m_track = mt.ModeTrack()

        self.freq_window = int(self.data_dict['freq_window'])  # Frequency window used for identify peaks specified in MHz
        self.sa_span = int(self.data_dict['sa_span'])  # MHz
        self.sa_averages = int(self.data_dict['sa_averages'])  # total number of averages to take, Max is
        self.fft_length = int(self.data_dict['fft_length'])  # Number of IQ points to generate spectrum, Max is
        
    def prequel(self):
        self.prequel_reflection()
        
    def set_bg_data(self, blank_data):
        
        bg_str = ''
        for triple in blank_data:
            temp_str = str(triple)
            # Create translation table.
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            temp_str = temp_str.translate(trans_table)
            bg_str += temp_str + "\n"
        
        # need to remove list item in list since it will be a blank line
        print("Background data sent to sub-process.")
        self.m_track.SetBackground(bg_str[:-1])

    def find_minima_peak(self, formatted_points):
        data_str = ''
        
        for triple in formatted_points:
            temp_str = str(triple)
            # Create translation table.
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            temp_str = temp_str.translate(trans_table)
            data_str += temp_str + "\n"
        
        return self.m_track.GetPeaksBiLat(data_str[:-1], 1)
    
    def __derive_cavity_length(self):
        
        total_iterations = self.num_of_iters
        start_length = float(self.data_dict['start_length'])
        current_iteration = float(self.iteration)
        tune_length = float(self.data_dict['len_of_tune'])
        
        cavity_length = start_length + (current_iteration * tune_length / (total_iterations))
        return cavity_length
        
    def __recenter_peak(self, power_list, mode_of_desire):
             
#         cavity_length = self.__derive_cavity_length()
        cavity_length = self.ardu_comm.get_cavity_length()
        trans_window_str = self.convertor.power_list_to_str(power_list, mode_of_desire, self.freq_window, cavity_length)
        
        return self.m_track.GetMaxPeak(trans_window_str[:-1])
    
    def save_freq_window(self, freq_window_spec):
        
        power_list = self.convertor.str_list_to_power_list(freq_window_spec)
        
        path = os.path.join(os.getcwd() + '/data/current_freq_window.csv')
        out_file = open(path, 'w+')
        
        out_str = ''
        for power in power_list:
            out_str += str(power) + "\n"
            
        print(out_str, end="", file=out_file)

        out_file.close() 
        
        path += " current_freq_window.jpeg"
        command = "./data/transfer_power_spec.sh " + path
        subprocess.Popen(command, shell=True)

    def check_peak(self, mode_of_desire):
        
        nwa_span = self.nwa_span
        freq_window = self.freq_window

        if (mode_of_desire == 0.0):
            self.print_red("Mode of desire not found.")
            return

        self.print_purple("Checking peak.")
        
        # since we identified the position of our mode using reflection measurements
        # we need to switch to transmission to find the 'real' position of the mode
        self.switch_comm.switch_to_transmission()
        
        self.nwa_comm.set_freq_window(mode_of_desire , freq_window)
        initial_window = self.nwa_comm.take_data_single()
        self.save_freq_window(initial_window)
        
        initial_window = self.convertor.str_list_to_power_list(initial_window)
        
#         self.plotter(initial_window, mode_of_desire, freq_window)

        new_mode_of_desire = self.__recenter_peak(initial_window, mode_of_desire)

        self.nwa_comm.set_freq_window(new_mode_of_desire , freq_window)
        final_window = self.nwa_comm.take_data_single()
        self.save_freq_window(final_window)
        
        final_window = self.convertor.str_list_to_power_list(final_window)
        
#         self.plotter(final_window, new_mode_of_desire, freq_window)

        self.fitter(final_window, new_mode_of_desire, freq_window)

        self.nwa_comm.set_freq_window(new_mode_of_desire , nwa_span)

        # return to reflection measurements
        self.switch_comm.switch_to_reflection()
        
        return new_mode_of_desire
    
    def get_data_sa(self, mode_of_desire):
        
        self.nwa_comm.turn_off_RF_source()
        
        self.sa_comm.set_signal_analyzer(mode_of_desire, self.fft_length, self.freq_window, self.sa_averages)
        raw_sa_data = self.sa_comm.take_data_signal_analyzer()
        
        self.nwa_comm.turn_on_RF_source()
        
        return raw_sa_data
    
class ModeTrackProgram(ModeTracker):

    def __init__(self, config_path):
        super(ModeTrackProgram, self).__init__(config_path)
        atexit.register(self.panic_cleanup)
        
    def find_mode_of_desire_reflection(self):
        nwa_data = self.get_data_nwa()
        self.save_power_spec(nwa_data)
        
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
    
    def save_power_spec(self, power_spec):
        
        power_list = self.convertor.str_list_to_power_list(power_spec)
        
        path = os.path.join(os.getcwd() + '/data/current_power_spectrum.csv')
        out_file = open(path, 'w+')
        
        out_str = ''
        for power in power_list:
            out_str += str(power) + "\n"
            
        print(out_str, end="", file=out_file)

        out_file.close() 
        
        path += " current_power_spectrum.jpeg"
        command = "./data/transfer_power_spec.sh " + path
        subprocess.Popen(command, shell=True)
        
    def save_data(self, formatted_data, idx):
        
        path = self.generate_save_file_name(idx)
        out_file = open(path, 'a')
        
        for item in formatted_data:
            out_str = str(item)
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            out_str = out_str.translate(trans_table)
        
            print(out_str, end="\n", file=out_file)
        
        out_str = "Wrote data to " + path
        
        out_file.close()           

    def program(self):

        self.prequel()
        self.set_background()
        self.next_iteration()

        # start indexing at one since we used our first iteration to capture
        # background data
        for x in range(1, self.num_of_iters):
            
            mode_of_desire = self.find_mode_of_desire_reflection()
            if (mode_of_desire <= 0):
                self.next_iteration()
                continue
            mode_of_desire = self.find_mode_of_desire_transmission(mode_of_desire)
            if (mode_of_desire <= 0):
                self.next_iteration()
                continue
            
            data = self.get_data_sa(mode_of_desire)
            data = self.convertor.str_list_to_power_list(data)
            self.save_data(data, x)

            self.next_iteration()

#         self.retract_cavity()
        self.close_all()

    def panic_cleanup(self):

        current_iteration = self.iteration
        revs_per_iters = int(self.data_dict['revs_per_iter'])
        self.step_comm.panic_reset_cavity(current_iteration, revs_per_iters)
        self.close_all()