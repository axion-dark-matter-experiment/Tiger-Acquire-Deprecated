# plot.py filename
# Program to make a plot of some data
# Ari Brill 7/25/14

import sys
import numpy as np
import matplotlib.pyplot as plt

try:
    filename = sys.argv[1]
except:
    print "usage: plot.py filename"

data = np.loadtxt(filename, delimiter=',')
power = 10**(data/10)

plt.clf()
plt.plot(power, 'o')
#plt.xlabel("Number of averages")
#plt.ylabel("(mu/sigma)^2")
plt.show()
