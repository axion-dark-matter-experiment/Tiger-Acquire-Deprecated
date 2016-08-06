import program_core as core

import atexit
import subprocess
import os
import data_processors as procs
import modetrack as mt
import time
import sys

class ModeTracker(core.ProgramCore):
    
    def __init__(self, config_path):
        super(ModeTracker, self).__init__(config_path)
        
        self.fitter = procs.LorentzianFitter()
        self.m_track = mt.ModeTrack()

        self.freq_window = int(self.data_dict['freq_window'])  # Frequency window used for identify peaks specified in MHz
        self.sa_span = int(self.data_dict['sa_span'])  # MHz
        self.sa_averages = int(self.data_dict['sa_averages'])  # total number of averages to take, Max is
        self.fft_length = int(self.data_dict['fft_length'])  # Number of IQ points to generate spectrum, Max is
        
        self.noise_temperature = int(self.data_dict['noise_temperature'])  # Degrees Kelvin
        self.effective_volume = int(self.data_dict['effective_volume'])  # Note from Legacy code read 'Invalid !!'
        self.bfield = float(self.data_dict['bfield'])  # Tesla
        
        self.center_frequency = 0.0
        self.hwhm = 0.0
        self.quality_factor = 0.0
        
        # actual_center_freq, sa_span, fft_length, fitted hwhm, effective_volume, bfield, noise_temperature, sa_averages
        
    def prequel(self):
        self.prequel_reflection()
        
    def _build_data_header(self):
        header = ''
        header += "sa_span;" + str(self.sa_span) + "\n"
        header += "fft_length;" + str(self.fft_length) + "\n"
        header += "effective_volume;" + str(self.effective_volume) + "\n"
        header += "bfield;" + str(self.bfield) + "\n"
        header += "noise_temperature;" + str(self.noise_temperature) + "\n"
        header += "sa_averages;" + str(self.sa_averages) + "\n"
        header += "Q;" + str(self.quality_factor) + "\n"
        header += "actual_center_freq;" + str(self.center_frequency) + "\n"
        header += "fitted_hwhm;" + str(self.hwhm) + "\n"
        header += "cavity_length;" + str(self.ardu_comm.get_cavity_length()) + "\n"
        
        return header
    
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
        
#         path = os.path.join(os.getcwd() + '/data/current_freq_window.csv')
        dir_path = os.path.dirname(os.path.realpath(__file__))
        path = dir_path + "/data/current_freq_window.csv"
        out_file = open(path, 'w+')
        
        out_str = ''
        for power in power_list:
            out_str += str(power) + "\n"
            
        print(out_str, end="", file=out_file)

        out_file.close() 
        
        path += " " + dir_path + "/data/current_freq_window.jpeg"
        command = dir_path + "/data/transfer_power_spec.sh " + path
        
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
        
        initial_window = self.convertor.str_list_to_power_list(initial_window)

        new_mode_of_desire = self.__recenter_peak(initial_window, mode_of_desire)

        self.nwa_comm.set_freq_window(new_mode_of_desire , freq_window)
        final_window = self.nwa_comm.take_data_single()
        self.save_freq_window(final_window)
        
        final_window = self.convertor.str_list_to_power_list(final_window)

        data_triple = self.fitter(final_window, new_mode_of_desire, freq_window)
        
        self.quality_factor = data_triple[0]
        self.center_frequency = data_triple[1]
        self.hwhm = data_triple[2]

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
        self.directory = self.get_folder_name()
        self.make_empty_data_folder(self.directory)
        
        self.saver = procs.FlatFileSaver('data', 'SA', 'Formatted')
        self.raw_saver = procs.FlatFileSaver('data', 'R_SA', 'Raw')
        
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
#         time_stamp = time.strftime("%d.%m.%Y")
        # concatenate the base save-file path with the date-time string to form the name of all necessary .csv files
#         save_path = self.data_dict['save_file_path']
        
        save_path = self.directory
        return os.path.join(save_path, str(idx) + 'SA.csv')
    
    def save_power_spec(self, power_spec):
        
        power_list = self.convertor.str_list_to_power_list(power_spec)
        
        dir_path = os.path.dirname(os.path.realpath(__file__))
        path = dir_path + "/data/current_power_spectrum.csv"
        
        out_file = open(path, 'w+')
        
        out_str = ''
        for power in power_list:
            out_str += str(power) + "\n"
            
        print(out_str, end="", file=out_file)

        out_file.close() 
        
        path += " " + dir_path + "/data/current_power_spectrum.jpeg"
        command = dir_path + "/data/transfer_power_spec.sh " + path

        subprocess.Popen(command, shell=True)
        
    def transfer_terminal_output(self):
        dir_path = os.path.dirname(os.path.realpath(__file__)) + "/"

        cmd = "cat " + dir_path + "etig_log.txt" + " | " + dir_path + "ansi2html.sh"

        terminal_html = subprocess.getoutput(cmd)
        
        path = dir_path + "index.html"
        out_file = open(path, 'w+')
        
        print(terminal_html, end="", file=out_file)
        out_file.close()
        
        transfer_cmd = "scp " + dir_path + "index.html "
        transfer_cmd += "kitsune.dyndns-ip.com:~/"
         
        subprocess.Popen(transfer_cmd, shell=True)
        
        
    def get_folder_name(self):
        time_stamp = time.strftime("%H:%M:%S_%d.%m.%Y")
        dir_path = os.path.dirname(os.path.realpath(__file__))
        path = dir_path + "/data/" + time_stamp + "/"
        
        return path
        
    def make_empty_data_folder(self, directory):
        
        if not os.path.exists(directory):
            os.makedirs(directory)
            
    # actual_center_freq, sa_span, fft_length, fitted hwhm, effective_volume, bfield, noise_temperature, sa_averages
        
    def save_data(self, formatted_data):
        
        header = self._build_data_header()
        self.saver(formatted_data, header)
        
    def save_raw_data(self, raw_data):
        
        header = self._build_data_header()
        self.raw_saver(raw_data, header)

    def program(self):

        self.prequel()
        self.set_background()
        self.next_iteration()

        # start indexing at one since we used our first iteration to capture
        # background data
        for x in range(1, self.num_of_iters):
            self.transfer_terminal_output()
            
            mode_of_desire = self.find_mode_of_desire_reflection()
            if (mode_of_desire <= 0):
                self.next_iteration()
                continue
            mode_of_desire = self.find_mode_of_desire_transmission(mode_of_desire)
            if (mode_of_desire <= 0):
                self.next_iteration()
                continue
            
            data = self.get_data_sa(mode_of_desire)
            self.save_raw_data(data)
            
            data = self.convertor.str_list_to_power_list(data)
            self.save_data(data)

            self.next_iteration()

#         self.retract_cavity()
        self.close_all()

    def panic_cleanup(self):

        current_iteration = self.iteration
        revs_per_iters = float(self.data_dict['revs_per_iter'])
        self.step_comm.panic_reset_cavity(current_iteration, revs_per_iters)
        self.close_all()
