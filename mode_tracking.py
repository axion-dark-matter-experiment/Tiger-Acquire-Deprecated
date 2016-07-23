import base_classes
import base_functions as funcs
import modetrack as mt

import socket_connect_2 as sc
import time
import atexit

class ModeTrackBody(base_classes.BaseTypes):

    def __init__(self,config_path):
        super(ModeTrackBody, self).__init__(config_path)

        self.nwa_sock = self.sock_dict['nwa']
        self.switch_sock = self.sock_dict['switch']
        self.sa_sock = self.sock_dict['sa']

        self.freq_window = 100 # Frequency window used for identify peaks specified in MHz
        self.sa_span = 10 # MHz
        self.sa_averages = 256 #total number of averages to take, Max is
        self.fft_length = 65536 #Number of IQ points to generate spectrum, Max is

        self.fitted_q=0.0
        self.fitted_center_freq=0.0
        self.fitted_height=0.0

        #initialize modetrack class
        self.m_track = mt.ModeTrack()
        #container for formatted data triples
        self.formatted_points=[]
        #position of the mode of desire in frequency space
        self.mode_of_desire=0.0
        self.iteration = 0

    def retract_cavity(self):
        step = funcs.get_step_sock(self.addr_dict)
        tune_length=float(self.data_dict['len_of_tune'])

        funcs.reset_cavity(step,tune_length)

        step.close()

    def prequel(self):

    	sc.send_command(self.switch_sock, "V2 28") #Set power supply voltage on source 2 to 28 volts (switch actuation voltage)
    	sc.send_command(self.switch_sock, "OP2 0") #Set switch to route return RF through directional coupler and amplifiers

    	funcs.set_network_analyzer(self.nwa_sock,self.nwa_points)
    	funcs.set_RF_mapping(self.nwa_sock,self.switch_sock,self.nwa_span,self.nwa_power)

    def get_data_nwa(self):
        self.raw_nwa_data.extend(funcs.collect_data(self.nwa_sock,self.nominal_centers))


    def format_points(self):

        total_iterations=self.num_of_iters
        start_length=float(self.data_dict['start_length'])
        current_iteration=float(self.iteration)
        tune_length=float(self.data_dict['len_of_tune'])

        cavity_length=start_length + (current_iteration*tune_length/(total_iterations))
        funcs.c_print("Current cavity length: "+str(cavity_length),"Yellow")

        del self.formatted_points[:]

        self.formatted_points = funcs.make_plot_points(cavity_length,self.nominal_centers,self.nwa_span,self.nwa_points,self.raw_nwa_data)

        del self.raw_nwa_data[:]

    def set_bg_data(self):
    	bg_str = ''
    	for triple in self.formatted_points:
    		temp_str = str(triple)
    		# Create translation table.
    		trans_table = dict.fromkeys(map(ord, ' []'), None)
    		temp_str = temp_str.translate(trans_table)
    		bg_str += temp_str + "\n"

    	#need to remove list item in list since it will be a blank line
    	funcs.c_print("Background data sent to sub-process.","Green")
    	self.m_track.SetBackground(bg_str[:-1])

    def find_minima_peaks(self):
    	data_str = ''

    	for triple in self.formatted_points:
    		temp_str = str(triple)
    		# Create translation table.
    		trans_table = dict.fromkeys(map(ord, ' []'), None)
    		temp_str = temp_str.translate(trans_table)
    		data_str += temp_str + "\n"

    	self.mode_of_desire = self.m_track.GetPeaksBiLat(data_str[:-1],0)

    def next_iteration(self):

        len_of_tune=self.data_dict['len_of_tune']
        revs=int(self.data_dict['revs_per_iter'])

        self.iteration += 1

        iters= self.iteration
        num_of_iters= self.num_of_iters

        step_sock = funcs.get_step_sock(self.addr_dict)
        funcs.walk_loop(step_sock,len_of_tune,revs,iters,num_of_iters)

    def set_signal_analyzer(self):

    	sa_sock=self.sock_dict['sa']
    	fft_length = self.fft_length
    	sa_span = self.sa_span
    	sa_averages = self.sa_averages
    	# actual_center_freq = rt_params.actual_center_freq
    	actual_center_freq = 4260

    	funcs.c_print("Setting spectrum analyzer","Purple")

    	#Set RF switch so that signal goes to Signal Analyzer
    	switch=self.sock_dict['switch']
    	sc.send_command(switch, "OP1 1")

    	#general configuration
    	sc.send_command(sa_sock, "INST:SEL BASIC") # set IQ analyzer mode
    	sc.send_command(sa_sock, "SPEC:DIF:BAND 10MHz") # set Digital IF Bandwidth
    	sc.send_command(sa_sock, "SPEC:DIF:FILT:TYPE FLAT") # set filter type to flattop
    	sc.send_command(sa_sock, "SPEC:FFT:WIND UNIF") # set FFT window to uniform
    	sc.send_command(sa_sock, "SPEC:FFT:LENG:AUTO OFF") # disable automatic FFT window and length control

    	#Max size for FFT length is 131072
    	#FFT length represents number of IQ pairs used to generate power spectrum
    	#FFT length indirectly controls 'capture time'
    	#Presumably this time is synonymous with integration time
    	sc.send_command(sa_sock, "SPEC:FFT:WIND:LENG "+str(fft_length)) # set FFT window length
    	sc.send_command(sa_sock, "SPEC:FFT:LENG "+str(fft_length)) # set FFT length

    	#configure measurements
    	sc.send_command(sa_sock, "CONF:SPEC:NDEF") # configure measurement
    	sc.send_command(sa_sock, "FREQ:CENT "+str(actual_center_freq)+"MHz") # set center frequency
    	sc.send_command(sa_sock, "SPEC:FREQ:SPAN "+str(sa_span)+"MHz") # set frequency span

    	#configure averaging
    	sc.send_command(sa_sock, "SPEC:AVER:TYPE RMS") # set average type to power average
    	sc.send_command(sa_sock, "ACP:AVER:TCON EXP") # set averaging to non-repeating
    	#Maximum number of averaged values is 20001
    	sc.send_command(sa_sock, "SPEC:AVER:COUN "+str(sa_averages)) # set number of averages
    	sc.send_command(sa_sock, "INIT:CONT OFF") # turn off continuous measurement operation
    	#Total integration time is given by time_per_frame(FFT length)*num_averages

    	funcs.c_print("Spectrum analyzer set","Green")

    def take_data_signal_analyzer(self):
    	funcs.c_print("Starting integration...","Purple")
    	sa_sock=self.sock_dict['sa']

    	#Initialize measurement
    	#This will start collecting and averaging samples
    	sc.send_command(sa_sock, "INIT:IMM")

    	# *OPC? will write "1\n" to the output when operation is complete.
    	while True:
    		#Poll the signal analyzer
    		sc.send_command(sa_sock, "*OPC?")
    		status_str = sc.read_data(sa_sock, printlen=True, timeout=0.5)

    		#Wait until *OPC? returns '1\n' indicating that the requested number
    		#of samples have been collected
    		if(status_str == "1\n"):
    			print ("Integration complete")
    			break
    		else:
    			print ("Waiting...")

    	#Since measurement is already initliazed collect data with the
    	#FETC(h) command
    	sc.send_command(sa_sock, ":FETC:SPEC7?")
    	raw_sa_data = sc.read_data(sa_sock, printlen=True, timeout=0.5)

    	out_file=open(self.data_dict['file_name'],'a')

    	print(raw_sa_data, end="\n", file=out_file)
    	out_str="Wrote data to "+self.data_dict['file_name']
    	funcs.c_print(out_str,"Green")

    	out_file.close()

    def set_trans_frequency_window(self):
    	nwa_sock=self.sock_dict['nwa']
    	nwa_span=self.nwa_span
    	freq_window=self.freq_window

    	switch=self.sock_dict['switch']

    	mode_of_desire = self.mode_of_desire

    	if ( mode_of_desire == 0.0):
        	funcs.c_print("Mode of desire not found.","Red")
    	return

    	funcs.c_print("Checking peak.","Purple")

    	#switch to measuring transmission spectrum
    	sc.send_command(switch, "OP2 1")

    	# set passthrough mode to source
    	sc.send_command(nwa_sock, "PT19")
    	# change GPIB address to passthrough, send commands to signal sweeper
    	sc.send_command(nwa_sock, "++addr 17")

    	# set center frequency to mode of desire
    	print ("setting center frequency to", mod," MHz")
    	sc.send_command(nwa_sock, "CF "+str(round(mod))+"MZ")
    	time.sleep(1)

    	#establish narrow frequency window around peak
    	#peak position will deviate slighty from observed position in
    	#reflection measurements
    	sc.send_command(nwa_sock, "DF "+str(freq_window)+"MZ")
    	time.sleep(1)

    	# return to network analyzer
    	sc.send_command(nwa_sock, "++addr 16")

    def recenter_peak(self, power_list):
    	total_iterations=self.num_of_iters
    	start_length=float(self.data_dict['start_length'])
    	current_iteration=float(self.iteration)
    	tune_length=float(self.data_dict['len_of_tune'])

    	cavity_length = start_length + (current_iteration*tune_length/(total_iterations))
    	trans_window_str = funcs.power_list_to_str(power_list, self.mode_of_desire, self.freq_window, cavity_length)

    	self.mode_of_desire = self.m_track.GetMaxPeak(trans_window_str[:-1])

    def check_peak(self):
        nwa_sock = self.sock_dict['nwa']
        nwa_span = self.nwa_span
        freq_window = self.freq_window

        switch = self.sock_dict['switch']

        if ( self.mode_of_desire == 0.0):
            funcs.c_print("Mode of desire not found.","Red")
            return

        funcs.c_print("Checking peak.","Purple")
        #switch to measuring transmission spectrum
        sc.send_command(switch, "OP2 1")

        funcs.set_freq_window(nwa_sock, self.mode_of_desire , freq_window)
        initial_trans_window = funcs.take_data_single(nwa_sock)
        initial_trans_window = funcs.str_to_power_list(initial_trans_window)

        funcs.plot_freq_window(initial_trans_window, self.mode_of_desire, freq_window)

        self.recenter_peak(initial_trans_window)

        final_trans_window = funcs.take_data_single(nwa_sock)
        final_trans_window = funcs.str_to_power_list(final_trans_window)

        funcs.plot_freq_window(final_trans_window, self.mode_of_desire, freq_window)

        funcs.fit_lorentzian(final_trans_window, self.mode_of_desire, freq_window)

        funcs.set_freq_window(nwa_sock, self.mode_of_desire , nwa_span)

        #return to reflection measurements
        sc.send_command(switch, "OP2 0")

