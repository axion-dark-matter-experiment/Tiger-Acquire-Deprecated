#include "Spectrum.hh"
#include <fstream>
#include <sstream>
#include <stdlib.h>

Spectrum::Spectrum()
{
    power=NULL;
    uncertainty=NULL;
    freq_start=0;
    freq_span=1;
    length=0;
}

Spectrum::Spectrum(unsigned int l)
{
    power=NULL;
    uncertainty=NULL;
    freq_start=0;
    freq_span=1;
    length=0;
    resize(l);
}

Spectrum::~Spectrum()
{
    delete [] power;
    delete [] uncertainty;
}
 
Spectrum::Spectrum(const Spectrum &s)
{
    power=NULL;
    uncertainty=NULL;
    freq_start=0;
    freq_span=1;
    length=0;
    (*this)=s;
}
    
Spectrum &Spectrum::operator=(const Spectrum &s)
{
    resize(s.length);
    freq_start=s.freq_start;
    freq_span=s.freq_span;
    for(unsigned int i=0;i<length;i++) {
        power[i]=s.power[i];
        uncertainty[i]=s.uncertainty[i];
    }
    return *this;
}
    
Spectrum &Spectrum::operator*=(double d)
{
    for(unsigned int i=0;i<length;i++) {
        power[i]*=d;
        uncertainty[i]*=d;
    }
    return *this;
}

Spectrum &Spectrum::operator+=(double d)
{
    for(unsigned int i=0;i<length;i++) {
        power[i]+=d;
    }
    return *this;
}


void Spectrum::resize(unsigned int l)
{
    delete [] power;
    delete [] uncertainty;
    length=l;
    power=new double[length];
    uncertainty=new double[length];
}
    
double Spectrum::getBinStartFreq(unsigned int i) const
{
    return freq_start+((double)i)*freq_span/((double)length);
}
    
double Spectrum::getBinMidFreq(unsigned int i) const
{
    return getBinStartFreq(i)+0.5*getBinWidth();
}
    
double Spectrum::getPowerStdev() const
{
    double x=0;
    double xx=0;
    for(unsigned int i=0;i<length;i++) {
        x+=power[i];
        xx+=power[i]*power[i];
    }
    double ex=x/((double)length);
    double exx=xx/((double)length);
    return sqrt(exx-ex*ex);
}

double Spectrum::getPowerMean() const
{
    double x=0;
    for(unsigned int i=0;i<length;i++) {
        x+=power[i];
    }
    double ex=x/((double)length);
    return ex;
}



void Spectrum::print(ostream &out) const
{
    for(unsigned int i=0;i<length;i++) {
        out.precision(10);
       out << getBinStartFreq(i) << " " << power[i] << " " << uncertainty[i] << endl;
    }
}

void splitSALine(string &s,string &a,string &b)
{
    size_t comma=s.find(',');
    if(comma==string::npos) {
        a=s;
        b="";
        while(a.size()!=0&&((a[a.size()-1]==13)||(a[a.size()-1]==10))) {
            a=a.substr(0,a.size()-1);
        }
        return;
    }
    a=s.substr(0,comma);
    b=s.substr(comma+1,s.size()-comma-1);
    while(a.size()!=0&&((a[a.size()-1]==13)||(a[a.size()-1]==10)))
       a=a.substr(0,a.size()-1);
    while(b.size()!=0&&((b[b.size()-1]==13)||(b[b.size()-1]==10)))
       b=b.substr(0,b.size()-1);


}

void Spectrum::loadFromSAFile(const char *fname)
{
    ifstream fin(fname);
    string line;
    string a;
    string b;
    //read off heading
    while(line.substr(0,4)!="DATA"&&fin.good()) {
        getline(fin,line);
        splitSALine(line,a,b);
        if(a=="Number of Points") {
  //          cout << "npoints " << atoi(b.c_str()) << endl;
            resize(atoi(b.c_str()));
        }
        if(a=="Start Frequency") {
            freq_start=atof(b.c_str())/1e6;
//            cout << "start frequency " << freq_start << endl;
        }
        if(a=="Stop Frequency") {
            freq_span=atof(b.c_str())/1e6-freq_start;
    //        cout << "span frequency " << freq_span << endl;
        }
    }
    for(unsigned int i=0;i<length;i++) {
        getline(fin,line);
        splitSALine(line,a,b);
        power[i]=pow10(atof(b.c_str())/10.0);
        uncertainty[i]=power[i];
    }
    fin.close();
}

void Spectrum::loadFromDBString(string &data, unsigned int fft_length,\
        double f0, double span, unsigned int bin_length)
{
    // choose bin size (approximate)
    // bin_window ~ # points / (0.5 * axion width / (frequency span / # points))
    // bins overlap in half bin size increments
    int bin_window = (bin_length / 2);
    // set power and uncertainty to the correct number of points
    length = (unsigned int)(fft_length / bin_window) - 1; // rounds down
    resize(length);
    // set freq start and span
    freq_start = f0 - (span / 2);
    freq_span = span;
    // read points from data string
    istringstream ss(data);
    string point;
    double prev_sum = 0; // sum of previous 36 FFT points
    double curr_sum = 0; // running sum of current FFT points
    unsigned int leni = 0; // index for running over binned spectrum length
    unsigned int ffti = 0; // index for running over fft length
    for (ffti; ffti < fft_length; ffti++) {
        if ((leni >= length) || (!getline(ss, point, ','))) {
            break;
        }
        curr_sum += pow10(atof(point.c_str()) / 10.0);
        if ((ffti % bin_window) == bin_window - 1) {
            // average over all the points in the current and previous sums
            if (ffti != bin_window - 1) {
                power[leni] = (curr_sum + prev_sum) / (bin_window*2);
                uncertainty[leni] = power[leni];
                leni++;
            }
            prev_sum = curr_sum;
            curr_sum = 0;
        }
    }
}

// chop off the first start_chop bins and the last end_chop bins
void Spectrum::chopBins(unsigned int start_chop, unsigned int end_chop,\
        double bin_size)
{
    unsigned int newlength = length - start_chop - end_chop;
    double *newpower = new double[newlength];
    double *newuncertainty = new double[newlength];
    unsigned int newi = 0;
    for (unsigned int i = 0; i < length; i++) {
        if ((i >= start_chop) && (i < length - end_chop)) {
            newpower[newi] = power[i];
            newuncertainty[newi] = uncertainty[i];
            newi++;
        }
    }
    delete [] power;
    delete [] uncertainty;
    power = newpower;
    uncertainty = newuncertainty;
    length = newlength;
    freq_start = freq_start + bin_size*start_chop;
    freq_span = freq_span - bin_size*(start_chop + end_chop);
}

double Spectrum::getBinWidth() const
{
    return freq_span/((double)length);
}
    
unsigned int Spectrum::getBinAtFreq(double f) const
{
    if(f<freq_start || f > freq_start+freq_span) {
        return INT_MAX;
    }
    return (unsigned int)floor(((double)length)*(f-freq_start)/freq_span);
}
    
void Spectrum::zero()
{
    for(unsigned int i=0;i<length;i++)
    {
        power[i]=0;
        uncertainty[i]=0;
    }
}
