# socket_connect.py
# Functions for connecting to remote machines

import socket
import sys
import select
import time  # sleep
import color_printer as cp


class SocketComm:

    def socket_connect(self, host, port):

        # get host info using supplied host and port
        try:
            sockinfo = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        except OSError:
            print ("Socket Connect: could not get host info.")
            return None

        # connect to first socket we can
        for sock in sockinfo:
            try:
                s = socket.socket(sock[0], sock[1], sock[2])
                s.settimeout(5)  # set socket time-out to 5 seconds, default is ~120 seconds
                s.connect((host, port))
                print ("Socket Connect: connected to", s.getpeername()[0])
                return s
            except (IOError, ValueError) as exc:
                print ("Socket Connect: Could not connect to socket.")
                # raise the same errors that tripped socket_connect so functioned that
                # caller is aware of the error
                raise exc
                return None

    # send a string to the device connected on the socket
    def send_command(self, sock, cmd, terminator='\n'):
        try:
            command = cmd + terminator
            sock.send(command.encode())
        except:
            print ("Error sending command", cmd, sys.exc_info()[0])

    # send a command of arbitary length to socket
    # entire command will be sent until finished or an error occurs
    # unlike send_command the socket will not time-our or end prematurely
    def send_command_long(self, sock, cmd, terminator='\n'):
        try:
            command = cmd + terminator
            sock.sendall(command.encode())
        except:
            print ("Error sending command", cmd, sys.exc_info()[0])

    # read data and store in a string
    def read_data(self, sock, printlen=False, timeout=2):
        data = ''
        while(select.select([sock], [], [], timeout) != ([], [], [])):
            buff = sock.recv(2048)
            data += buff.decode()
        if printlen: print ("received", len(data), "bytes")
        return data

    # Special send command that formats data so it can be send to the stepper motor
    def send_command_scl(self, sock, cmd):
        cmd = "\0\a" + cmd
        self.send_command(sock, cmd, terminator='\r')

class NetworkAnalyzerComm (SocketComm):

    def __init__(self, nwa_sock):
        
        self.nwa_sock = nwa_sock

        self.__set__GPIB()
        self.__set_network_analyzer()
        self.__set_RF_mapping()
        
        self.print_green = cp.ColorPrinter("Green")
        self.print_purple = cp.ColorPrinter("Purple")
        self.print_yellow = cp.ColorPrinter("Yellow")
        self.print_red = cp.ColorPrinter("Red")

    def __set_GPIB(self):

        self.print_purple("Setting GPIB converter")
        # set to network analyzer GPIB address
        self.send_command(self.nwa_sock, "++addr 16")
        # disable auto-read
        self.send_command(self.nwa_sock, "++auto 0")
        # enable EOI assertion at end of commands
        self.send_command(self.nwa_sock, "++eoi 1")
        # append CR+LF to instrument commands
        self.send_command(self.nwa_sock, "++eos 0")
        
        self.print_green("GPIB converter set.")

    def __set_network_analyzer(self, nwa_points, do_avg=False):

        self.print_purple("Setting network analyzer")
        # set active channel to 1
        self.send_command(self.nwa_sock, "C1")
        # turn cursor off
        self.send_command(self.nwa_sock, "CU0")
        # set cursor delta off
        self.send_command(self.nwa_sock, "CD0")
        # set data format to ascii
        self.send_command(self.nwa_sock, "FD0")
        # set number of points to nwa_points
        self.send_command(self.nwa_sock, "SP" + str(nwa_points))
        
        if do_avg == True:
            # turn on averaging if requested
            self.send_command(self.nwa_sock, "AF16")
        
        # self.send_command(nwa_sock, "++read 10")
        
        self.print_green("Network analyzer set")

    def __set_RF_mapping(self, switch, nwa_span, nwa_power):

        # Make sure first switch is directing signal to the network analyzer
        # instead of the signal analyzer
        self.print_purple("Sending signal to Network Analyzer")
        # switch actuation voltage is 28 volts
        self.send_command(switch, "V2 28")
        # switch needs to be off to send signal to network analyzer
        self.send_command(switch, "OP1 0")
        
        self.print_purple("setting up RF source")
        # set passthrough mode to RF source
        self.send_command(self.nwa_sock, "PT19")
        # change GPIB address to passthrough
        self.send_command(self.nwa_sock, "++addr 17")
        # RF output on
        print ("turning on RF")
        self.send_command(self.nwa_sock, "RF1")
        # set center frequency
        print ("setting frequency span " + str(nwa_span) + " MHz")
        # set frequency span
        self.send_command(self.nwa_sock, "DF " + str(nwa_span) + "MZ")
        # set power level
        self.send_command(self.nwa_sock, "PL " + str(nwa_power) + "DB")
        
        # provide short delay so network analyzer can set-up
        time.sleep(1)
        # return to network analyzer
        self.send_command(self.nwa_sock, "++addr 16")

    def collect_data(self, freq_centers):
        
        tmp_list = []
        
        for idx, val in enumerate(freq_centers):
            self.print_purple("Setting RF source " + str(idx + 1))
            # set passthrough mode to source
            self.send_command(self.nwa_sock, "PT19")
            # change GPIB address to passthrough, send commands to signal sweeper
            self.send_command(self.nwa_sock, "++addr 17")
        
            # set center frequency
            print ("setting center frequency to", val, " MHz")
            self.send_command(self.nwa_sock, "CF " + str(val) + "MZ")
            # set signal sweep time to 100ms (fastest possible)
            self.send_command(self.nwa_sock, "ST100MS")
            # provide short delay
            time.sleep(1)
        
            # return to network analyzer
            self.send_command(self.nwa_sock, "++addr 16")
        
            # turn off swept mode
            self.send_command(self.nwa_sock, "SW0")
            # set analyzer to perform exactly five sweeps
            self.send_command(self.nwa_sock, "TS1")
            # give network analyzer time to complete sweeps
            time.sleep(3)
        
            print ("Transferring data " + str(idx + 1))
            # take measurement
            # Input A absolute power measurement
            self.send_command(self.nwa_sock, "C1IA")
            self.send_command(self.nwa_sock, "C1OD")
            # data output takes ~0.8 seconds in ASCII mode
            time.sleep(1)
            self.send_command(self.nwa_sock, "++read 10")
        
            tmp_list.append(self.read_data(self.nwa_sock, printlen=True))
        
        return tmp_list

    def set_freq_window(self, frequency , span):
        # set passthrough mode to source
        self.send_command(self.nwa_sock, "PT19")
        # change GPIB address to passthrough, send commands to signal sweeper
        self.send_command(self.nwa_sock, "++addr 17")
        
        # set center frequency to frequency specified
        print ("Setting center frequency to", frequency, " MHz")
        self.send_command(self.nwa_sock, "CF " + str(round(frequency)) + "MZ")
        time.sleep(1)
        
        # set frequency window around center to specified span
        self.send_command(self.nwa_sock, "DF " + str(span) + "MZ")
        time.sleep(1)
        
        # return to network analyzer
        self.send_command(self.nwa_sock, "++addr 16")
        
    def take_data_single(self):
        
        # set passthrough mode to source
        self.send_command(self.nwa_sock, "PT19")
        # change GPIB address to passthrough, send commands to signal sweeper
        self.send_command(self.nwa_sock, "++addr 17")
        
        # set signal sweep time to 100ms (fastest possible)
        self.send_command(self.nwa_sock, "ST100MS")
        # provide short delay
        time.sleep(1)
        
        # return to network analyzer
        self.send_command(self.nwa_sock, "++addr 16")
        
        # turn off swept mode
        self.send_command(self.nwa_sock, "SW0")
        # set analyzer to perform exactly one sweep
        self.send_command(self.nwa_sock, "TS1")
        # give network analyzer time to complete sweeps
        time.sleep(3)
        
        print ("Transferring data...")
        # take measurement
        # Input A absolute power measurement
        self.send_command(self.nwa_sock, "C1IA")
        self.send_command(self.nwa_sock, "C1OD")
        # data output takes ~0.8 seconds in ASCII mode
        time.sleep(1)
        self.send_command(self.nwa_sock, "++read 10")
        
        return self.read_data(self.nwa_sock, printlen=True)

