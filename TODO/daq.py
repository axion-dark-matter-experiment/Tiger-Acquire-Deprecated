# daq.py [mode [nominal_center_frequency]]
# Program to conduct data acquisition for the Orpheus prototype experiment.
# First connect to 8757E Network Analyzer and 83620A Synthesized Sweeper 
# through Prologix converter box.
# Retrieve spectrum, adjust frequency, and calculate Q until user approves.
# Or, in auto mode, a stepper motor will adjust Q until computer approves.
# Next connect to N9000A CXA Signal Analyzer and take data. 
# Then upload all data and relevant parameters to database.
# Written by Ari Brill, 7/15/14

# Modes
# data: Manual data taking. Perform entire procedure.
# auto: Automatic data taking. Perform entire procedure.
# nwa: Network analyzer only. For e.g. measuring Qs.
# sa: Spectrum analyzer only. For e.g. measuring backgrounds.

import sys
import socket_connect as sc # custom socket communication functions
import time
from scipy.optimize import leastsq
import psycopg2 # psql library
import numpy as np
import matplotlib.pyplot as plt

#### Parameters ###

nwa_span = 200 # MHz
nwa_points = 401
nwa_power = 10 # dBm
sa_span = 10 # MHz
sa_averages = 1024
fft_length = 65536
noise_temperature = 1417.0 # K
effective_volume = 20.0 # cm^3 # invalid!!
bfield = 8.5e-4 # T

points_to_MHz = float(nwa_span) / float(nwa_points) # for network analyzer
steps_per_MHz = 200 # for stepper motor

#### Functions ####

# calculate Lorentzian given x and parameters [HWHM, center, height]
def lorentzian(x,p):
    numerator = p[0]**2
    denominator = (x - p[1])**2 + p[0]**2
    y = p[2]*(numerator/denominator)
    return y

# calculate residuals of fitted curve
def residuals(p,y,x):
    if within_bounds(p):
        err = y - lorentzian(x,p)
        return err
    else:
        return 1e6

# check whether parameters [HWHM, center, height] are within reasonable bounds
def within_bounds(p):
    if p[0] < 0 or p[0] > nwa_span:
        return False
    if (p[1] < actual_center_freq - nwa_span or
            p[1] > actual_center_freq + nwa_span):
        return False
    return True

###################

# check command line arguments

argv = sys.argv
argc = len(argv)
if argc >= 2:
    mode = argv[1]
else:
    mode = 'data'
if mode not in ['data', 'auto', 'nwa', 'sa']:
    print "error: mode must be 'data', 'auto', 'nwa', or 'sa'"
    sys.exit()
print mode, "mode selected"

# get nominal center frequency either from input arg or prompt if necessary

first_try = True
while True:
    try:
        if argc >= 3 and first_try:
            nominal_center_freq = int(argv[2])
        else:
            nominal_center_freq =\
                    int(raw_input('Enter center frequency (MHz): '))
        if nominal_center_freq <= 0:
            raise ValueError
        break
    except ValueError:
        first_try = False
    print "center frequency must be a whole number of MHz, try again"
actual_center_freq = nominal_center_freq # these might differ later on

# connect to Prologix converter box
print "connecting to GPIB converter box..."
gpib = sc.socket_connect('10.28.3.21', 1234)
if not gpib:
    sys.exit()

