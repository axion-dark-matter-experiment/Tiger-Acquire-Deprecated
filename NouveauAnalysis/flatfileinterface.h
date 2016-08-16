#ifndef FLATFILEINTERFACE_H
#define FLATFILEINTERFACE_H

//C++ System headers
#include <vector>//vector
#include <string>//string

//C System-Headers
//
//C++ System headers
#include <vector>//vector
#include <string>//string
//Boost Headers
//
//Miscellaneous Headers
//

class FlatFileReader
{
public:
    FlatFileReader(std::string dir_name);
    ~FlatFileReader();

    std::string at(uint index);

    uint size();
    bool has(uint index);

private:
    std::vector<std::string> raw_data_list;

    std::vector<std::string> EnumerateFiles(std::string dir_name, std::string sift_term);
    uint GetFileLines(std:: string file_name);

    std::string FastRead( std::string file_name);

};

#endif // FLATFILEINTERFACE_H
