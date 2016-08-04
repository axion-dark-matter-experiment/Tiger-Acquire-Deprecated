#Usage:
#gnuplot -p -e "filename='~/bilat_data.csv'" mode_map_plotter.plot

set title "Current Power Spectrum"
set xlabel "Frequency (MHz)"
set ylabel "Power (dBm)"

set term jpeg size 1280,720
set output outputname

plot filename notitle with lines
