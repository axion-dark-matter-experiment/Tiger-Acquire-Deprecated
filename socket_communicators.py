"""
Group of classes that handle communications between the local machine (the one running the program)
and remote instruments via network sockets.

This file also serves as a replacement for the old 'socket_connect' module and its' slightly more
modern incarnation, 'socket_connect_2'
"""

import socket
import sys
import select
import time  # sleep
import datetime as dt
import color_printer as cp

class SocketComm:
    """
    Object that handles basic network socket operations.
    This class is responsible for generating sockets, sending strings and receiving strings.
    """    
    def __init__(self):
        """
        Initialize color printers.
        """
        
        self.print_green = cp.ColorPrinter("Green")
        self.print_purple = cp.ColorPrinter("Purple")
        self.print_yellow = cp.ColorPrinter("Yellow")
        self.print_red = cp.ColorPrinter("Red")

    def _socket_connect(self, host, port):
        """
        Attempt to generate a socket to IP address 'host' on port 'port'
        
        Args:
            host: The IP address we want to connect to, specified as a string
            ex "8.8.8.8"
            
            port: The port we wish to connect to, specifed as a number
            ex. 80
            
        Returns:
            Socket object to the specified IP and port on success, None on failure
        """

        #Attempt to get host info
        try:
            sockinfo = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        except OSError:
            #Return None if we fail
            print ("Socket Connect: could not get host info.")
            return None

        # Connect to first socket we can
        for sock in sockinfo:
            try:
                s = socket.socket(sock[0], sock[1], sock[2])
                s.settimeout(5)  # set socket time-out to 5 seconds, default is ~120 seconds
                s.connect((host, port))
                print ("Socket Connect: connected to", s.getpeername()[0])
                #Return socket object on success
                return s
            except (IOError, ValueError) as exc:
                print ("Socket Connect: Could not connect to socket.")
                # Raise the same errors that tripped _socket_connect so functioned that
                # caller is aware of the error
                raise exc
                return None

    def _send_command(self, sock, cmd, terminator='\n'):
        """
        Send a terminated string to a socket.
        Most instruments recognize '\n' as EOF so we use that for the default.
        
        Note that this function should not be used to send long commands since
        it will time-out after a while.
        
        Args:
            sock: The socket object to send the string to
            cmd: The string to be sent
            terminator: EOF character to append to the end of the string
        """
        try:
            command = cmd + terminator
            sock.send(command.encode())
        except:
            print ("Error sending command", cmd, sys.exc_info()[0])

    def _send_command_long(self, sock, cmd, terminator='\n'):
        """
        Send a terminated string of arbitrary length to a socket.
        Unlike _send_command this function will never time and, and will
        continuing sending data until finished or an error occurs.
        
        Args:
            sock: The socket object to send the string to
            cmd: The string to be sent
            terminator: EOF character to append to the end of the string
        """
        try:
            command = cmd + terminator
            sock.sendall(command.encode())
        except:
            print ("Error sending command", cmd, sys.exc_info()[0])
            
    # Special send command that formats data so it can be send to the stepper motor
    def _send_command_scl(self, sock, cmd):
        """
        Special version of _send_command that accommodates the amazingly weird
        terminator conventions that Applied Motion Products steppers motors use.
        
        Args:
            sock: Stepper motor socket object
            cmd: String to be sent
        """
        cmd = "\0\a" + cmd
        self._send_command(sock, cmd, terminator='\r')


    # read data and store in a string
    def _read_data(self, sock, printlen=False, timeout=2):
        """
        Read a string from a socket object.
        
        Args:
            sock: Socket to read from
            printlen: if true show the number of bytes read
            timeout: max time to wait for the socket to respond
            
        Returns:
            data: The data read from the socket as a string
        """
        data = ''
        while(select.select([sock], [], [], timeout) != ([], [], [])):
            buff = sock.recv(2048)
            data += buff.decode()
        if printlen: print ("received", len(data), "bytes")
        return data

