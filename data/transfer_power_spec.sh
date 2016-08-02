#!/bin/bash

selection="$1"
cd ./data
gnuplot -e "filename='$selection'" power_spectrum_plotter.plot
scp ./current_power_spectrum.jpeg kyou@kitsune.dyndns-ip.com:/mnt/data/www/html/Electric_Tiger/Current_Data/
