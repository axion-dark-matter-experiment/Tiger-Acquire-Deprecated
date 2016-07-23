%module modetrack

%{
#include "modetrack.h"
%}

%include "std_string.i"

%apply const std::string& {std::string* c_str};

class ModeTrack
{
public:
    ModeTrack();
    ~ModeTrack();
    void FromFile(std::string config_name);
    void SetBackground(std::string background_str);
    double GetPeaksGauss(std::string data_str,int mode_number);
    double GetPeaksBiLat(std::string data_str,int mode_number);
    double GetMaxPeak(std::string data_str);
};