if mode in ['data', 'auto', 'nwa']:
    print "setting converter box"
    # set to network analyzer GPIB address
    sc.send_command(gpib, "++addr 16")
    # disable auto-read
    sc.send_command(gpib, "++auto 0")
    # enable EOI assertion at end of commands
    sc.send_command(gpib, "++eoi 1")
    # append CR+LF to instrument commands
    sc.send_command(gpib, "++eos 0")
    
    print "setting network analyzer"
    # set active channel to 1
    sc.send_command(gpib, "C1")
    # set cursor on
    sc.send_command(gpib, "CU1")
    # set cursor delta off
    sc.send_command(gpib, "CD0")
    # set data format to ascii
    sc.send_command(gpib, "FD0")
    # set number of points to nwa_points
    sc.send_command(gpib, "SP"+str(nwa_points))
    
    if mode == 'auto':
        print "connecting to stepper motor"
        step = sc.socket_connect("10.28.3.71", 7776)
        if not step:
            sys.exit()
        print "setting stepper motor"
        # set acceleration
        sc.send_and_confirm_scl(step, "AC1")
        # set deceleration
        sc.send_and_confirm_scl(step, "DE1")
        # set velocity
        sc.send_and_confirm_scl(step, "VE0.5")
        step.close()
    
    if mode in ['data', 'auto']: # set RF source just once in data or auto mode
        print "setting RF source..."
        # set passthrough mode to source
        sc.send_command(gpib, "PT19")
        # change GPIB address to passthrough
        sc.send_command(gpib, "++addr 17")
        # RF output on
        print "turning on RF"
        sc.send_command(gpib, "RF1")
        # set center frequency
        print "setting center frequency to", nominal_center_freq
        sc.send_command(gpib, "CF "+str(nominal_center_freq)+"MZ")
        time.sleep(1)
        # set frequency span
        sc.send_command(gpib, "DF "+str(nwa_span)+"MZ")
        time.sleep(1)
        # set power level
        sc.send_command(gpib, "PL "+str(nwa_power)+"DB")
        time.sleep(1)
        # return to network analyzer
        sc.send_command(gpib, "++addr 16")
        time.sleep(1)
    
    while True:
        
        if mode == 'nwa': # set RF source every time in nwa mode
            print "setting RF source..."
            # set passthrough mode to source
            sc.send_command(gpib, "PT19")
            # change GPIB address to passthrough
            sc.send_command(gpib, "++addr 17")
            # RF output on
            print "turning on RF"
            sc.send_command(gpib, "RF1")
            # set center frequency
            print "setting center frequency to", nominal_center_freq
            sc.send_command(gpib, "CF "+str(nominal_center_freq)+"MZ")
            time.sleep(1)
            # set frequency span
            sc.send_command(gpib, "DF "+str(nwa_span)+"MZ")
            time.sleep(1)
            # set power level
            sc.send_command(gpib, "PL "+str(nwa_power)+"DB")
            time.sleep(1)
            # return to network analyzer
            sc.send_command(gpib, "++addr 16")
            time.sleep(1)
        
        # tune reflector manually
        if mode in ['data', 'nwa']:
            # set cursor to maximum
            sc.send_command(gpib, "CX")
            raw_input("Tune reflector now and press ENTER: ")

        # get the peak
        print "finding peak..."
        # turn on averaging (16 averages is a good number)
        sc.send_command(gpib, "AF16")
        time.sleep(5)
        # set cursor to maximum
        sc.send_command(gpib, "CX")
        time.sleep(1)
        # measure and read horizontal position of peak in points
        sc.send_command(gpib, "OC")
        time.sleep(1)
        sc.send_command(gpib, "++read 10")
        p_peak = int(sc.read_data(gpib).split(',')[1].strip())
        # convert peak from points to MHz
        actual_center_freq_unrounded = (nominal_center_freq + 
                (p_peak - (float(nwa_points)/2))*points_to_MHz)
        actual_center_freq = int(round(actual_center_freq_unrounded))
        # turn off averaging
        sc.send_command(gpib, "A0")
       
        # adjust center frequency in nwa mode
        if mode == 'nwa':
            print "adjusting center frequency..."
            # set passthrough mode to source
            sc.send_command(gpib, "PT19")
            # change GPIB address to passthrough
            sc.send_command(gpib, "++addr 17")
            # set center frequency to actual resonant frequency
            sc.send_command(gpib, "CF "+str(actual_center_freq)+"MZ")
            # change back GPIB address to network analyzer
            sc.send_command(gpib, "++addr 16")
            time.sleep(1)
            # turn averaging back on
            sc.send_command(gpib, "AF16")
            time.sleep(5)
    
        # tune reflector automatically in auto mode
        if mode == 'auto':
            print "connecting to stepper motor..."
            step = sc.socket_connect('10.28.3.71', 7776)
            if not step:
                sys.exit()
            nsteps = ((nominal_center_freq - actual_center_freq_unrounded) * 
                    steps_per_MHz)
            nsteps = int(round(nsteps))
            print "moving motor", nsteps, "steps"
            sc.send_and_confirm_scl(step, "FL"+str(nsteps))
            time.sleep(2)
            step.close()
        
            # get the new peak
            print "finding new peak..."
            # turn on averaging (16 averages is a good number)
            sc.send_command(gpib, "AF16")
            time.sleep(5)
            # set cursor to maximum
            sc.send_command(gpib, "CX")
            time.sleep(1)
            # measure and read horizontal position of peak in points
            sc.send_command(gpib, "OC")
            time.sleep(1)
            sc.send_command(gpib, "++read 10")
            p_peak = int(sc.read_data(gpib).split(',')[1].strip())
            # convert peak from points to MHz
            actual_center_freq_unrounded = (nominal_center_freq + 
                    (p_peak - (float(nwa_points)/2))*points_to_MHz)
            actual_center_freq = int(round(actual_center_freq_unrounded))
            # turn off averaging
            sc.send_command(gpib, "A0")
            
        print "transferring data..."
        # take measurement
        sc.send_command(gpib, "IA")
        time.sleep(2)
        # output measurement data
        sc.send_command(gpib, "OD")
        sc.send_command(gpib, "++read 10")
        raw_nwa_data = sc.read_data(gpib, printlen=True)
        # reset cursor to maximum for aesthetics
        sc.send_command(gpib, "CX")
        # turn off averaging
        sc.send_command(gpib, "A0")
        
        print "fitting data"
        # turn string of power data into list of floats
        nwa_y = raw_nwa_data.strip().split(',')
        nwa_y = [float(y) for y in nwa_y]
        # convert from dBm to power (mW)
        nwa_y = [10.**(y/10) for y in nwa_y]
        # get x values from center frequency and span
        nwa_x = [(actual_center_freq - (nwa_span/2) +\
                nwa_span*(float(x)/nwa_points)) for x in xrange(nwa_points)]
        # convert to arrays
        nwa_x = np.array(nwa_x)
        nwa_y = np.array(nwa_y)
        # define middle values to fit to
        middle = ((2*nwa_points/5 < np.arange(nwa_points)) & 
                (np.arange(nwa_points) < 3*nwa_points/5))
        # initial values for fit: [HWHM, peak center, height]
        p = [25.0, actual_center_freq, nwa_y[nwa_points/2]]
        pbest = leastsq(residuals, p, args=(nwa_y[middle], nwa_x[middle]))[0]
        fitted_hwhm = pbest[0]
        fitted_center_freq = pbest[1]
        fitted_height = pbest[2]
        fitted_q = fitted_center_freq / (fitted_hwhm*2)
        # convert back to dBm
        fitted_height = 10 * np.log10(fitted_height)
    
        # report parameters
        print "\nParameters:"
        print "Fitted Q:", fitted_q
        print "Fitted center frequency (MHz):", fitted_center_freq
        print "Fitted height (dBm):", fitted_height, '\n'

        # display a plot in data or nwa mode
        if mode in ['data', 'nwa']:
            plt.clf()
            nwa_y_dbm = [10*np.log10(y) for y in nwa_y]
            lorentzian_dbm = 10*np.log10(lorentzian(nwa_x[middle], pbest))
            plt.plot(nwa_x, nwa_y_dbm, 'o')
            plt.plot(nwa_x[middle], lorentzian_dbm, 'r')
            plt.title('Lorentzian Fit to Resonance Peak')
            plt.xlabel('Frequency (MHz)')
            plt.ylabel('Power (dBm)')
            plt.show()

        # in data or nwa mode, break the loop if user says setup is good
        if mode in ['data', 'nwa']:
            cont = ''
            while cont.lower() not in ['y', 'n']:
                cont = raw_input("Tune again? (y/n): ")
            if cont.lower() == 'n':
                break

        # in auto mode, break the loop if results are acceptable
        # end program if results are way too far off
        if mode == 'auto':
            peak_distance = abs(nominal_center_freq - 
                    actual_center_freq_unrounded)
            if fitted_q < 1000 or fitted_height > 0 or peak_distance > 10:
                print "error: too far from peak"
                with open("errors.txt", 'a') as errorfile:
                    errorfile.write(str(nominal_center_freq)+'\n')
                sys.exit()
            if peak_distance < 1: # tuned to +-1 MHz of target
                print "resonance tuned to", actual_center_freq, "MHz"
                break
            print "tuning again..."

