#include <string>
#include <vector>
#include "Spectrum.hh"
using namespace std;

class RunDef
{
public:
    double f0; //center frequency, MHz
    double hwhm; //half width half max, MHz
    double noise_temperature; //in kelvin
    double num_averages; //how many FFTs were averaged
    double effective_volume; //in cm^3
    double bfield; //in Tesla
    double freq_span; //freqency span, MHz
    double fft_length; //number of points in FFT
    string spectrum_data;
};

vector<RunDef> loadRunDef(const char* fname);

//get the axion photon conversion power for a Q of 1
//veff is in cm^3
//B is in Tesla
//f is in GHz
//assumes dark matter density is 0.45 GeV/cm^3
double getMaxKSVZPower(double veff,double B,double f);
//gets above except as a spectrum with center f and Q of Q
Spectrum getKSVZPowerInSpectrum(double veff,double B,Spectrum &spectrumformat,double Q,double f0);

void remove_background(Spectrum &spectrum, double bin_size);
