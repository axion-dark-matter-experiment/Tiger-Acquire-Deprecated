#Usage:
#gnuplot -p -e "filename='~/workspace/Electric-Tiger/28.06.2016MM.csv'" mode_map_plotter.plot

set title "Current Mode Map"
set xlabel "Frequency (MHz)"
set ylabel "Cavity Length (Inches)"
set zlabel "Power (dBm)"

set datafile separator ','
set palette rgb 7,5,15

set pm3d map

splot filename using 1:2:3 notitle with points palette
