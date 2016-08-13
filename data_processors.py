import re  # re.split
from scipy.optimize import leastsq  # least squares curve fitting
import numpy as np  # numpy arrays
import color_printer as cp
import os
import time
import subprocess

# convert either a list of strings, or a single string
# into a list of floats

class Convertor:
    
    def str_list_to_power_list(self, raw_strs):
    
        total_str = ''.join(raw_strs)
        power_list = total_str.strip()
        power_list = re.split(',|\n', power_list)
        power_list = [float(y) for y in power_list]
    
        return power_list
    
    def power_list_to_str(self, power_list, center_freq, freq_window, cavity_length):
    
        plot_points = []
    
        max_length = round(center_freq) + freq_window / 2
        min_length = round(center_freq) - freq_window / 2
        num_points = len(power_list)
    
        for idx, power in enumerate(power_list):
            frequency = (idx + 1) * (max_length - min_length) / (num_points) + min_length
            frequency = int(round(frequency))
            plot_points.append([frequency, cavity_length, power])
    
        freq_window_str = ''
        for triple in plot_points:
            temp_str = str(triple)
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            temp_str = temp_str.translate(trans_table)
            freq_window_str += temp_str + "\n"
    
        return freq_window_str
    
    def make_plot_points(self, raw_data, cavity_length, min_frequency, max_frequency):
        """Convert collected data into a format suitable for saving or processing.
        Output data will be a list of triples (Frequency(mHz),Cavity Length(in),Power(dBm))
    
        Args:
            raw_data:Either a list of strings or a single string in comma seperated format
            cavity_length:The current length of the cavity in inches
            nominal_centers:RunTimeParameters class
    
        Returns:
            plot_points, a list of data triples with the format described above
        """
        
        # If input is a -list- of strings join together to form a single string
        # If input is a single string, do nothing
        total_str = ''.join(raw_data)
        # remove end of field characters which would mess-up split
        power_list = total_str.strip()
        # Since we are expecting a comma seperated list of strings (or single string)
        # we split on command or newlines to remove these special characters
        power_list = re.split(',|\n', power_list)
    
        power_list = [float(y) for y in power_list]
        num_points = len(power_list)
        
        formatted_points = []
    
        for idx, power in enumerate(power_list):

            frequency = (idx + 1) * (max_frequency - min_frequency) / (num_points) + min_frequency
            frequency = int(round(frequency))
            formatted_points.append([frequency, cavity_length, power])
    
        return formatted_points
    
class NouveauLorentzianFitter:
    
    def __init__(self):
        """
        Initialize colored terminal printers.
        """
        self.print_blue = cp.ColorPrinter("Blue")
        self.print_purple = cp.ColorPrinter("Purple")
        
        
    def __call__(self, fit_data, center_freq, freq_window):
        """
        Overload __call__ function designed to fit the functor design pattern.
        Call the internal function __determine_Q.
        
        Args:
            fit_data: power spectrum where mode of desire is expected to be, in units of dBm
            center_freq: frequency where the mode of desire is centered
            freq_window: tne width of the frequency window in MHz
            
        Returns:
            data triple in the format [Q, Max Power Frequency (dBm), HWHM(MHz)]
        """
        return self.__determine_Q(fit_data, center_freq, freq_window)
    
    def __get_min_delta_index(self, search_list, reference ):
        """
        Compare all elements in a list to a reference and determine which element
        is the closest to the reference.
        The list under comparison MUST have a reference level of ZERO.
        
        Args:
            search_list, the list of data to be compared to the reference value
            reference, the element to be compared against. Needs to be strictly positive.
            
        Returns:
            The index of whatever element was closest to 'reference'
            If multiple elements are all equally close to 'reference' return the
            element with the highest index (Python's behaviour, not mine)
        """
            
        delta_list = [ abs(val - reference) for val in search_list ]
        
        min_delta = min ( delta_list )
        return delta_list.index( min_delta )
    
    def __convert_to_mwatts(self, power_list):
        """
        Convert a power spectrum from units of dBm to units of milliWatts
        
        Args:
            power_list, list of power data in dBm
        
        Returns:
            List of power data in mW
        """
        return [10.**(dbm_power / 10) for dbm_power in power_list]
    
    def __set_zero_reference(self, power_list):
        
        min_power = min (power_list)
        return [ (power - min_power) for power in power_list]
        
    def __determine_Q(self, freq_window, center_frequency, frequency_span ):
        
        max_power_dbm = max( freq_window )
        
        mw_power_list = self.__convert_to_mwatts( freq_window )

        max_power_mw = max ( mw_power_list )
        
        max_power_index = mw_power_list.index( max_power_mw )

        half_max_power = max_power_mw / 2
        
        index_left_side = self.__get_min_delta_index( mw_power_list[:max_power_index], half_max_power )

        index_right_side = self.__get_min_delta_index( mw_power_list[max_power_index:], half_max_power )
        index_right_side += ( max_power_index )
        
        FWHM = frequency_span*abs(index_left_side - index_right_side)/len(freq_window)
        
        min_frequency = center_frequency - frequency_span / 2
        max_power_frequency = ( max_power_index * frequency_span ) / (len( freq_window )) + min_frequency
        
        # Print parameters to terminal
        self.print_purple("Parameters:")
        
        quality_factor = (max_power_frequency/FWHM)
    
        out_str = "Q: " + str(quality_factor) + "\nCenter Frequency (MHz): "\
        + str(max_power_frequency) + "\nMax Power (dBm): " + str(max_power_dbm)\
        + "\nFWHM:"+str(FWHM)
    
        self.print_blue(out_str)
        
        return [quality_factor, max_power_frequency, FWHM/2]
        