class ModeTrackProgram(ModeTrackBody):

    def __init__(self,config_path):
        super(ModeTrackProgram, self).__init__(config_path)
        atexit.register(self.panic_cleanup)

    def program(self):

        funcs.set_GPIB(self.nwa_sock)
        self.prequel()

        for x in range(0,self.num_of_iters):
            self.get_data_nwa()
            self.format_points()
            # self.save_plot_points()

            if(x == 0):
            	self.set_bg_data()
            elif(x >= 1):
            	self.find_minima_peaks()
            	self.check_peak()
            	# subprocess.Popen("~/workspace/Electric-Tiger/Python_Files/MM-plot.m",shell=True)

            self.next_iteration()

        self.retract_cavity()
        self.close_all()

    def panic_reset_cavity(self):

        rev = -1.0*self.iteration
        nsteps = int(rev*200)

        step = sc.socket_connect("10.95.100.177", 7776)

        # set steps per revolution to 200 steps/revolution
        sc.send_command_scl(step, "MR0")

        # Acceleration of 5 rev/s/s
        sc.send_command_scl(step, "AC5")
        # Deceleration of 5 rev/s/s
        sc.send_command_scl(step, "DE5")
        # Velocity of 5 rev/s
        sc.send_command_scl(step, "VE5")

        funcs.c_print("Program halted! Resetting cavity to initial length.","Red")
        print ("Moving motor "+ str(abs(rev))+" revolutions.")

        sc.send_command_scl(step, "FL"+str(nsteps))

        step.close()

    def panic_cleanup(self):

        self.panic_reset_cavity()
        self.close_all()