class StepperMotorComm (SocketComm):

    def __init__(self, addr_dict):
        self.step_addr = self.__get_step_addr(addr_dict)
        
        self.print_green = cp.ColorPrinter("Green")
        self.print_purple = cp.ColorPrinter("Purple")
        self.print_yellow = cp.ColorPrinter("Yellow")
        self.print_red = cp.ColorPrinter("Red")
        
    def __get_step_addr(self, addr_dict):
        ip_addrs = addr_dict['step'][0]
        port = addr_dict['step'][1]
        
        return [ip_addrs, port]

    def __get_step_sock(self):

        ip_addrs = self.step_addr[0]
        port = self.step_addr[1]
        
        inst_name = "Stepper Motor"

        try:
            sock = self.socket_connect(ip_addrs, int(port))
            st = "Successfully connected to " + inst_name
            self.print_green(st)
            return sock
        except (IOError, ValueError) as exc:
            # some exception handling overlaps with socket_connect, but we need to handle ValueError in the case of a bad port number
            st = "Problem generating socket object for " + inst_name + "!"+"Error was: "+ str(exc)
            self.print_red(st)
            return -1

    def __set_stepper_motor(self, step_sock):
        
        step_sock = self.get_step_sock()

        self.print_purple("Setting stepper motor")
        # set 200 steps/rev
        self.send_command_scl(step_sock, "MR0")
        # set acceleration
        self.send_command_scl(step_sock, "AC1")
        # set deceleration
        self.send_command_scl(step_sock, "DE1")
        # set velocity
        self.send_command_scl(step_sock, "VE0.5")
        
        self.print_green("Stepper motor set.")

    def reset_cavity(self, step_sock, len_of_tune):

        self.set_stepper_motor(step_sock)

        rev = int(len_of_tune * -16)

        self.print_purple("Setting cavity back to initial length...")

        nsteps = int(rev * 200)

        # set steps per revolution to 200 steps/revolution
        self.send_command_scl(step_sock, "MR0")
        # set acceleration
        self.send_command_scl(step_sock, "AC1")
        # set deceleration
        self.send_command_scl(step_sock, "DE1")
        # set velocity
        self.send_command_scl(step_sock, "VE1.5")
        print ("Moving motor ", rev, " Revolutions.")  # Movement will take", abs(duration), "seconds."
        self.send_command_scl(step_sock, "FL" + str(nsteps))
        self.send_command_scl(step_sock, "VE.5")

        step_sock.close()

    def walk_loop(self, step, len_of_tune, revs, iters, num_of_iters):

        self.__set_stepper_motor(step)

        print ("Iteration:", iters, " of ", num_of_iters, ".  Moving stepper", revs, "revolution(s).")
        itsteps = int(revs * 200)
        self.send_command_scl(step, "FL" + str(itsteps))
        self.send_command_scl(step, "VE.5")
        # wait for stepper motor to move
        time.sleep(revs)
        step.close
        
class SignalAnalyzerComm( SocketComm ):
    
    def __init__(self, sock_dict):
    
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
