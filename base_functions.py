"""
Modules of functions that are used by all three principal classes-
ModeTracking, ModeMap, and ReflectionMap.

Each class utilizes these functions but does -not- inherit from this
module directly.

Functions
"""

import socket_connect_2 as sc
import time  # time.sleep()
import re  # re.split
from scipy.optimize import leastsq  # least squares curve fitting
import numpy as np  # numpy arrays
import matplotlib.pyplot as plt  # accursed matplotlib functions

def lorentzian(x, p):
	"""Calculate Lorentz Line Shape.

	Used for determining Q of a particular peak.

	Args:
		p:List of parameters of the form [HWHM, Center, Height]
	"""
	numerator = p[0] ** 2
	denominator = (x - p[1]) ** 2 + p[0] ** 2
	return p[2] * (numerator / denominator)

# check whether parameters [HWHM, center, height] are within reasonable bounds
def within_bounds(p, center_freq, freq_window):
	"""
	Check whether values for Lorentzian best fit curve are within reasonable
	bounds.

	Args:
		p:List of parameters
        center_freq: Center of the frequency window where the Lorentzian will be fitted
        freq_window: Width of of the frequency window centered at center_freq
		class.

	Returns:
		True if within reasonable bounds, False otherwise
	"""

	if p[0] < 0 or p[0] > freq_window:
		return False
	if (p[1] < center_freq - freq_window or p[1] > center_freq + freq_window):
		return False
	return True

# calculate residuals of fitted curve
def residuals(p, y, x, center_freq, freq_window):
	if within_bounds(p, center_freq, freq_window):
		err = y - lorentzian(x, p)
		return err
	else:
		return 1e6

def fit_lorentzian(fit_data, center_freq, freq_window):

	nwa_fit_data = fit_data
	nwa_points = len(fit_data)
	actual_center_freq = center_freq

	print ("Fitting data")
	try:
		nwa_yw = [float(y) for y in fit_data]
	except ValueError as exc:
		print ("Could not convert to float: ", exc)

	# convert from dBm to power (mW)
	nwa_yw = [10.**(y / 10) for y in nwa_yw]
	# get x values from center frequency and span
	nwa_xw = [(actual_center_freq - (freq_window / 2) + \
			freq_window * (float(x) / nwa_points)) for x in range(nwa_points)]
	# convert to arrays
	nwa_xw = np.array(nwa_xw)
	nwa_yw = np.array(nwa_yw)

	# define middle values to fit to
	middle = ((2 * nwa_points / 5 < np.arange(nwa_points)) & 
			(np.arange(nwa_points) < 3 * nwa_points / 5))
	# initial values for fit: [HWHM, peak center, height]
	p = [25.0, actual_center_freq, nwa_yw[nwa_points / 2]]
	pbest = leastsq(residuals, p, args=(nwa_yw[middle], nwa_xw[middle], center_freq, freq_window))[0]

	fitted_hwhm = pbest[0]
	fitted_center_freq = pbest[1]
	fitted_center_freq_step = fitted_center_freq + 20

	fitted_height = pbest[2]
	fitted_q = fitted_center_freq / (fitted_hwhm * 2)
	# convert back to dBm
	fitted_height = 10 * np.log10(fitted_height)

	nwa_y_dbmw = [10 * np.log10(y) for y in nwa_yw]

	# report parameters
	c_print("Parameters:", "Purple")

	out_str = "Fitted Q: " + str(fitted_q) + "\nFitted center frequency (MHz): "\
	+ str(fitted_center_freq) + "\nFitted height (dBm): " + str(fitted_height)

	c_print(out_str, "Yellow")

	output_triple = [fitted_q, fitted_center_freq, fitted_height]

	return output_triple

def c_print(message, color):
    if(color == "Purple"):
        print ('\033[95m' + str(message) + '\033[0m')
    elif(color == "Green"):
        print ('\033[92m' + str(message) + '\033[0m')
    elif(color == "Blue"):
        print ('\033[94m' + str(message) + '\033[0m')
    elif(color == "Yellow"):
        print ('\033[93m' + str(message) + '\033[0m')
    elif(color == "Red"):
        print ('\033[91m' + str(message) + '\033[0m')
    else:
        print(str(message))

def set_GPIB(nwa_sock):

	c_print("Setting GPIB converter", "Purple")
	# set to network analyzer GPIB address
	sc.send_command(nwa_sock, "++addr 16")
	# disable auto-read
	sc.send_command(nwa_sock, "++auto 0")
	# enable EOI assertion at end of commands
	sc.send_command(nwa_sock, "++eoi 1")
	# append CR+LF to instrument commands
	sc.send_command(nwa_sock, "++eos 0")

	c_print("GPIB converter set.", "Green")

def set_network_analyzer(nwa_sock, nwa_points, do_avg=False):

	c_print("Setting network analyzer", "Purple")
	# set active channel to 1
	sc.send_command(nwa_sock, "C1")
	# turn cursor off
	sc.send_command(nwa_sock, "CU0")
	# set cursor delta off
	sc.send_command(nwa_sock, "CD0")
	# set data format to ascii
	sc.send_command(nwa_sock, "FD0")
	# set number of points to nwa_points
	sc.send_command(nwa_sock, "SP" + str(nwa_points))

	if do_avg == True:
		# turn on averaging if requested
		sc.send_command(nwa_sock, "AF16")

	# sc.send_command(nwa_sock, "++read 10")

	c_print("Network analyzer set", "Green")

