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

data = np.loadtxt(filename, delimiter=' ')
plt.clf()

if filename == "power_spectrum.txt":
    frequency = data[:,0]
    power = data[:,1]
    uncertainty = data[:,2]
    plt.errorbar(frequency, power, yerr=uncertainty, color="Black",\
            linestyle="None")
    plt.plot(frequency, power, 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Power (W)")

if filename == "single_scan_g_prediction.txt":
    frequency = data[:,0]
    g = data[:,1]
    uncertainty = data[:,2]
    plt.errorbar(frequency, g, yerr=uncertainty, color="Black",\
            linestyle="None")
    plt.plot(frequency, g, 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("g Prediction (GeV^-2)")

if filename == "sensitivity.txt":
    frequency = data[:,0]
    g_sensitivity = data[:,1]
    plt.plot(frequency, g_sensitivity, 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("g Sensitivity (GeV^-1)")

if filename == "limits.txt":
    frequency = data[:,0]
    limits = data[:,1]
    uncertainty = data[:,2]
    plt.errorbar(frequency, limits, yerr=uncertainty, color="Black",\
            linestyle="None")
    plt.plot(frequency, limits, 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("Limits on g")

ax = plt.gca()
ax.ticklabel_format(useOffset=False)
plt.ticklabel_format(style='sci', scilimits=(0,0), axis='y')
plt.show()
