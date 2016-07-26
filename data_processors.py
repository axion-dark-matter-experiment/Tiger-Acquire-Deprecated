import re  # re.split
from scipy.optimize import leastsq  # least squares curve fitting
import numpy as np  # numpy arrays
import matplotlib.pyplot as plt  # accursed matplotlib functions
import color_printer as cp

#convert either a list of strings, or a single string
#into a list of floats

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
        
        #If input is a -list- of strings join together to form a single string
        #If input is a single string, do nothing
        total_str = ''.join(raw_data)
        #remove end of field characters which would mess-up split
        power_list = total_str.strip()
        #Since we are expecting a comma seperated list of strings (or single string)
        #we split on command or newlines to remove these special characters
        power_list = re.split(',|\n', power_list)
    
        power_list = [float(y) for y in power_list]
        num_points = len(power_list)
        
        formatted_points = []
        
    
#         max_frequency = nominal_centers[-1] + nwa_span / 2
#         min_frequency = nominal_centers[0] - nwa_span / 2
#         num_points = 4 * nwa_points
    
        for idx, power in enumerate(power_list):
            # (idx+1)*(4600 - 3000)/(1604) + 3000
            frequency = (idx + 1) * (max_frequency - min_frequency) / (num_points) + min_frequency
            frequency = int(round(frequency))
            formatted_points.append([frequency, cavity_length, power])
    
        return formatted_points
    
class Plotter:
        
    def __call__(self, plot_data, center_freq, freq_window):
        self.__plot_freq_window(plot_data, center_freq, freq_window)
        
    def __plot_freq_window(self, plot_data, center_freq, freq_window):
        plot_title = 'Frequency Window'
    
        points = len(plot_data)
    
        nwa_y = [10.**(y / 10) for y in plot_data]  # convert from dBm to power (mW)
    
        # get x values from center frequency and span
        nwa_x = [(center_freq - (freq_window / 2) + \
          freq_window * (float(x) / points)) for x in range(points)]
    
        # convert to arrays
        nwa_x = np.array(nwa_x)
        nwa_y = np.array(nwa_y)
        nwa_y_dbm = [10 * np.log10(y) for y in nwa_y]
    
        plt.title(plot_title)
        plt.xlabel('Frequency (MHz)')
        plt.ylabel('Power (dBm)')
        plt.plot(nwa_x, nwa_y_dbm, '.')
        #plot figure. While the figure is displayed the program will be halted, because
        # you know- Matplotlib.
        plt.show()
        
class LorentzianFitter:
    
    def __init__(self):
        self.print_yellow = cp.ColorPrinter("Yellow")
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
        middle = ((2 * nwa_points / 5 < np.arange(nwa_points)) & 
                (np.arange(nwa_points) < 3 * nwa_points / 5))
        # initial values for fit: [HWHM, peak center, height]
        p = [25.0, center_freq, nwa_yw[nwa_points / 2]]
        pbest = leastsq(self.residuals, p, args=(nwa_yw[middle], nwa_xw[middle], center_freq, freq_window))[0]
    
        fitted_hwhm = pbest[0]
        fitted_center_freq = pbest[1]
        fitted_center_freq_step = fitted_center_freq + 20
    
        fitted_height = pbest[2]
        fitted_q = fitted_center_freq / (fitted_hwhm * 2)
        # convert back to dBm
        fitted_height = 10 * np.log10(fitted_height)
    
        nwa_y_dbmw = [10 * np.log10(y) for y in nwa_yw]
    
        # report parameters
        self.print_purple("Parameters:")
    
        out_str = "Fitted Q: " + str(fitted_q) + "\nFitted center frequency (MHz): "\
        + str(fitted_center_freq) + "\nFitted height (dBm): " + str(fitted_height)
    
        self.print_yellow(out_str)
    
        output_triple = [fitted_q, fitted_center_freq, fitted_height]
    
        return output_triple