class NetworkAnalyzerComm (SocketComm):
    """
    Object to communicate with the HP8757 C Network Analyzer.
    """

    def __init__(self, nwa_sock, nwa_points, nwa_span, nwa_power):
        """
        Handle all set-up tasks necessary so the Analyzer can receive commands and output data.
        
        It should be noted the Args for this contructor should be pulled from the config file,
        and not specified by hand.
        
        Args:
            nwa_sock: Socket where the Network Analyzer can be found
            nwa_points: Number of data points the NA will output when collecting a -single- set of data
            nwa_span: How wide the frequency window is for a -single- set of data, in MHz
            nwa_power: Power to set the RF source to, in dBm
        """
        super(NetworkAnalyzerComm, self).__init__()
        
        self.nwa_sock = nwa_sock

        self.__set_GPIB()
        self.__set_network_analyzer(nwa_points)
        self.__set_RF_mapping(nwa_span, nwa_power)
        self.print_purple("Setting GPIB convertor")

    def __set_GPIB(self):
        """
        Initialize the Prologix GPIB-ETHERNET Controller.
        """

        self.print_purple("Setting GPIB converter")
        
        # Set to network analyzer GPIB address
        self._send_command(self.nwa_sock, "++addr 16")
        # Disable Auto-Read
        self._send_command(self.nwa_sock, "++auto 0")
        # Enable EOI assertion at end of commands
        self._send_command(self.nwa_sock, "++eoi 1")
        # Append CR+LF to instrument commands
        self._send_command(self.nwa_sock, "++eos 0")
        
        self.print_green("GPIB converter set.")

    def __set_network_analyzer(self, nwa_points, do_avg=False):
        """
        Set all - Network Analyzer - parameters that will not change for the duration of the
        experiment. 
        
        Args:
            nwa_points: Number of data points the NA will output when collecting a -single- set of data
            do_avg: Should averaging be performed or not? Since by default we only collect data from a
             single signal sweep this is set to off by default.
        """

        self.print_purple("Setting network analyzer")
        # set active channel to 1
        self._send_command(self.nwa_sock, "C1")
        # turn cursor off
        self._send_command(self.nwa_sock, "CU0")
        # set cursor delta off
        self._send_command(self.nwa_sock, "CD0")
        # set data format to ascii
        self._send_command(self.nwa_sock, "FD0")
        # set number of points to nwa_points
        self._send_command(self.nwa_sock, "SP" + str(nwa_points))
        
        if do_avg == True:
            # turn on averaging if requested
            self._send_command(self.nwa_sock, "AF16")
        
        # self._send_command(nwa_sock, "++read 10")
        
        self.print_green("Network analyzer set")

    def __set_RF_mapping(self, nwa_span, nwa_power):
        
        """
        Set all - Signal Sweeper - parameters that will not change for the duration of the
        experiment.
        
        Args:
            nwa_span: How wide the frequency window is for a -single- set of data, in MHz
            nwa_power: Power to set the RF source to, in dBm
        """
        
        self.print_purple("setting up RF source")
        # set passthrough mode to RF source
        self._send_command(self.nwa_sock, "PT19")
        # change GPIB address to passthrough
        self._send_command(self.nwa_sock, "++addr 17")
        # RF output on
        print ("turning on RF")
        self._send_command(self.nwa_sock, "RF1")
        # set center frequency
        print ("setting frequency span " + str(nwa_span) + " MHz")
        # set frequency span
        self._send_command(self.nwa_sock, "DF " + str(nwa_span) + "MZ")
        # set power level
        self._send_command(self.nwa_sock, "PL " + str(nwa_power) + "DB")
        
        # provide short delay so network analyzer can set-up
        time.sleep(1)
        # return to network analyzer
        self._send_command(self.nwa_sock, "++addr 16")

    def collect_data(self, freq_centers):
        """
        Collect wide-scan data by stitching together data from several individual frequency windows.
        This is the main method used to collect power specta from the Network Analyzer.
        
        Args:
            freq_centers: List of frequencies where the individual frequency windows should be centered.
            Note that the frequency span used is set by the constructor parameter 'freq_span'
            
        Returns:
            Comma seperated power spectrum, returned as a single string
        """
        
        tmp_list = []
        
        for idx, val in enumerate(freq_centers):
            self.print_purple("Setting RF source " + str(idx + 1))
            # set passthrough mode to source
            self._send_command(self.nwa_sock, "PT19")
            # change GPIB address to passthrough, send commands to signal sweeper
            self._send_command(self.nwa_sock, "++addr 17")
        
            # set center frequency
            print ("setting center frequency to", val, " MHz")
            self._send_command(self.nwa_sock, "CF " + str(val) + "MZ")
            # set signal sweep time to 100ms (fastest possible)
            self._send_command(self.nwa_sock, "ST100MS")
            # provide short delay
            time.sleep(1)
        
            # return to network analyzer
            self._send_command(self.nwa_sock, "++addr 16")
        
            # turn off swept mode
            self._send_command(self.nwa_sock, "SW0")
            # set analyzer to perform exactly one sweep
            self._send_command(self.nwa_sock, "TS1")
            # give network analyzer time to complete sweep
            # this delay time needs to be much longer that what would appear obvious,
            # if the analyzer does not have time to complete a sweep we will gather the most recent
            # data set (usually the last data set or garbage)
            time.sleep(3)
        
            print ("Transferring data " + str(idx + 1))
            # take measurement
            # Input A absolute power measurement
            self._send_command(self.nwa_sock, "C1IA")
            self._send_command(self.nwa_sock, "C1OD")
            # allow time for data to be sent ( data output takes ~0.8 seconds in ASCII mode )
            time.sleep(1)
            self._send_command(self.nwa_sock, "++read 10")
        
            tmp_list.append(self._read_data(self.nwa_sock, printlen=True))
        
        return tmp_list

    def set_freq_window(self, frequency , span):
        
        # set passthrough mode to source
        self._send_command(self.nwa_sock, "PT19")
        # change GPIB address to passthrough, send commands to signal sweeper
        self._send_command(self.nwa_sock, "++addr 17")
        
        # set center frequency to frequency specified
        print ("Setting center frequency to", frequency, " MHz")
        self._send_command(self.nwa_sock, "CF " + str(round(frequency)) + "MZ")
        time.sleep(1)
        
        # set frequency window around center to specified span
        self._send_command(self.nwa_sock, "DF " + str(span) + "MZ")
        time.sleep(1)
        
        # return to network analyzer
        self._send_command(self.nwa_sock, "++addr 16")
        
    def take_data_single(self):
        
        # set passthrough mode to source
        self._send_command(self.nwa_sock, "PT19")
        # change GPIB address to passthrough, send commands to signal sweeper
        self._send_command(self.nwa_sock, "++addr 17")
        
        # set signal sweep time to 100ms (fastest possible)
        self._send_command(self.nwa_sock, "ST100MS")
        # provide short delay
        time.sleep(1)
        
        # return to network analyzer
        self._send_command(self.nwa_sock, "++addr 16")
        
        # turn off swept mode
        self._send_command(self.nwa_sock, "SW0")
        # set analyzer to perform exactly one sweep
        self._send_command(self.nwa_sock, "TS1")
        # give network analyzer time to complete sweeps
        time.sleep(3)
        
        print ("Transferring data...")
        # take measurement
        # Input A absolute power measurement
        self._send_command(self.nwa_sock, "C1IA")
        self._send_command(self.nwa_sock, "C1OD")
        # data output takes ~0.8 seconds in ASCII mode
        time.sleep(1)
        self._send_command(self.nwa_sock, "++read 10")
        
        return self._read_data(self.nwa_sock, printlen=True)
    
    def __set_RF_source(self, turn_on):
        
        self._send_command(self.nwa_sock, "PT19") # set passthrough mode to source
        self._send_command(self.nwa_sock, "++addr 17") # change GPIB address to passthrough
        
        if (turn_on == True):
            self._send_command(self.nwa_sock, "RF1") # turn on RF
        elif (turn_on == False):
            self._send_command(self.nwa_sock, "RF0") # turn off RF
        else:
            self.print_red("Bad command RF source not set.")
            
        self._send_command(self.nwa_sock, "++addr 16") # change back GPIB address to network analyzer
    
    def turn_off_RF_source(self):
        
        self.print_yellow("Turning off RF source.")
        self.__set_RF_source(False)
        
    def turn_on_RF_source(self):
        
        self.print_yellow("Turning on RF source.")
        self.__set_RF_source(True)