class LorentzianFitter:
    
    def __init__(self):
        self.print_blue = cp.ColorPrinter("Blue")
        self.print_purple = cp.ColorPrinter("Purple")
        
        
    def __call__(self, fit_data, center_freq, freq_window):
        return self.__fit_lorentzian(fit_data, center_freq, freq_window)
        
    def __lorentzian(self, x, p):
        """Calculate Lorentz Line Shape.
    
        Used for determining Q of a particular peak.
    
        Args:
            p:List of parameters of the form [HWHM, Center, Height]
        """
        numerator = p[0] ** 2
        denominator = (x - p[1]) ** 2 + p[0] ** 2
        return p[2] * (numerator / denominator)

    # check whether parameters [HWHM, center, height] are within reasonable bounds
    def __within_bounds(self, p, center_freq, freq_window):
        """
        Check whether values for Lorentzian best fit curve are within reasonable
        bounds.
    
        Args:
            p:List of parameters
            center_freq: Center of the frequency window where the Lorentzian will be fitted
            freq_window: Width of of the frequency window centered at center_freq
            class.
    
        Returns:
            True if within reasonable bounds, False otherwise
        """
    
        if p[0] < 0 or p[0] > freq_window:
            return False
        if (p[1] < center_freq - freq_window or p[1] > center_freq + freq_window):
            return False
        return True
    
    # calculate residuals of fitted curve
    def __residuals(self, p, y, x, center_freq, freq_window):
        if self.__within_bounds(p, center_freq, freq_window):
            err = y - self.__lorentzian(x, p)
            return err
        else:
            return 1e6
    
    def __fit_lorentzian(self, fit_data, center_freq, freq_window):
    
        nwa_points = len(fit_data)
    
        print ("Fitting data")
        try:
            nwa_yw = [float(y) for y in fit_data]
        except ValueError as exc:
            print ("Could not convert to float: ", exc)
    
        # convert from dBm to power (mW)
        nwa_yw = [10.**(y / 10) for y in nwa_yw]
        # get x values from center frequency and span
        nwa_xw = [(center_freq - (freq_window / 2) + \
                freq_window * (float(x) / nwa_points)) for x in range(nwa_points)]
        # convert to arrays
        nwa_xw = np.array(nwa_xw)
        nwa_yw = np.array(nwa_yw)
    
        # define middle values to fit to
        middle = ((2 * nwa_points / 5 < np.arange(nwa_points)) & (np.arange(nwa_points) < 3 * nwa_points / 5))
        # initial values for fit: [HWHM, peak center, height]
        p = [25, center_freq, nwa_yw[nwa_points / 2]]
        
        pbest = leastsq(self.__residuals, p, args=(nwa_yw[middle], nwa_xw[middle], center_freq, freq_window))[0]
    
        fitted_hwhm = pbest[0]
        fitted_center_freq = pbest[1]
    
        fitted_height = pbest[2]
        fitted_q = fitted_center_freq / (fitted_hwhm * 2)
        # convert back to dBm
        fitted_height = 10 * np.log10(fitted_height)
    
        # report parameters
        self.print_purple("Parameters:")
    
        out_str = "Fitted Q: " + str(fitted_q) + "\nFitted center frequency (MHz): "\
        + str(fitted_center_freq) + "\nFitted height (dBm): " + str(fitted_height)
    
        self.print_blue(out_str)
    
        output_triple = [fitted_q, fitted_center_freq, fitted_hwhm]
    
        return output_triple
    
