# calculate_veff.py frequency w0 bfield_file
# Program to calculate the effective volume of the Orpheus resonator
# Written by Ari Brill 8/18/14

import numpy as np
import os.path
import sys

# check command line arguments
argv = sys.argv
argc = len(argv)

if argc != 4:
    print "usage: calculate_veff.py frequency w0 bfield_file"
    sys.exit()

try:
    frequency = float(argv[1]) # MHz
    w0 = float(argv[2]) # m
except ValueError:
    print "usage: frequency and w0 must be floats"
    sys.exit()

bfield_file = argv[3]
if not os.path.isfile(bfield_file):
    print "error: file", bfield_file, "not found"
    sys.exit()

# load bfield data
bfield_data = np.loadtxt(bfield_file, delimiter=',')
zpoints = bfield_data[:,0]
bfield = bfield_data[:,1]

# normalize zpoints to be distance from resonator center
zpoints -= 0.1
# normalize bfield to have maximum = 1
bfield /= np.max(bfield)

# define constants and parameters
c = 299792458 # m/s
k = 2*np.pi*frequency*1e6/c
z0 = (k*w0**2)/2
r = zpoints*(1 + z0**2/zpoints**2)
phi = np.arctan(zpoints/z0)
w = w0*np.sqrt(1 + (zpoints**2/z0**2))
rho = 0.05

# calculate efield at center
efield = (w0/w)*np.exp(-1*rho**2/w**2)*np.exp(-1j*(k*zpoints-phi)-1j*(k*rho**2)/(2*r))
efield = efield.real

print bfield*efield
