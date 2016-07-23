# socket_connect.py
# Functions for connecting to remote machines

import socket
import sys
import select


class SocketComm:
    
    def socket_connect(host, port):

        # get host info using supplied host and port
        try:
            sockinfo = socket.getaddrinfo(host, port, 0, socket.SOCK_STREAM)
        except OSError:
            print ("Socket Connect: could not get host info.")
            return None

        # connect to first socket we can
        for sock in sockinfo:
            try:
                s = socket.socket(sock[0], sock[1], sock[2])
                s.settimeout(5)#set socket time-out to 5 seconds, default is ~120 seconds
                s.connect((host, port))
                print ("Socket Connect: connected to", s.getpeername()[0])
                return s
            except (IOError,ValueError) as exc:
                print ("Socket Connect: Could not connect to socket.")
                #raise the same errors that tripped socket_connect so functioned that
                # caller is aware of the error
                raise exc
                return None

    # send a string to the device connected on the socket
    def send_command(sock, cmd, terminator='\n'):
        try:
            command = cmd+terminator
            sock.send(command.encode())
        except:
            print ("Error sending command", cmd, sys.exc_info()[0])

    # send a command of arbitary length to socket
    # entire command will be sent until finished or an error occurs
    # unlike send_command the socket will not time-our or end prematurely
    def send_command_long(sock, cmd, terminator='\n'):
        try:
            command = cmd+terminator
            sock.sendall(command.encode())
        except:
            print ("Error sending command", cmd, sys.exc_info()[0])

    # read data and store in a string
    def read_data(sock, printlen=False, timeout=2):
        data = ''
        while(select.select([sock], [], [], timeout) != ([], [], [])):
            buff = sock.recv(2048)
            data += buff.decode()
        if printlen: print ("received", len(data), "bytes")
        return data

    # Special send command that formats data so it can be send to the stepper motor
    def send_command_scl(sock,cmd):
        cmd = "\0\a"+cmd
        send_command(sock, cmd, terminator='\r')
