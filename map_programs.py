import program_core as core

import atexit
import subprocess
import os

class MapBuilderCore (core.ProgramCore):
    
    def __init__(self, config_path, map_type):
        super(MapBuilderCore, self).__init__(config_path)
        
        if (map_type == "R"):
            self.file_name = self.data_dict['file_nameR']
        elif(map_type == 'M'):
            self.file_name = self.data_dict['file_name']
        else:
            pass
        
        atexit.register(self.__panic_cleanup)
    
    def __transfer_map(self):
        
        path = self.file_name
        
        command = "./data/transfer_map.sh " + path
        subprocess.Popen(command, shell=True)
        
    def __transfer_power_spec(self, power_spec):
        
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
        
        
    def __save_data(self, formatted_data):
        
        path = self.file_name
        
        out_file = open(path, 'a')
        
        for item in formatted_data:
            out_str = str(item)
            trans_table = dict.fromkeys(map(ord, ' []'), None)
            out_str = out_str.translate(trans_table)
        
            print(out_str, end="\n", file=out_file)
        
        out_str = "Wrote data to " + path
        
        out_file.close()      
        
    def _get_nwa_data(self):
        nwa_data = self.get_data_nwa()
        self.__transfer_power_spec(nwa_data)
        
        formatted_points = self.format_points(nwa_data)
        self.__save_data(formatted_points)
        self.__transfer_map()    

    def __panic_cleanup(self):

        current_iteration = self.iteration
        revs_per_iters = int(self.data_dict['revs_per_iter'])
        self.step_comm.panic_reset_cavity(current_iteration, revs_per_iters)
        self.close_all()

class ModeMapProgram(MapBuilderCore):
    
    def __init__(self, config_path):
        super(ModeMapProgram, self).__init__(config_path, 'M')
        
    def __prequel(self):
        self.prequel_transmission()
        
    def program(self):

        self.__prequel()

        for x in range(0, self.num_of_iters):
            
            self._get_nwa_data()
            self.next_iteration()

        self.close_all()
        
class ReflectionMapProgram(MapBuilderCore):
    
    def __init__(self, config_path):
        super(ReflectionMapProgram, self).__init__(config_path, 'R')
        
    def __prequel(self):
        self.prequel_reflection()
        
    def program(self):

        self.__prequel()

        for x in range(0, self.num_of_iters):
            
            self._get_nwa_data()
            self.next_iteration()

        self.close_all()