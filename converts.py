import re  # re.split


#convert either a list of strings, or a single string
#into a list of floats

class Convertor:
    
    def __init__(self):
        #
    
    def __call__(self, message):
#     print "I got called with %r!" % (a,)
    
    def str_list_to_power_list(self,raw_strs):
    
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