class FlatFileSaver:
    
    def __init__(self, root_dir ):
        
        self.root_dir = root_dir
        self.directory = self.__get_folder_name()
        
        self.__make_empty_data_folder(self.directory)
    
    def __make_empty_data_folder(self, directory):
        
        if not os.path.exists(directory):
            print("Made new folder at: " + directory)
            os.makedirs(directory)
    
    def __get_folder_name(self):
        
        time_stamp = time.strftime("%S:%M:%H_%d.%m.%Y")
        dir_path = os.path.dirname(os.path.realpath(__file__))
        
        root_path = "/" + self.root_dir + "/"
        path = dir_path + root_path + time_stamp + "/"

        return path

    def _generate_save_file_name(self, idx = None, opt = None):
        
        if( idx is None and opt is None):
            return os.path.join( '.csv')
        elif( opt is None ):
            return os.path.join(str(idx) + '.csv')
        elif( idx is None ):
            return os.path.join(str(opt) + '.csv')
        else:
            return os.path.join(str(opt) + str(idx) + '.csv')
    
    def _append_to_data( self, data , file_path, header_string = None):
        
        out_file = open(file_path, 'a')
        
        if( header_string is not None):
            print(header_string, end="\n", file=out_file)
        
        for item in data:
            out_str = str(item)
#             trans_table = dict.fromkeys(map(ord, ' []'), None)
#             out_str = out_str.translate(trans_table)
        
            print(out_str, end="\n", file=out_file)
        
        out_str = "Wrote data to " + file_path
        
        out_file.close()
        
class SignalAnalyzerSaver( FlatFileSaver ):
    
    def __init__(self, root_dir, sa_type = 'R+F'):

        super(SignalAnalyzerSaver, self).__init__( root_dir )
        
        if (sa_type == 'R'):
            self.__call_back = self.__save_raw_data
            
        elif( sa_type == 'F'):
            self.__call_back = self.__save_formatted_data
            
        elif( sa_type == 'R+F'):
            self.convertor = Convertor()
            self.__call_back = self.__save_raw_and_formatted
            
        self.counter = 0
         
    def __call__(self, data, header_string = None):
        
        self.__call_back( data, header_string )
        self.counter += 1
        
        return self.counter
    
    def __save_raw_data(self, raw_data, header_string):
        
        path = self._generate_save_file_name(self.counter, 'SA_R')
        file_path = self.directory + path
        
        out_file = open(file_path, 'a')
        
        print(header_string, end="\n", file=out_file)
        print(raw_data, end="\n", file=out_file)
        
        out_str = "Wrote data to " + path
        print (out_str)
        
        out_file.close()
        
    def __save_formatted_data( self, formatted_data, header_string ):
        
        path = self._generate_save_file_name(self.counter, 'SA_F')
        file_path = self.directory + path
        
        self._append_to_data( formatted_data, file_path, header_string )
        
    def __save_raw_and_formatted(self, raw_data, header_string ):
        
        self.__save_raw_data( raw_data, header_string )
        formatted_data = self.convertor.str_list_to_power_list(raw_data)
        
        self.__save_formatted_data(formatted_data, header_string)
        
class NetworkAnalyzerSaver( FlatFileSaver ):
    
    def __init__(self, root_dir ):

        super(NetworkAnalyzerSaver, self).__init__( root_dir )
#         self.file_name = os.path.join('NA' + '.csv')
        self.file_name = self._generate_save_file_name('NA')
        
    def __call__(self, formatted_data ):
        self.__save_data( formatted_data )
        self.__transfer_map()
        
    def __save_data(self, formatted_data):
        
        path = self.directory + self.file_name
        
        out_file = open(path, 'a')
        
        for item in formatted_data:
            out_str = str(item)
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            out_str = out_str.translate(trans_table)
        
            print(out_str, end="\n", file=out_file)
        
        out_str = "Wrote data to " + path
        
        out_file.close()
        
    def __transfer_map(self):
        
        path = self.directory + self.file_name
        dir_path = os.path.dirname(os.path.realpath(__file__))
        
        command = dir_path + "/data/transfer_map.sh " + path
        
        subprocess.Popen(command, shell=True)
