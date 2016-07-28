#!/usr/bin/env python3.4

import socket_communicators as sc
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
        self.step_sock = self._socket_connect(host, port)
        
    def __call__(self, tune_length, haste):
        self.__move_step(tune_length, haste)

    def __move_step(self, tune_length, haste_on = False): 
            
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
    
        print ("Moving motor "+ str(abs(rev))+" revolutions.")
    
        self._send_command_scl(self.step_sock, "FL"+str(nsteps))
    
        self.step_sock.close()

def main():
    
    step_mover = StepperMover()

    if(args.extend):
        step_mover(args.travel,args.haste)
    elif(args.retract):
        step_mover(-1*args.travel,args.haste)

if __name__ == "__main__":
    main()
