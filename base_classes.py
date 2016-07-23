"""Three principle classes that contain all variables and data needed by the
rest of the program. These classes are used as arguements for the functions
defined in etig_funcs.py
"""


import socket_connect_2 as sc
import base_functions as funcs

import sys #basic std library functions
import csv #.csv file parsing
import time #time.strftime
import os.path #os.path.join
import socket
import subprocess

class Constants:
	"""
	Contains plain data that is designed to be immutable. Each program will need
	access to these data, but will not need to modify anything.
	"""
	nwa_span = 400 # Frequency window size used for collecting data, in MHz
	nwa_points = 401 # Number of data points to be collected for any given frequency window
	nwa_power = 12.5 # Power to set the Signal Sweeper to, in dBm
	steps_per_MHz = -6 # Change in frequency per set, for stepper motor

	#nominal_centers=[3200,3600,4000,4400]#Center frequencies, as used in Mode Map construction, specified in MHz
	nominal_centers = [3200,3600,4000,4400]
	points_to_MHz = float(nwa_span) / float(nwa_points) # for network analyzer

class ConfigTypes():
	"""Contains data that is read from user specified config file.
	Class is responsible for reading and parsing config file, as well as generating
	socket objects for all instruments.
	Makes use of two dictionaries, data_dict for plain data types and sock_dict for socket objects.

	Member variables in data_dict are mutable during run time, members of sock_dict are not.

	Attributes:
		sock_data: Dictionary that holds socket objects, format is instrument_name:[socket_object]
		data_dict: Dictionary that hold plain data loaded from the config file, format is data_title:[data_value]
	"""
	def __init__(self,config_path):
		"""Initailzie dictionary objects, and populate from config file information.

		Args:
			config_path: string specifying path to config file, set by command line argument.
		"""
		self.sock_dict={}#dictionary to hold socket objects
		self.data_dict={}#dictionary to hold POD, such as bools, ints, and str's
		self.addr_dict={}#dictionary to hold information used to generate sockets
		# but -not- the sockets themselves, format is key=name val=[ip,port]
		#self.__set_from_config(config_path)

		#itialize dictionary of functions for parsing data
		self.func_dict = {2:self.__handle_plain_data,\
		3:self.__handle_socket_objects,'n':self.__handle_lists}

		self.__parse_config_data(config_path)

		self.data_dict['num_of_iters']=self.__get_total_iterations()
		self.__generate_file_paths()

	def __handle_plain_data(self,two_element_list):
		type_name = two_element_list[0]
		data_val = two_element_list[1]
		self.data_dict[type_name] = data_val

	def __handle_socket_objects(self,three_element_list):
		inst_name=three_element_list[0]
		ip_addrs=three_element_list[1]
		port=three_element_list[2]
		self.addr_dict[inst_name]=[ip_addrs,port]
		st="Connecting to "+inst_name+" at IP Address: "+ip_addrs+" using port "+str(port)
		#let user known that an attemp us being made to generate a socket object, specifiying
		#instrument name, IP address and port number
		funcs.c_print(st,"Purple")

		#attemp to generate a socket object
		try:
			sock=sc.socket_connect(ip_addrs,int(port))
			#let user know a socket object has been generated successfully
			st="Successfully connected to "+inst_name
			funcs.c_print(st,"Green")
			#store the instrument name as key and socket as the value in sock_dict
			self.sock_dict[inst_name] = sock;

		#handle errors in socket object generation
		except (IOError, ValueError) as exc:
			#some exception handling overlaps with socket_connect, but we need to handle ValueError in the case of a bad port number
			st="Problem generating socket object for "+inst_name+"! Exiting..."
			#let user know socket generation has failed
			funcs.c_print(st,"Red")
			#close all sockets so that we do not leave a socket hanging
			self.close_all()
			#exit the program
			sys.exit()

	def __handle_lists(self,n_element_list):

		tmp_list = []
		key_name = n_element_list[0]

		#start indexing at one since we will use the first token as the dictionary
		#key
		for x in range(1,len(n_element_list)):
			tmp_list.append(n_element_list[x])

		self.data_dict[key_name] = tmp_list

	def __parse_config_data(self,config_path):
		config_list = list(csv.reader(open(config_path, newline=''), delimiter=';'))

		#loop over all enteries specified in config file
		for x in range(0,len(config_list)):
			number_enteries = len(config_list[x])

			if (number_enteries < 2):
				continue
			elif(number_enteries > 4):
				number_enteries = 'n'

			self.func_dict[number_enteries](config_list[x])


	def __set_from_config(self,config_path):
		"""Read from config file and populate two main dictionaries, sock_dict and data_dict

		Args:
			config_path: string specifying path to config file, set by command line argument.
		"""
		#open config file and parse based on newline characters and the delimiter ';'
		config_list = list(csv.reader(open(config_path, newline=''), delimiter=';'))

		#loop over all enteries specified in config file
		for x in range(0,len(config_list)):

			#Any line that has at least three enteries is assumed to be in the form "Instrument Name";"IP Address";"Port Number"
			#Such enteries are treated as special socket objects and loaded into sock_dict
			if len(config_list[x])>=3:
				inst_name=config_list[x][0]
				ip_addrs=config_list[x][1]
				port=config_list[x][2]
				self.addr_dict[inst_name]=[ip_addrs,port]
				st="Connecting to "+inst_name+" at IP Address: "+ip_addrs+" using port "+str(port)
				#let user known that an attemp us being made to generate a socket object, specifiying
				#instrument name, IP address and port number
				funcs.c_print(st,"Purple")

				#attemp to generate a socket object
				try:
					sock=sc.socket_connect(ip_addrs,int(port))
					#let user know a socket object has been generated successfully
					st="Successfully connected to "+inst_name
					funcs.c_print(st,"Green")
					#store the instrument name as key and socket as the value in sock_dict
					self.sock_dict[inst_name] = sock;

				#handle errors in socket object generation
				except (IOError, ValueError) as exc:
					#some exception handling overlaps with socket_connect, but we need to handle ValueError in the case of a bad port number
					st="Problem generating socket object for "+inst_name+"! Exiting..."
					#let user know socket generation has failed
					funcs.c_print(st,"Red")
					#close all sockets so that we do not leave a socket hanging
					self.close_all()
					#exit the program
					sys.exit()
			#If line has less than three enteries it is assumed to be plain data
			# in the format "Data_Title;Data_Value" and is loaded into data_dict as such
			elif len(config_list[x])<3:
				inst_name=config_list[x][0]
				data_val=config_list[x][1]
				self.data_dict[inst_name]=data_val

		self.data_dict['num_of_iters']=self.__get_total_iterations()
		self.__generate_file_paths()

	def __generate_file_paths(self):
		#Generate file name time-stamp in the form dd.mm.yyyy
		time_stamp=time.strftime("%d.%m.%Y")
		#concatenate the base save-file path with the date-time string to form the name of all necessary .csv files
		save_path=self.data_dict['save_file_path']
		#Store miscellaneous file save paths and names in data_dict dictionary
		self.data_dict['file_namew']=os.path.join(save_path, time_stamp + 'F.csv')
		self.data_dict['file_name']=os.path.join(save_path, time_stamp + 'MM.csv')
		self.data_dict['file_namec']=os.path.join(save_path, time_stamp + 'CP.csv')


	def close_all(self):
		"""Function to close all sockets in the socket dictionary, to be called before program exit or during error handling
			should not throw errors since sockets should only be added to dictionary when connection was successful, avoiding the case of a NULL value
		"""
		for key in self.sock_dict:
			st="Closing socket for "+key
			funcs.c_print(st,"Blue")
			self.sock_dict[key].close()

	def __get_total_iterations(self):
		"""Function that computes the total number of iterations needed when constucting a Mode Map.
		Used to populate the member variable num_of_iters.

		Args:
			config_pars:ConfigTypes class,
		"""
		tune_length=float(self.data_dict['len_of_tune'])*16.0
		revolutions=abs(float(self.data_dict['revs_per_iter']))
		num_of_iters=tune_length/revolutions

		return int(round(num_of_iters))


class BaseTypes(ConfigTypes):
	"""
	Contains data that is mutable during run time, but does not need to be saved after program exits.
	Class is designed to be accessed and have member variable values changed by external functions.
	"""

	def __init__(self,config_path):
		super(BaseTypes, self).__init__(config_path)

		self.actual_center_freq_unrounded=0.0
		self.actual_center_freq=0
		#single string used to store a -single- comma seperated list of data grabbed from the network analzyer
		#user for Lorentzian fitting and plotting and -nothing else-
		self.nwa_fit_data=''
		#raw_nwa_data is a list-of-strings. It can have anywhere between zero and eight elements.
		self.raw_nwa_data=[]
		#special list needed to hold 'background' data, that is data collected where no modes are present
		#needs to be passed to the modetracking sub-process as a string
		self.background_data=''
		self.iterations=0
		self.number_of_iterations=0
		self.nsteps=0
		self.num_of_iters=0 #counter for current iteration, needs to be set by

		self.num_of_iters = self.get_total_iterations()

	def clear_lists(self):
		"""	Clear all raw data that was taken from the network analyzer
			needs to be called during loops so that data is not duplicated.
		"""
		for li in self.raw_nwa_data:
			del li[:]
