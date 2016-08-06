# power.py
# Program to calculate number of averages performed on data from average power
# Written by Ari Brill 7/25/14

import numpy as np

# load data
data = np.loadtxt("power_data.csv", delimiter=',')
#real_data = data[:,0]
#complex_data = data[:,1]

# convert to absolute units
power = 10**(data/10)

# calculate power
#power = real_data**2 + complex_data**2
#power = data**2

# get mean
mean = np.mean(power)

# calculate standard deviation
std = np.std(power)

# calculate N
N = (mean/std)**2

print mean
print std
print N