def set_RF_mapping(nwa_sock, switch, nwa_span, nwa_power):

	# Make sure first switch is directing signal to the network analyzer
	# instead of the signal analyzer
	c_print("Sending signal to Network Analyzer", "Purple")
	# switch actuation voltage is 28 volts
	sc.send_command(switch, "V2 28")
	# switch needs to be off to send signal to network analyzer
	sc.send_command(switch, "OP1 0")

	c_print("setting up RF source", "Purple")
	# set passthrough mode to RF source
	sc.send_command(nwa_sock, "PT19")
	# change GPIB address to passthrough
	sc.send_command(nwa_sock, "++addr 17")
	# RF output on
	print ("turning on RF")
	sc.send_command(nwa_sock, "RF1")
	# set center frequency
	print ("setting frequency span " + str(nwa_span) + " MHz")
	# set frequency span
	sc.send_command(nwa_sock, "DF " + str(nwa_span) + "MZ")
	# set power level
	sc.send_command(nwa_sock, "PL " + str(nwa_power) + "DB")

	# provide short delay so network analyzer can set-up
	time.sleep(1)
	# return to network analyzer
	sc.send_command(nwa_sock, "++addr 16")

def collect_data(nwa_sock, nominal_centers):

    tmp_list = []

    for idx, val in enumerate(nominal_centers):
        c_print("Setting RF source " + str(idx + 1), "Purple")
        # set passthrough mode to source
        sc.send_command(nwa_sock, "PT19")
        # change GPIB address to passthrough, send commands to signal sweeper
        sc.send_command(nwa_sock, "++addr 17")

        # set center frequency
        print ("setting center frequency to", val, " MHz")
        sc.send_command(nwa_sock, "CF " + str(val) + "MZ")
        # set signal sweep time to 100ms (fastest possible)
        sc.send_command(nwa_sock, "ST100MS")
        # provide short delay
        time.sleep(1)

        # return to network analyzer
        sc.send_command(nwa_sock, "++addr 16")

        # turn off swept mode
        sc.send_command(nwa_sock, "SW0")
        # set analyzer to perform exactly five sweeps
        sc.send_command(nwa_sock, "TS1")
        # give network analyzer time to complete sweeps
        time.sleep(3)

        print ("Transferring data " + str(idx + 1))
        # take measurement
        # Input A absolute power measurement
        sc.send_command(nwa_sock, "C1IA")
        sc.send_command(nwa_sock, "C1OD")
        # data output takes ~0.8 seconds in ASCII mode
        time.sleep(1)
        sc.send_command(nwa_sock, "++read 10")

        tmp_list.append(sc.read_data(nwa_sock, printlen=True))

    return tmp_list

def make_plot_points(cavity_length, nominal_centers, nwa_span, nwa_points, raw_nwa_data):
	"""Convert collected data into a format suitable for saving or processing.
	Output data will be a list of triples (Frequency(mHz),Cavity Length(in),Power(dBm))

	Args:
		config_pars:ConfigParameters class
		constants:Constants class
		rt_params:RunTimeParameters class

	Returns:
		plot_points, a list of data triples with the format described above
	"""

	tmp_list = raw_nwa_data

	total_str = ''.join(tmp_list)

	power_list = total_str.strip()
	power_list = re.split(',|\n', power_list)

	power_list = [float(y) for y in power_list]

	plot_points = []

	max_length = nominal_centers[-1] + nwa_span / 2
	min_length = nominal_centers[0] - nwa_span / 2
	num_points = 4 * nwa_points

	for idx, power in enumerate(power_list):
		# (idx+1)*(4600 - 3000)/(1604) + 3000
		frequency = (idx + 1) * (max_length - min_length) / (num_points) + min_length
		frequency = int(round(frequency))
		plot_points.append([frequency, cavity_length, power])

	return plot_points

def get_step_sock(addr_dict):

    ip_addrs = addr_dict['step'][0]
    port = addr_dict['step'][1]
    inst_name = "Stepper Motor"

    try:
        sock = sc.socket_connect(ip_addrs, int(port))
        st = "Successfully connected to " + inst_name
        c_print(st, "Green")
        return sock
    except (IOError, ValueError) as exc:
        # some exception handling overlaps with socket_connect, but we need to handle ValueError in the case of a bad port number
        st = "Problem generating socket object for " + inst_name + "!"
        c_print(st, "Red")
        return -1

def set_stepper_motor(step_sock):

	c_print("Setting stepper motor", "Purple")
	# set 200 steps/rev
	sc.send_command_scl(step_sock, "MR0")
	# set acceleration
	sc.send_command_scl(step_sock, "AC1")
	# set deceleration
	sc.send_command_scl(step_sock, "DE1")
	# set velocity
	sc.send_command_scl(step_sock, "VE0.5")

	c_print("Stepper motor set.", "Green")