class StepperMotorComm (SocketComm):

    def __init__(self, addr_dict):
        super(StepperMotorComm, self).__init__()
        self.step_addr = self.__get_step_addr(addr_dict)
        
    def __get_step_addr(self, addr_dict):

        ip_addrs = addr_dict[0]
        port = addr_dict[1]
        
        return [ip_addrs, port]

    def __get_step_sock(self):

        ip_addrs = self.step_addr[0]
        port = self.step_addr[1]
        
        inst_name = "Stepper Motor"

        try:
            sock = self._socket_connect(ip_addrs, int(port))
            st = "Successfully connected to " + inst_name
            self.print_green(st)
            return sock
        except (IOError, ValueError) as exc:
            # some exception handling overlaps with _socket_connect, but we need to handle ValueError in the case of a bad port number
            st = "Problem generating socket object for " + inst_name + "!"+"Error was: "+ str(exc)
            self.print_red(st)
            return -1

    def __set_stepper_motor(self, step_sock, traverse_speed):

        self.print_purple("Setting stepper motor")
        # set 200 steps/rev
        self._send_command_scl(step_sock, "MR0")
        # set acceleration
        self._send_command_scl(step_sock, "AC"+str(traverse_speed))
        # set deceleration
        self._send_command_scl(step_sock, "DE"+str(traverse_speed))
        # set velocity
        self._send_command_scl(step_sock, "VE"+str(traverse_speed))
        
        self.print_green("Stepper motor set.")
        
    def set_to_initial_length(self, initial_length, current_length):
        
        self.print_purple("Moving to initial cavity length of "+str(initial_length))
        
        step_sock = self.__get_step_sock()
        self.__set_stepper_motor(step_sock, 5)
        
        delta_l = initial_length - current_length
        delta_steps = int(round(16*200*delta_l))
        
        self.print_yellow("Need to move "+str(delta_l))
        
        self._send_command_scl(step_sock, "FL" + str(delta_steps))
        delay_time = 2*abs(5/16*delta_l)
        time.sleep(delay_time)
        
        step_sock.close()
        
        

    def reset_cavity(self, len_of_tune):

        step_sock = self.__get_step_sock()
        self.__set_stepper_motor(step_sock, 5)

        rev = int(len_of_tune * -16)

        self.print_purple("Setting cavity back to initial length...")

        nsteps = int(rev * 200)

        print ("Moving motor ", rev, " Revolutions.")  # Movement will take", abs(duration), "seconds."
        self._send_command_scl(step_sock, "FL" + str(nsteps))

        step_sock.close()
        
    def panic_reset_cavity(self, iteration, revs_per_iter):

        rev = -1.0 * iteration * revs_per_iter
        nsteps = int(rev * 200)

        step_sock = self.__get_step_sock()
        self.__set_stepper_motor(step_sock, 5)

        self.print_red("Program halted! Resetting cavity to initial length.")
        print ("Moving motor " + str(abs(rev)) + " revolutions.")

        self._send_command_scl(step_sock, "FL" + str(nsteps))

        step_sock.close()

    def walk_loop(self, len_of_tune, revs, iters, num_of_iters):

        step_sock = self.__get_step_sock()
        self.__set_stepper_motor(step_sock, 1)

        print ("Iteration:", iters, " of ", num_of_iters, ".  Moving stepper", revs, "revolution(s).")
        itsteps = int(revs * 200)
        self._send_command_scl(step_sock, "FL" + str(itsteps))

        # wait for stepper motor to move
        time.sleep(revs)
        step_sock.close()
        
