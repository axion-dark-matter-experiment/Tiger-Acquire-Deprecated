# update_veff.py veff_file
# Program to match each entry in Orpheus database with its veff from veff_file
# Written by Ari Brill, 8/19/14

import sys
import os.path
import psycopg2
import numpy as np

def index_of_closest(val, lst):
    best_index, best_difference = 0, 1e15
    for i, l in enumerate(lst):
        difference = abs(val*1e6 - l)
        if difference < best_difference:
            best_index = i
            best_difference = difference
    return best_index

# parse command line args
argv = sys.argv
argc = len(argv)

if argc != 2:
    print "usage: update_veff.py veff_file"
    sys.exit()

veff_file = argv[1]

if not os.path.isfile(veff_file):
    print "error: file", veff_file, "not found"
    sys.exit()

# get info from veff_file
veff_data = np.loadtxt(veff_file)
position = veff_data[:,0]
frequency = veff_data[:,1]
volume = veff_data[:,2]

# correct volume
volume /= 0.00126**2

# connect to Orpheus database
conn = psycopg2.connect("dbname=orpheus host=localhost user=orpheus\
        password=orpheus")
cur = conn.cursor()
entries = conn.cursor()
entries.execute("SELECT id, actual_center_freq FROM main WHERE ignore = FALSE;")

# match each entry to the closest volume and update its veff
for entry in entries:
    entry_id = entry[0]
    center_freq = entry[1]
    veff = volume[index_of_closest(center_freq, frequency)]
    cur.execute("UPDATE main SET effective_volume = %s WHERE id = %s",
            (veff, entry_id))

# commit the changes
conn.commit()

# close database connection
cur.close()
entries.close()
conn.close()

