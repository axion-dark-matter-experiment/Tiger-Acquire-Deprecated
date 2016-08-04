import socket_communicators as sc

import sys  # basic std library functions
import csv  # .csv file parsing
import time  # time.strftime
import os.path  # os.path.join
import color_printer as cp

class ConfigTypes:
	"""Contains data that is read from user specified config file.
	Class is responsible for reading and parsing config file, as well as generating
	socket objects for all instruments.
	Makes use of two dictionaries, data_dict for plain data types and sock_dict for socket objects.

	Member variables in data_dict are mutable during run time, members of sock_dict are not.

	Attributes:
		sock_data: Dictionary that holds socket objects, format is instrument_name:[socket_object]
		data_dict: Dictionary that hold plain data loaded from the config file, format is data_title:[data_value]
	"""
	def __init__(self, config_path):
		"""Initailzie dictionary objects, and populate from config file information.

		Args:
			config_path: string specifying path to config file, set by command line argument.
		"""
		self.print_green = cp.ColorPrinter("Green")
		self.print_purple = cp.ColorPrinter("Purple")
		self.print_blue = cp.ColorPrinter("Blue")
		self.print_red = cp.ColorPrinter("Red")
		
		self.sock_dict = {}  # dictionary to hold socket objects
		self.data_dict = {}  # dictionary to hold POD, such as bools, ints, and str's
		self.addr_dict = {}  # dictionary to hold information used to generate sockets
		# but -not- the sockets themselves, format is key=name val=[ip,port]
		
		self.sock_comm = sc.SocketComm()

		config_token_handler = self.__generate_token_handlers()
		self.__parse_config_data(config_path, config_token_handler)

		self.data_dict['num_of_iters'] = self.__get_total_iterations()
		self.__generate_file_paths()
		
	def __generate_token_handlers(self):
		func_dict = {'d':self.__handle_plain_data, \
		's':self.__handle_socket_objects, \
		'l':self.__handle_lists}
		
		return func_dict
				
	def __handle_plain_data(self, two_element_list):
		type_name = two_element_list[0]
		data_val = two_element_list[1]
		self.data_dict[type_name] = data_val

	def __handle_socket_objects(self, three_element_list):
		inst_name = three_element_list[0]
		ip_addrs = three_element_list[1]
		port = three_element_list[2]
		self.addr_dict[inst_name] = [ip_addrs, port]
		st = "Connecting to " + inst_name + " at IP Address: " + ip_addrs + " using port " + str(port)
		# let user known that an attemp us being made to generate a socket object, specifiying
		# instrument name, IP address and port number
		self.print_purple(st)

		# attempt to generate a socket object
		try:
			sock = self.sock_comm._socket_connect(ip_addrs, int(port))
			# let user know a socket object has been generated successfully
			st = "Successfully connected to " + inst_name
			self.print_green(st)
			# store the instrument name as key and socket as the value in sock_dict
			self.sock_dict[inst_name] = sock;

		# handle errors in socket object generation
		except (IOError, ValueError) as exc:
			# some exception handling overlaps with socket_connect, but we need to handle ValueError in the case of a bad port number
			st = "Problem generating socket object for " + inst_name + "! Exiting..."
			# let user know socket generation has failed
			self.print_red(st)
			# close all sockets so that we do not leave a socket hanging
			self.close_all()
			# exit the program
			sys.exit()

	def __handle_lists(self, n_element_list):

		tmp_list = []
		key_name = n_element_list[0]

		# start indexing at one since we will use the first token as the dictionary
		# key
		for x in range(1, len(n_element_list)):
			tmp_list.append(n_element_list[x])

		self.data_dict[key_name] = tmp_list

	def __parse_config_data(self, config_path, func_dict):
		config_list = list(csv.reader(open(config_path, newline=''), delimiter=';'))

		# loop over all enteries specified in config file
		for x in range(0, len(config_list)):
			
			type_id = config_list[x][0]
			func_dict[type_id](config_list[x][1:])


	def __generate_file_paths(self):
		# Generate file name time-stamp in the form dd.mm.yyyy
		time_stamp = time.strftime("%d.%m.%Y")
		# concatenate the base save-file path with the date-time string to form the name of all necessary .csv files
		save_path = self.data_dict['save_file_path']
		# Store miscellaneous file save paths and names in data_dict dictionary
		self.data_dict['file_name'] = os.path.join(save_path, time_stamp + 'MM.csv')
		self.data_dict['file_nameR'] = os.path.join(save_path, time_stamp + 'R.csv')


	def __get_total_iterations(self):
		"""Function that computes the total number of iterations needed when constucting a Mode Map.
		Used to populate the member variable num_of_iters.

		Args:
			config_pars:ConfigTypes class,
		"""
		tune_length = float(self.data_dict['len_of_tune']) * 16.0
		revolutions = abs(float(self.data_dict['revs_per_iter']))
		num_of_iters = tune_length / revolutions

		return int(round(num_of_iters))
	
	def close_all(self):
		"""Function to close all sockets in the socket dictionary, to be called before program exit or during error handling
			should not throw errors since sockets should only be added to dictionary when connection was successful, avoiding the case of a NULL value
		"""
		for key in self.sock_dict:
			st = "Closing socket for " + key
			self.print_blue(st)
			self.sock_dict[key].close()
