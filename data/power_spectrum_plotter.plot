#Usage:
#gnuplot -p -e "filename='~/bilat_data.csv'" mode_map_plotter.plot

set title "Current Power Spectrum"
set xlabel "Frequency (MHz)"
set ylabel "Power (dBm)"

#set arrow 1 from 150,0 to 150,f(150)
set term jpeg size 1280,720
#set output 'current_power_spectrum.jpeg'
set output outputname

plot filename notitle with lines
