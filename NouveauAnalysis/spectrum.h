#ifndef SPECTRUM_H
#define SPECTRUM_H

//C System-Headers
//
//C++ System headers
#include <vector>//vector
#include <string>//string
#include <fstream>//iss*
#include <map>//std::map

//Boost Headers
//

//Miscellaneous Headers
//

class SingleSpectrum {
  public:
    SingleSpectrum(std::string raw_data);
    ~SingleSpectrum();
  private:
    void ParseRawData(std::string raw);

    uint NumLines(std:: string raw_data);

    std::vector<double> sa_power_list;
    std::map<std::string,double> header;

};

class Spectrum {
  public:
    Spectrum();
    ~Spectrum();
};

#endif // SPECTRUM_H
