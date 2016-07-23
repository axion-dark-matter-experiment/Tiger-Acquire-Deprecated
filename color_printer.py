class ColorPrinter:
    
    def __init__(self, color):
        self.__determine_color( color )
        
    def __call__(self, message):
#     print "I got called with %r!" % (a,)
        self.__c_func(message)
        
    def __determine_color(self, color):
        if(color == "Purple"):
            self.head = '\033[95m'
        elif(color == "Green"):
            self.head = '\033[92m'
        elif(color == "Blue"):
            self.head = '\033[94m'
        elif(color == "Yellow"):
            self.head = '\033[93m'
        elif(color == "Red"):
            self.head = '\033[91m'
        else:
            self.head = ''
        
    def __c_func(self, message):
        print (self.head + str(message) + '\033[0m')