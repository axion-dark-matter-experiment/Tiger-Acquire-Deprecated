#!/usr/bin/env python3.4

import socket_connect_2 as sc
import argparse

parser = argparse.ArgumentParser(description='Manually tune the length of the cavity.')
parser.add_argument('-X','--extend', help='Extend the cavity (e.g. make longer)',action='store_true')
parser.add_argument('-R','--retract', help='Retract the cavity (e.g. make shorter)',action='store_true')
parser.add_argument('-H','--haste', help='Move the cavity quickly (5x faster than usual)',action='store_true')
parser.add_argument('travel', type=float, help='Distance to tune the cavity (in inches).')
args = parser.parse_args()

def move_step(tune_length, haste_on = False):
    rev = tune_length * 16
    step = sc.socket_connect("10.95.100.177", 7776)

    nsteps = int(rev*200)
    # set steps per revolution to 200 steps/revolution
    sc.send_command_scl(step, "MR0")

    if(haste_on):
        # Acceleration of 5 rev/s/s
        sc.send_command_scl(step, "AC5")
        # Deceleration of 5 rev/s/s
        sc.send_command_scl(step, "DE5")
        # Velocity of 5 rev/s
        sc.send_command_scl(step, "VE5")

    else:
        # Acceleration of 1 rev/s/s
        sc.send_command_scl(step, "AC1")
        # Deceleration of 1 rev/s/s
        sc.send_command_scl(step, "DE1")
        # Velocity of 80 rev/s
        sc.send_command_scl(step, "VE1")

    print ("Moving motor "+ str(abs(rev))+" revolutions.")

    sc.send_command_scl(step, "FL"+str(nsteps))

    step.close()

def main():

    if(args.extend):
        move_step(args.travel,args.haste)
    elif(args.retract):
        move_step(-1*args.travel,args.haste)

if __name__ == "__main__":
    main()
