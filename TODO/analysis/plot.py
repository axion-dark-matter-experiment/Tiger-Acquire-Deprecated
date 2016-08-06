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
    plt.title("Flattened Power Spectrum")

if filename == "single_scan_g_prediction.txt":
    frequency = data[:,0]
    g = data[:,1]
    uncertainty = data[:,2]
    plt.errorbar(frequency, g, yerr=uncertainty, color="Black",\
            linestyle="None")
    plt.plot(frequency, g, 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel(r"(G$_\mathrm{a\gamma\gamma}$)$^2$ Prediction (GeV$^{-2}$)")
    plt.title("Predicted Axion Coupling for a Single Scan")

if filename == "grand_g_prediction.txt":
    frequency = data[:,0]
    g = data[:,1]
    uncertainty = data[:,2]
    plt.errorbar(frequency[::80], g[::80], yerr=uncertainty[::80],\
            color="Black", linestyle="None")
    plt.plot(frequency[::80], g[::80], 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel(r"(G$_\mathrm{a\gamma\gamma}$)$^2$ Prediction (GeV$^{-2}$)")
    plt.title("Predicted Axion Coupling for All Scans")

if filename == "sensitivity.txt":
    frequency = data[:,0]
    g_sensitivity = data[:,1]
    plt.plot(frequency, g_sensitivity, 'o')
    plt.xlabel("Frequency (MHz)")
    plt.ylabel("g Sensitivity (1/GeV)")

if filename == "limits.txt":
    frequency = data[:,0]
    limits = data[:,1]
    full_left, full_right = 16300, 17700
    full_frequency = np.arange(full_left,full_right,5)

    top = np.ones(len(frequency))*1e-4
    full_top = np.ones(len(full_frequency))*1e-4
    alps_limits = np.ones(len(full_frequency))*6e-8
    cast_limits = np.ones(len(full_frequency))*2.3e-10
    qcd_upper_limit = np.ones(len(full_frequency))*3.354e-14
    qcd_lower_limit = np.ones(len(full_frequency))*4.870e-15

    fig, ax1 = plt.subplots()
    ax1 = fig.add_subplot(111)

    ax1.plot(frequency, limits, ls='steps')
    ax1.plot(full_frequency, alps_limits, color='#61D480')
    ax1.plot(full_frequency, cast_limits, color='#F55F62')
    ax1.plot(full_frequency, qcd_upper_limit, '--k')
    ax1.plot(full_frequency, qcd_lower_limit, '--k')
    
    ax2 = ax1.twiny()
    ax1Xs = ax1.get_xticks()

    ax2Xs = []
    h = 4.135667516e-15
    for X in ax1Xs:
        ax2Xs.append(round(X*1e6*h*1e6,2))

    ax2.set_xticks(ax1Xs)
    ax2.set_xbound(ax1.get_xbound())
    ax2.set_xticklabels(ax2Xs)

    ax1.set_xlim([full_left, full_right])
    ax1.set_ylim([1e-15, 1e-4])
    ax1.set_yscale('log')

    ax1.set_xlabel("Frequency (MHz)")
    ax2.set_xlabel(r"Axion Mass ($\mu$eV)")
    ax1.set_ylabel(r"|G$_\mathrm{a\gamma\gamma}$| Limit (GeV$^{-1}$)")
    ax1.set_title("Axion Coupling Limits").set_y(1.1)

    ax1.fill_between(full_frequency, cast_limits, full_top, interpolate=True,
            color='#F55F62')
    ax1.fill_between(full_frequency, alps_limits, full_top, interpolate=True,
            color='#61D480')
    ax1.fill_between(frequency, limits, top, interpolate=True, color='b',
            zorder=10)

    fig.subplots_adjust(top=0.85)

#plt.gca().ticklabel_format(useOffset=False)
#plt.ticklabel_format(style='sci', scilimits=(0,0), axis='y')
plt.show()
