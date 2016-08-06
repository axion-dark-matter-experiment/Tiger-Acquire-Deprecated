#include <iostream>
#include <math.h>
#include <limits.h>

using namespace std;

class Spectrum
{
public:
    Spectrum();
    Spectrum(unsigned int l);
    Spectrum(const Spectrum &s);
    ~Spectrum();
    Spectrum &operator=(const Spectrum &s);
    Spectrum &operator*=(double d);
    Spectrum &operator+=(double d);

    void resize(unsigned int l);
    double getBinStartFreq(unsigned int i) const;
    double getBinMidFreq(unsigned int i) const;
    double getPowerStdev() const;
    double getPowerMean() const;
    double getBinWidth() const;
    unsigned int getBinAtFreq(double f) const; //returns MAX_INT

    void print(ostream &out) const;
    void zero();
    void loadFromSAFile(const char *fname);
    void loadFromDBString(string &data, unsigned int fft_length, double f0,\
            double span, unsigned int bin_length);
    void chopBins(unsigned int start_chop, unsigned int end_chop,\
            double bin_size);

    double *power;
    double *uncertainty;
    double freq_start;
    double freq_span;
    unsigned int length;

};