class SwitchComm ( SocketComm ):
    
    def __init__(self, switch_sock ):
        super(SwitchComm, self).__init__()
        self.switch_sock = switch_sock
        self.__set_voltages()
        
    def __set_voltages(self):
        self._send_command(self.switch_sock, "V1 28")
        self._send_command(self.switch_sock, "V2 28")
        
    def switch_to_signal_analyzer(self):
        self.print_purple("Switched to Signal Analyzer")
        self._send_command(self.switch_sock,"OP1 1")
        
    def switch_to_network_analyzer(self):
        self.print_purple("Switched to Network Analyzer")
        self._send_command(self.switch_sock,"OP1 0")
        
    def switch_to_transmission(self):
        self.print_purple("Switched to Transmission Measurements")
        self._send_command(self.switch_sock, "OP2 1")
        
    def switch_to_reflection(self):
        self.print_purple("Switched to Reflection Measurements")
        self._send_command(self.switch_sock, "OP2 0")
        
class ArduComm( SocketComm ):
    
    def __init__(self, ardu_sock ):
        super(ArduComm, self).__init__()
        self.ardu_sock = ardu_sock
        
    def get_cavity_length(self):
        self._send_command(self.ardu_sock, "LengthOfCavity")
        return float(self._read_data(self.ardu_sock, printlen=False).strip(' \t\n\r'))
        
