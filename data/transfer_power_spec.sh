#!/bin/bash

file_path="$1"
plot_name="$2"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

gnuplot -e "filename='$file_path'; outputname='$plot_name'" $DIR/power_spectrum_plotter.plot
scp $plot_name kyou@kitsune.dyndns-ip.com:/mnt/data/www/html/Electric_Tiger/Current_Data/