def reset_cavity(step_sock, len_of_tune):

    set_stepper_motor(step_sock)

    rev = int(len_of_tune * -16)

    c_print("Setting cavity back to initial length...", "Purple")

    nsteps = int(rev * 200)

    # set steps per revolution to 200 steps/revolution
    sc.send_command_scl(step_sock, "MR0")
    # set acceleration
    sc.send_command_scl(step_sock, "AC1")
    # set deceleration
    sc.send_command_scl(step_sock, "DE1")
    # set velocity
    sc.send_command_scl(step_sock, "VE1.5")
    print ("Moving motor ", rev, " Revolutions.")  # Movement will take", abs(duration), "seconds."
    sc.send_command_scl(step_sock, "FL" + str(nsteps))
    sc.send_command_scl(step_sock, "VE.5")

    step_sock.close()

def walk_loop(step, len_of_tune, revs, iters, num_of_iters):

    set_stepper_motor(step)

    print ("Iteration:", iters, " of ", num_of_iters, ".  Moving stepper", revs, "revolution(s).")
    itsteps = int(revs * 200)
    sc.send_command_scl(step, "FL" + str(itsteps))
    sc.send_command_scl(step, "VE.5")
    # wait for stepper motor to move
    time.sleep(revs)
    step.close

def set_freq_window(nwa_sock, frequency , span):
	# set passthrough mode to source
	sc.send_command(nwa_sock, "PT19")
	# change GPIB address to passthrough, send commands to signal sweeper
	sc.send_command(nwa_sock, "++addr 17")

	# set center frequency to frequency specified
	print ("Setting center frequency to", frequency, " MHz")
	sc.send_command(nwa_sock, "CF " + str(round(frequency)) + "MZ")
	time.sleep(1)

	# set frequency window around center to specified span
	sc.send_command(nwa_sock, "DF " + str(span) + "MZ")
	time.sleep(1)

	# return to network analyzer
	sc.send_command(nwa_sock, "++addr 16")

def take_data_single(nwa_sock):

    # set passthrough mode to source
    sc.send_command(nwa_sock, "PT19")
    # change GPIB address to passthrough, send commands to signal sweeper
    sc.send_command(nwa_sock, "++addr 17")

    # set signal sweep time to 100ms (fastest possible)
    sc.send_command(nwa_sock, "ST100MS")
    # provide short delay
    time.sleep(1)

    # return to network analyzer
    sc.send_command(nwa_sock, "++addr 16")

    # turn off swept mode
    sc.send_command(nwa_sock, "SW0")
    # set analyzer to perform exactly one sweep
    sc.send_command(nwa_sock, "TS1")
    # give network analyzer time to complete sweeps
    time.sleep(3)

    print ("Transferring data...")
    # take measurement
    # Input A absolute power measurement
    sc.send_command(nwa_sock, "C1IA")
    sc.send_command(nwa_sock, "C1OD")
    # data output takes ~0.8 seconds in ASCII mode
    time.sleep(1)
    sc.send_command(nwa_sock, "++read 10")

    return sc.read_data(nwa_sock, printlen=True)

def str_list_to_power_list(raw_strs):

	total_str = ''.join(raw_strs)
	power_list = total_str.strip()
	power_list = re.split(',|\n', power_list)
	power_list = [float(y) for y in power_list]

	return power_list

def str_to_power_list(raw_str):

	power_list = raw_str.strip().split(',')
	power_list = [float(y) for y in power_list]

	return power_list

def plot_freq_window(plot_data, center_freq, freq_window):
	plot_title = 'Frequency Window'

	points = len(plot_data)
	c_print("Preparing data for plotting...", "Purple")

	nwa_y = [10.**(y / 10) for y in plot_data]  # convert from dBm to power (mW)

	# get x values from center frequency and span
	nwa_x = [(center_freq - (freq_window / 2) + \
	  freq_window * (float(x) / points)) for x in range(points)]

	# convert to arrays
	nwa_x = np.array(nwa_x)
	nwa_y = np.array(nwa_y)
	nwa_y_dbm = [10 * np.log10(y) for y in nwa_y]

	plt.title(plot_title)
	plt.xlabel('Frequency (MHz)')
	plt.ylabel('Power (dBm)')
	plt.plot(nwa_x, nwa_y_dbm, '.')
	plt.show()

	plt.clf()

def power_list_to_str(power_list, center_freq, freq_window, cavity_length):

	plot_points = []

	max_length = round(center_freq) + freq_window / 2
	min_length = round(center_freq) - freq_window / 2
	num_points = len(power_list)

	for idx, power in enumerate(power_list):
		frequency = (idx + 1) * (max_length - min_length) / (num_points) + min_length
		frequency = int(round(frequency))
		plot_points.append([frequency, cavity_length, power])

	freq_window_str = ''
	for triple in plot_points:
		temp_str = str(triple)
		trans_table = dict.fromkeys(map(ord, ' []'), None)
		temp_str = temp_str.translate(trans_table)
		freq_window_str += temp_str + "\n"

	return freq_window_str
