import sys #basic std library functions

def c_print(message,color):
    if(color == "Purple"):
        print ('\033[95m' + str(message) + '\033[0m')
    elif(color == "Green"):
        print ('\033[92m' + str(message) + '\033[0m')
    elif(color == "Blue"):
        print ('\033[94m' + str(message) + '\033[0m')
    elif(color == "Yellow"):
        print ('\033[93m' + str(message) + '\033[0m')
    elif(color == "Red"):
        print ('\033[91m' + str(message) + '\033[0m')
    else:
        print(str(message))
