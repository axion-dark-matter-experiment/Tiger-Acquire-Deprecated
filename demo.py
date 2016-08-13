#!/usr/bin/env python3.5

import program_core
import time

argv = "/home/bephillips2/workspace/Electric_Tiger_Control_Code/ETigConfig.txt"

def main():

    
    meta_tig = program_core.ProgramCore(argv)
    
    while True:
        print( "Attempting to get cavity length...")
        print( meta_tig.ardu_comm.get_cavity_length() )
        time.sleep(1)

if __name__ == "__main__":
    main()