class SignalAnalyzerComm( SocketComm ):
    
    def __init__(self, sa_sock ):
        super(SignalAnalyzerComm, self).__init__()
        self.sa_sock = sa_sock
    
    def set_signal_analyzer(self, center_freq, fft_length = 131072, freq_span = 10, num_averages = 20001):
        
        self.print_purple("Setting spectrum analyzer")
        
        #Set RF switch so that signal goes to Signal Analyzer
#         switch=self.sock_dict['switch']
#         self._send_command(switch, "OP1 1")
        
        #general configuration
        self._send_command(self.sa_sock, "INST:SEL BASIC") # set IQ analyzer mode
        self._send_command(self.sa_sock, "SPEC:DIF:BAND 10MHz") # set Digital IF Bandwidth
        self._send_command(self.sa_sock, "SPEC:DIF:FILT:TYPE FLAT") # set filter type to flattop
        self._send_command(self.sa_sock, "SPEC:FFT:WIND UNIF") # set FFT window to uniform
        self._send_command(self.sa_sock, "SPEC:FFT:LENG:AUTO OFF") # disable automatic FFT window and length control
        
        #Max size for FFT length is 131072
        #FFT length represents number of IQ pairs used to generate power spectrum
        #FFT length indirectly controls 'capture time'
        #Presumably this time is synonymous with integration time
        self._send_command(self.sa_sock, "SPEC:FFT:WIND:LENG "+str(fft_length)) # set FFT window length
        self._send_command(self.sa_sock, "SPEC:FFT:LENG "+str(fft_length)) # set FFT length
        
        #configure measurements
        self._send_command(self.sa_sock, "CONF:SPEC:NDEF") # configure measurement
        self._send_command(self.sa_sock, "FREQ:CENT "+str(center_freq)+"MHz") # set center frequency
        self._send_command(self.sa_sock, "SPEC:FREQ:SPAN "+str(freq_span)+"MHz") # set frequency span
        
        #configure averaging
        self._send_command(self.sa_sock, "SPEC:AVER:TYPE RMS") # set average type to power average
        self._send_command(self.sa_sock, "ACP:AVER:TCON EXP") # set averaging to non-repeating
        #Maximum number of averaged values is 20001
        self._send_command(self.sa_sock, "SPEC:AVER:COUN "+str(num_averages)) # set number of averages
        self._send_command(self.sa_sock, "INIT:CONT OFF") # turn off continuous measurement operation
        #Total integration time is given by time_per_frame(FFT length)*num_averages
        
        self.print_green("Spectrum analyzer set")

    def take_data_signal_analyzer(self):
        self.print_purple("Starting integration...")

        #Initialize measurement
        #This will start collecting and averaging samples
        self._send_command(self.sa_sock, "INIT:IMM")
        
        elapsed_time = 0.0

        # *OPC? will write "1\n" to the output when operation is complete.
        while True:
            #Poll the signal analyzer
            self._send_command(self.sa_sock, "*OPC?")
            status_str = self._read_data(self.sa_sock, printlen=False, timeout=0.5)
            
            #Wait until *OPC? returns '1\n' indicating that the requested number
            #of samples have been collected
            if(status_str == "1\n"):
                print ("\nIntegration complete")
                break
            else:
                elapsed_time += dt.datetime.now().microsecond
#                 print ("\rWaiting, time elapsed: "+str(round(elapsed_time/1e6))+ " seconds")
                status = "\rWaiting, time elapsed: "+str(round(elapsed_time/1e6))+ " seconds"
                sys.stdout.write(status)
                sys.stdout.flush()

        #Since measurement is already initliazed collect data with the
        #FETC(h) command
        self._send_command(self.sa_sock, ":FETC:SPEC7?")
        raw_sa_data = self._read_data(self.sa_sock, printlen=True, timeout=0.5)
        
        return raw_sa_data

#         out_file=open(self.data_dict['file_name'],'a')
# 
#         print(raw_sa_data, end="\n", file=out_file)
#         out_str="Wrote data to "+self.data_dict['file_name']
#         funcs.c_print(out_str,"Green")
#  
#         out_file.close()
