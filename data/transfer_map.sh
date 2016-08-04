#!/bin/bash

selection="$1"
cd ./data
gnuplot -e "filename='$selection'" mode_map_plotter.plot
scp ./current_mode_map.jpeg kyou@kitsune.dyndns-ip.com:/mnt/data/www/html/Electric_Tiger/Current_Data/
