#!/usr/bin/env python3.4

import mode_tracking as mt

import sys #basic std library functions
import argparse

parser = argparse.ArgumentParser(description='Control code for Electric Tiger.')
parser.add_argument('-M','--mode_map', help='Build a mode map (i.e. map of transmitted power.)',action='store_true')
parser.add_argument('-R','--reflection_map', help='Build a map of reflected power.',action='store_true')
parser.add_argument('-T','--modetrack', help='Experimental mode to test the modetracking module.',action='store_true')
args = parser.parse_args()


#argv = sys.argv
argv="/home/bephillips2/workspace/Electric-Tiger/Control_Code/ETigConfig.txt"#temporary stand-in for command line input

def main():

	meta_tig=mt.ModeTrackProgram(argv)
	meta_tig.program()

if __name__ == "__main__":
    main()