# in network analyzer mode, we're done, end program
if mode == 'nwa':
    gpib.close()
    print "Done."
    sys.exit()

# tuning complete, prepare for data taking 

print "preparing to take data..."
# set passthrough mode to source
sc.send_command(gpib, "PT19")
# change GPIB address to passthrough
sc.send_command(gpib, "++addr 17")
# turn off RF
sc.send_command(gpib, "RF0")
print "turning off RF"
# change back GPIB address to network analyzer
sc.send_command(gpib, "++addr 16")
time.sleep(1)
# turn off cursor
sc.send_command(gpib, "CU0")
# close socket
gpib.close()

# connect to spectrum analyzer
print "connecting to spectrum analyzer..."
spec = sc.socket_connect('172.28.189.176', 5025)
if not spec:
    sys.exit()

print "setting spectrum analyzer"
# set Event Status Enable register to activate on any error
sc.send_and_confirm(spec, "*ESE 60")
# set IQ analyzer mode
sc.send_and_confirm(spec, "INST:SEL BASIC")
# set Digital IF Bandwidth
sc.send_and_confirm(spec, "SPEC:DIF:BAND 10MHz")
# set filter type to flattop
sc.send_and_confirm(spec, "SPEC:DIF:FILT:TYPE FLAT")
# set FFT window to uniform
sc.send_and_confirm(spec, "SPEC:FFT:WIND UNIF")
# disable automatic FFT window and length control
sc.send_and_confirm(spec, "SPEC:FFT:LENG:AUTO OFF")
# set FFT window length
sc.send_and_confirm(spec, "SPEC:FFT:WIND:LENG "+str(fft_length))
# set FFT length
sc.send_and_confirm(spec, "SPEC:FFT:LENG "+str(fft_length))

