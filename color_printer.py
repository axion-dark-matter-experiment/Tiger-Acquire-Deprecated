class ColorPrinter:
    """
    Functor that allows colored text to be printed to the terminal.
    The color of output text is set based on an argument passed to the constructor.
    The overloaded __call__ method is what actually outputs text to the terminal.
    
    Example usage:
        print_green = ColorPrint("Green")
        ...
        print_greem("Text!") -> Text! (printed to terminal in green)
        
    Color conventions:
        Purple: Header text
        Green: Okay, or Success status
        Blue: Finished or Done status
        Yellow: Warning or very high attention but not an error
        Red: Errors
    """
    
    def __init__(self, color):
        """
        Initialize the functor by specifying what color output text should be.
        
        Args:
            color: Name of the color specified as a string, options are 
            Purple, Green, Blue, Yellow, or Red.
        """
        self.__determine_color( color )
        
    def __call__(self, message):
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