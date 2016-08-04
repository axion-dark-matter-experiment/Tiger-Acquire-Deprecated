#!/bin/bash

file_path="$1"
plot_name="$2"
cd ./data
gnuplot -e "filename='$file_path'; outputname='$plot_name'" power_spectrum_plotter.plot
scp ./current_power_spectrum.jpeg kyou@kitsune.dyndns-ip.com:/mnt/data/www/html/Electric_Tiger/Current_Data/
