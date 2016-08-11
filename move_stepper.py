#!/usr/bin/env python3.5

import socket_communicators as sc
import color_printer as cp
import argparse

parser = argparse.ArgumentParser(description='Manually tune the length of the cavity.')
parser.add_argument('-X','--extend', help='Extend the cavity (e.g. make longer)',action='store_true')
parser.add_argument('-R','--retract', help='Retract the cavity (e.g. make shorter)',action='store_true')
parser.add_argument('-H','--haste', help='Move the cavity quickly (5x faster than usual)',action='store_true')
parser.add_argument('travel', type=float, help='Distance to tune the cavity (in inches).')
args = parser.parse_args()

class StepperMover (sc.SocketComm):
    
    def __init__(self, host = "10.95.100.177", port = 7776):
        super(StepperMover, self).__init__()
        
        self.print_green = cp.ColorPrinter("Green")
        self.print_red = cp.ColorPrinter("Red")
        
        self.step_sock = self._socket_connect( "10.95.100.177" , 7776)
        
        self.ardu_sock = self._socket_connect( "10.66.192.41" , 23)
        self.ardu_comm = sc.ArduComm(self.ardu_sock)
        
    def __call__(self, tune_length, haste):
        self.__move_step(tune_length, haste)
        
    def __err_message(self, requested_cavity_length):
        message = "Requested cavity length of "
        message += str(requested_cavity_length)
        message +=" is outside of reasonable bounds.\n"
        message +="Aborting!"
        
        self.print_red( message )
        
    def __confirm_message(self, requested_cavity_length):
        message = "Tuning cavity to "
        message += str(requested_cavity_length)
        message += " inches."
        
        self.print_green( message )
        
    def __sanity_check(self, requested_tune_length):
        
        current_length = self.ardu_comm.get_cavity_length()
        requested_cavity_length = current_length + requested_tune_length
        
        if( requested_cavity_length <= 4.5 or requested_cavity_length >= 11):
            self.__err_message(requested_cavity_length)
            return False
        else:
            self.__confirm_message(requested_cavity_length)
            return True
        
    def __close_sockets(self):
        self.step_sock.close()
        self.ardu_sock.close()
        

    def __move_step(self, tune_length, haste_on = False): 
        
        if ( not self.__sanity_check(tune_length)):
            self.__close_sockets()
            return
            
        rev = tune_length * 16
    
        nsteps = int(rev*200)
        # set steps per revolution to 200 steps/revolution
        self._send_command_scl(self.step_sock, "MR0")
    
        if(haste_on):
            # Acceleration of 5 rev/s/s
            self._send_command_scl(self.step_sock, "AC5")
            # Deceleration of 5 rev/s/s
            self._send_command_scl(self.step_sock, "DE5")
            # Velocity of 5 rev/s
            self._send_command_scl(self.step_sock, "VE5")
    
        else:
            # Acceleration of 1 rev/s/s
            self._send_command_scl(self.step_sock, "AC1")
            # Deceleration of 1 rev/s/s
            self._send_command_scl(self.step_sock, "DE1")
            # Velocity of 80 rev/s
            self._send_command_scl(self.step_sock, "VE1")
    
        self._send_command_scl(self.step_sock, "FL"+str(nsteps))
        
        self.__close_sockets()

def main():
    
    step_mover = StepperMover()

    if(args.extend):
        step_mover(args.travel,args.haste)
    elif(args.retract):
        step_mover(-1*args.travel,args.haste)

if __name__ == "__main__":
    main()
