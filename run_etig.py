#!/usr/bin/env python3.5

import mode_track_program as mode_tracker
import map_programs as map_builders

import argparse

parser = argparse.ArgumentParser(description='Control code for Electric Tiger.')
parser.add_argument('-M', '--mode_map', help='Build a mode map (i.e. map of transmitted power.)', action='store_true')
parser.add_argument('-R', '--reflection_map', help='Build a map of reflected power.', action='store_true')
parser.add_argument('-T', '--modetrack', help='Main program for collecting data.', action='store_true')
args = parser.parse_args()


# argv = sys.argv
argv = "/home/bephillips2/workspace/Electric_Tiger_Control_Code/ETigConfig2.txt"  # temporary stand-in for command line input

def main():

	
	if(args.mode_map):
		meta_tig = map_builders.ModeMapProgram(argv)
	elif(args.reflection_map):
		meta_tig = map_builders.ReflectionMapProgram(argv)
	elif(args.modetrack):
		meta_tig = mode_tracker.ModeTrackProgram(argv)
		
	meta_tig.program()

if __name__ == "__main__":
	main()