print "configuring measurement"
# configure measurement
sc.send_and_confirm(spec, "CONF:SPEC:NDEF")
# set center frequency
sc.send_and_confirm(spec, "FREQ:CENT "+str(actual_center_freq)+"MHz")
# set frequency span
sc.send_and_confirm(spec, "SPEC:FREQ:SPAN "+str(sa_span)+"MHz")

print "configuring averaging"
# set average type to power average
sc.send_and_confirm(spec, "SPEC:AVER:TYPE RMS")
# set number of averages
sc.send_and_confirm(spec, "SPEC:AVER:COUN "+str(sa_averages))
# turn off continuous measurement operation
sc.send_and_confirm(spec, "INIT:CONT OFF")

# check for errors
sc.send_command(spec, "*STB?")
sa_error = int(sc.read_data(spec))
# we get a decimal number encoding a byte: subtract off bits 7 and 6 
if sa_error >= 128: sa_error -= 128
if sa_error >= 64: sa_error -= 64
if sa_error >= 32: # if bit 5 is 1
    print "spectrum analyzer error - check its screen for more info"
    spec.close()
    sys.exit()

# set number of measurements to take depending on mode
# measurement 0 assumes current off in data mode, unspecified in sa mode
# measurement 1 assumes current is on
if mode == 'data':
    start = 1 # change this to 0 to take two runs with current off and on
    nmeas = 2
if mode == 'auto':
    start = 1
    nmeas = 2
if mode == 'sa':
    start = 0
    nmeas = 1

# make sure current starts off in data mode with two runs
current_on = False
if mode == 'data' and start == 0:
    raw_input("Make sure current is OFF and press ENTER: ")

for meas in range(start, nmeas):

    # have user turn on magnetic field only if it's the second measurement
    if meas == 1 and mode != 'auto':
        raw_input("Turn current ON and press ENTER: ")
        current_on = True
        time.sleep(2)
    
    print "taking data..."
    # acquire data
    sc.send_command(spec, ":READ:SPEC7?")
    sc.send_command(spec, "*OPC?")
    # *OPC? will write "1\n" to the output when operation is complete.
    # The data will then be written on top of that.
    # read a little bit of data to verify read is complete
    opc_data = sc.read_small(spec)
    # read the rest of the data
    raw_sa_data = sc.read_data(spec, printlen=True, timeout=0.5)
    # combine data
    raw_sa_data = opc_data + raw_sa_data
    # remove the "1\n" at the end from *OPC?
    raw_sa_data = raw_sa_data[:-2]
    
    # turn on continuous measurement operation again (looks prettier)
    sc.send_and_confirm(spec, "INIT:CONT ON")
    
    # if in data or auto mode, upload info and data to orpheus database
    if mode in ['data', 'auto']:
        print "uploading data to database..."
        # connect to orpheus database
        conn = psycopg2.connect("dbname=orpheus host=localhost user=orpheus\
                password=orpheus")
        # open a cursor to perform database operations
        cur = conn.cursor()
        try:
            # insert experiment info into main table
            cur.execute("INSERT INTO main (id, timestamp, nominal_center_freq,\
                    actual_center_freq, nwa_span, nwa_points, nwa_power,\
                    sa_span, sa_averages, fft_length, fitted_hwhm,\
                    fitted_center_freq, fitted_height, fitted_q,\
                    noise_temperature, effective_volume, bfield, current_on,\
                    ignore) VALUES (DEFAULT, localtimestamp, %s, %s, %s, %s,\
                    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, FALSE)\
                    RETURNING id",
                    (nominal_center_freq, actual_center_freq, nwa_span,
                        nwa_points, nwa_power, sa_span, sa_averages,
                        fft_length, fitted_hwhm, fitted_center_freq,
                        fitted_height, fitted_q, noise_temperature,
                        effective_volume, bfield, current_on))
            # get experiment id from return value
            exp_id = cur.fetchone()[0]
            # insert network analyzer data into nwa_data table
            cur.execute("INSERT INTO nwa_data (id, nwa_data) VALUES (%s, %s)",\
                    (exp_id, raw_nwa_data))
            # insert spectrum analyzer data into sa_data table
            cur.execute("INSERT INTO sa_data (id, sa_data) VALUES (%s, %s)",\
                    (exp_id, raw_sa_data))
            # commit the changes
            conn.commit()
            print "data uploaded"
        except:
            print "error uploading to database"
        # close database connection
        cur.close()
        conn.close()

    # if in sa mode, write data to file
    if mode == 'sa':
        with open("sa_data.txt", 'w') as safile:
            safile.write(raw_sa_data)

# if current on, have user turn it off again
if current_on and mode != 'auto':
    raw_input("Turn current OFF and press ENTER: ")
    
# close socket 
spec.close()
    
print "Done."
