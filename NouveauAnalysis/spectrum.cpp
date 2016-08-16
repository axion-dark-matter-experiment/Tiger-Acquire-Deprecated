//Header for this file
#include "spectrum.h"
//C System-Headers
#include <termios.h>  /* POSIX terminal control definitions */
#include <sys/ioctl.h>
#include <fcntl.h>//fopen(),fclose()
#include <unistd.h>//read(), write()
#include <stdio.h>

//C++ System headers
#include <vector>//vector
#include <string>//string
#include <fstream>//iss*
#include <chrono>// timing functions
#include <cmath>//sqrt, abs
#include <iostream>//cout
#include <typeinfo>//typeid
#include <algorithm> // transform, find, count
#include <functional> // plus/minus
#include <utility>//std::make_pair
#include <map>//std::map

//Boost Headers
#include <boost/algorithm/string.hpp>//split() and is_any_of for parsing .csv files
#include <boost/lexical_cast.hpp>//lexical cast (unsurprisingly)
#include <dirent.h>

//Miscellaneous Headers
#include <omp.h>//OpenMP pragmas

SingleSpectrum::SingleSpectrum(std::string raw_data){

}

SingleSpectrum::~SingleSpectrum(){}

uint SingleSpectrum::NumLines(std::string raw_data){

//        const char* c_file_name = raw_data.c_str();

//        std::ifstream file(c_file_name);

//        // new lines will be skipped unless we stop it from happening:
//        file.unsetf(std::ios_base::skipws);

//        // count the newlines with an algorithm specialized for counting:
//        unsigned line_count = std::count(
//                                  std::istream_iterator<char>(file),
//                                  std::istream_iterator<char>(),
//                                  '\n');

        size_t line_count = std::count(raw_data.begin(), raw_data.end(), '\n');

        return line_count;
}

void SingleSpectrum::ParseRawData(std::string raw_data){
    uint lines = NumLines ( raw_data );

    for (uint i = 0; i < 11 ; i++){
        std::vector<std::string> strs;
        boost::split(strs, input, boost::is_any_of(";"));
        if(strs.size()>=3) {
            std::string key=strs.at(0);
            std::string data=strs.at(1);
            std::string type=strs.at(2);

            std::pair<std::string,std::string> val=std::make_pair(data,type);
            all_the_things[key]=val;
        }
    }


}
