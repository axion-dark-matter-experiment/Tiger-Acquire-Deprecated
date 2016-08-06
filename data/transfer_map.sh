#!/bin/bash

selection="$1"

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

gnuplot -e "filename='$selection'; outputname='$DIR/current_mode_map.jpeg'" $DIR/mode_map_plotter.plot
scp $DIR/current_mode_map.jpeg kyou@kitsune.dyndns-ip.com:/mnt/data/www/html/Electric_Tiger/Current_Data/
