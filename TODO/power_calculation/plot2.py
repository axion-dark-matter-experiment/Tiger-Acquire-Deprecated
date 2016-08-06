# plot2.py filename
# Program to make a plot of some data
# Ari Brill 7/25/14

import sys
import numpy as np
import matplotlib.pyplot as plt

try:
    filename = sys.argv[1]
except:
    print "usage: plot2.py filename"

data = np.loadtxt(filename, delimiter=',')
xdata = data[:,0]
ydata = data[:,1]

plt.clf()
plt.plot(xdata, ydata, 'o')
plt.plot(xdata, 1024*2*xdata/2E7, 'r')
#plt.xlabel("Number of averages")
#plt.ylabel("(mu/sigma)^2")
plt.show()
