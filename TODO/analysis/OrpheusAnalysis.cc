// OrpheusAnalysis
// Program to perform data analysis for the Orpheus experiment
// Written by Gray Rybka
// Modified by Ari Brill, 7/23/14

#include "OrpheusAnalysis.hh"
#include <iostream>
#include <fstream>
#include <postgresql/libpq-fe.h> // requires libpq-dev
#include <cstdlib>
#include <cmath>
#include <gsl/gsl_multifit.h>

//Boltzmann's constant
const double kB=1.3806488e-23; //Watts / Hz / K

// Function to connect to Orpheus database and return vector with info and data
// for all runs not set to be ignored
vector<RunDef> loadRunsFromDB() {
    // make empty vector
    vector <RunDef> ret;
    
    // connect to Orpheus database
    PGconn *conn;
    PGresult *res;

    conn = PQconnectdb("dbname=orpheus host=localhost user=orpheus\
            password=orpheus");
    if (PQstatus(conn) == CONNECTION_BAD) {
        perror("PQconnectdb: couldn't connect");
        PQclear(res);
        PQfinish(conn);
        return ret;
    }

    // get experiment info
    cout << "Loading runs from database..." << endl;
    res = PQexec(conn, "SELECT main.actual_center_freq, main.sa_span,\
            main.fft_length, main.fitted_hwhm, main.effective_volume,\
            main.bfield, main.noise_temperature, main.sa_averages,\
            sa_data.sa_data FROM main, sa_data WHERE main.id = sa_data.id AND\
            main.ignore IS NOT TRUE");
    if (PQresultStatus(res) != PGRES_TUPLES_OK) {
        perror("PQexec: couldn't select");
        PQclear(res);
        PQfinish(conn);
        return ret;
    }
    int nruns = PQntuples(res); // number of runs
    cout << nruns << " runs loaded" << endl;

    // for each run, put info in a RunDef class and push it on the vector
    for (int i = 0; i < nruns; i++) {
        RunDef toadd;
        toadd.f0 = atoi(PQgetvalue(res, i, 0));
        toadd.freq_span = atof(PQgetvalue(res, i, 1));
        toadd.fft_length = atof(PQgetvalue(res, i, 2));
        toadd.hwhm = atof(PQgetvalue(res, i, 3));
        toadd.effective_volume = atof(PQgetvalue(res, i, 4));
        toadd.bfield = atof(PQgetvalue(res, i, 5));
        toadd.noise_temperature = atof(PQgetvalue(res, i, 6));
        toadd.num_averages = atoi(PQgetvalue(res, i, 7));
        toadd.spectrum_data = PQgetvalue(res, i, 8);
        ret.push_back(toadd);
    }

    PQclear(res);
    PQfinish(conn);
    return ret;
}


#define ALPHA 7.2973525376e-3
//h in eV s
#define H 6.58211899e-16*2*M_PI
double g_ksvz=0.97;
//m is in eV
//returns in GeV^-1
double get_axion_coupling(double g,double m) {
    return 1e-7*(m/0.62)*(ALPHA*g/M_PI);
}

//f is in MHz
//response in GeV^-1
double get_axion_KSVZ_coupling(double f) {
    double m=f*H*1e6;
    return get_axion_coupling(g_ksvz,m);
}

int main(int argc,char *argv[]) {
    vector<RunDef> runs=loadRunsFromDB();
    Spectrum thespectrum;
    Spectrum axionpower;
    vector<Spectrum> g_predictions;
    double freq_min=0;
    double freq_max=0;
    double bin_size=0; // in frequency
    // bin_length ~ # points / (axion width / (frequency span / # points))
    unsigned int bin_length = 72; // in points
    for(unsigned int onrun=0;onrun<runs.size();onrun++) {
        if ((onrun % 25) == 0) {
            cout << "Processing run " << onrun << " of " << runs.size() << endl;
        }
        // actual number of points is 2/3 nominal fft length, unsure why
        unsigned int fft_length = \
            static_cast<unsigned int>(round((runs[onrun].fft_length*(2./3.))));
        thespectrum.loadFromDBString(runs[onrun].spectrum_data, fft_length,\
                runs[onrun].f0, runs[onrun].freq_span, bin_length);
        bin_size=thespectrum.getBinWidth();
        thespectrum.chopBins(200, 200, bin_size); // ignore ends of spectrum
        if((freq_min==0)||(thespectrum.freq_start<freq_min))
            freq_min=thespectrum.freq_start;
        if((freq_max==0)||((thespectrum.freq_start+thespectrum.freq_span) > \
                    freq_max))
            freq_max=thespectrum.freq_start+thespectrum.freq_span;

        // background subtract by fitting to a polynomial
        remove_background(thespectrum, bin_size, 5);
        
        //expected power from axion at each bin
        double Q=runs[onrun].f0/(2.0*runs[onrun].hwhm);
        axionpower=getKSVZPowerInSpectrum(runs[onrun].effective_volume,runs[onrun].bfield,thespectrum,Q,runs[onrun].f0);
        //normalize power to temperature
        double noise_power=kB*runs[onrun].noise_temperature *
            (thespectrum.getBinWidth()*1e6);
        double mean=thespectrum.getPowerMean();
        thespectrum*=(noise_power/mean);
        thespectrum+=(-noise_power);
        //now each bin is in Watts above noise
        //put in uncertainty due to number of averages
        for(unsigned int i=0;i<thespectrum.length;i++) {
            thespectrum.uncertainty[i] = 
                noise_power / sqrt(runs[onrun].num_averages * bin_length);
        }

        //now we calculate a spectrum of predicted multiple of g factor squared
        Spectrum g_prediction=thespectrum;
        for(unsigned int i=0;i<thespectrum.length;i++) {
            //not really power.  unitless
            g_prediction.power[i]=thespectrum.power[i]/axionpower.power[i];
            //suffer like g did
            g_prediction.uncertainty[i]=thespectrum.uncertainty[i]/axionpower.power[i];
        }
        //if this is the first one, let's save a copy for plotting
        if(onrun==50) {
            ofstream powspectrum("power_spectrum.txt");
            thespectrum.print(powspectrum);
            powspectrum.close();
            ofstream singlescan("single_scan_g_prediction.txt");
            singlescan << "#Frequency (MHz)  G^2 prediction (GeV^-2)" << endl;
            for(unsigned int i=0;i<g_prediction.length;i++) {
                singlescan.precision(10);
                singlescan << g_prediction.getBinMidFreq(i) << " " << g_prediction.power[i]*(pow(get_axion_KSVZ_coupling(g_prediction.getBinMidFreq(i)),2.0)) << " " << g_prediction.uncertainty[i]*(pow(get_axion_KSVZ_coupling(g_prediction.getBinMidFreq(i)),2.0)) << endl;
            }
            singlescan.close();

        }
        g_predictions.push_back(g_prediction);
    }
    //now make a grand spectrum
    double total_span=freq_max-freq_min;
    unsigned int total_bins=(unsigned int)(floor(total_span/bin_size))-1;
    Spectrum grand_g_prediction(total_bins);
    grand_g_prediction.freq_start=freq_min;
    grand_g_prediction.freq_span=total_span;
    grand_g_prediction.zero();
    for(unsigned int i=0;i<grand_g_prediction.length;i++) {
        double f=grand_g_prediction.getBinMidFreq(i);
        for(unsigned int ons=0;ons<g_predictions.size();ons++) {
            unsigned int binno=g_predictions[ons].getBinAtFreq(f);
            if(binno==INT_MAX) continue;
            if(grand_g_prediction.uncertainty[i]==0) {
                grand_g_prediction.power[i]=g_predictions[ons].power[binno];
                grand_g_prediction.uncertainty[i]=g_predictions[ons].uncertainty[binno];
            } else {
                double a=grand_g_prediction.power[i];
                double b=g_predictions[ons].power[binno];
                double sa=grand_g_prediction.uncertainty[i];
                double sb=g_predictions[ons].uncertainty[binno];
                double taua=1.0/(sa*sa);
                double taub=1.0/(sb*sb);
                grand_g_prediction.power[i]=(taua*a+taub*b)/(taua+taub);
                grand_g_prediction.uncertainty[i]=sqrt(1.0/(taua+taub));
            }

        }
    }
    //now make some limits
    Spectrum thelimits=grand_g_prediction;
    for(unsigned int i=0;i<thelimits.length;i++) {
        double x=grand_g_prediction.power[i];
        if(x<0) x=0;
        thelimits.power[i]=x+2.0*grand_g_prediction.uncertainty[i];
    }
//    /*
    for(unsigned int i=0;i<thelimits.length;i++) {
        thelimits.power[i] = sqrt(thelimits.power[i]) * 
            get_axion_KSVZ_coupling(thelimits.getBinMidFreq(i));
        //thelimits.uncertainty[i]=H*thelimits.getBinMidFreq(i)*1e6;
        thelimits.uncertainty[i] = 
            get_axion_KSVZ_coupling(thelimits.getBinMidFreq(i));
    }
    // rebin the limits, keeping the most conservative sensitivity in each bin
    thelimits.rebin(600); // 120 points ~= 1 MHz with bin_length = 72
    
    // save the limits for plotting
    ofstream limits("limits.txt");
    thelimits.print(limits);
    limits.close();

    ofstream grand_g("grand_g_prediction.txt");
    for(unsigned int i=0;i<grand_g_prediction.length;i++) {
        grand_g.precision(10);
        grand_g << grand_g_prediction.getBinMidFreq(i) << " " << grand_g_prediction.power[i]*(pow(get_axion_KSVZ_coupling(grand_g_prediction.getBinMidFreq(i)),2.0)) << " " << grand_g_prediction.uncertainty[i]*(pow(get_axion_KSVZ_coupling(grand_g_prediction.getBinMidFreq(i)),2.0)) << endl;
    }
    grand_g.close();

    //save a sensitivity plot: what would we get if all bins were zero
    double desired_sigma=1.282; // 90% confidence
    ofstream fout("sensitivity.txt");
    fout << "#Frequency (MHz) g_sensitivity(GeV^-1)" << endl;
    for(unsigned int i=0;i<grand_g_prediction.length;i++) {
        double gsquaredunitless=grand_g_prediction.uncertainty[i]*desired_sigma;
        double g=sqrt(gsquaredunitless)*get_axion_KSVZ_coupling(thelimits.getBinMidFreq(i));
        fout.precision(10);
        fout << grand_g_prediction.getBinMidFreq(i) << " " << g << endl;
    }
    fout.close();
}


//get the axion photon conversion power for a Q of 1
//veff is in cm^3
//B is in Tesla
//f is in GHz
//assumes dark matter density is 0.45 GeV/cm^3
double getMaxKSVZPower(double veff,double B,double f)
{
    return 2.2e-23*(veff/1000.0)*B*B*(f/100.0)*(1.0/1e5);
}

double getLorentzian(double f0,double f,double Q)
{
    double Gamma=f/(2.0*Q);
    return Gamma*Gamma/( (f-f0)*(f-f0)+Gamma*Gamma);
}

Spectrum getKSVZPowerInSpectrum(double veff,double B,Spectrum &spectrumformat,double Q,double f0)
{
    Spectrum ret=spectrumformat;
    for(unsigned int i=0;i<ret.length;i++) {
        double f=ret.getBinMidFreq(i);
        // ignore veff and calculate a better value
        //veff = get_veff(f);
        ret.power[i]=getMaxKSVZPower(veff,B,(f/1e3))*Q*getLorentzian(f0,f,Q);
    }
    return ret;
}

// perform gsl_matrix_set for each element of an X matrix of arbitrary order
void set_X_matrix(gsl_matrix *X, double xi, unsigned int index, int order)
{
    for (int i = 0; i <= order; i++) {
        double xprod = 1.0;
        for (int j = 0; j < i; j++)
            xprod *= xi;
        gsl_matrix_set(X, index, i, xprod);
    }
}

// perform a polynomial fit using gsl
// code based on example from:
// https://www.gnu.org/software/gsl/manual/html_node/Fitting-Examples.html
void polynomial_fit(int order, double *spectrum_power, double *xfreq,\
        unsigned int length, double *best_fit)
{
    double xi, yi, ei, chisq;
    gsl_matrix *X, *cov;
    gsl_vector *y, *w, *c;

    // allocate memory
    X = gsl_matrix_alloc(length, (order + 1));
    y = gsl_vector_alloc(length);
    w = gsl_vector_alloc(length);

    c = gsl_vector_alloc(order + 1);
    cov = gsl_matrix_alloc(order + 1, order + 1);

    // set up vectors
    for (unsigned int i = 0; i < length; i++) {
        xi = xfreq[i];
        yi = spectrum_power[i];
        set_X_matrix(X, xi, i, order);
        gsl_vector_set(y, i, yi);
    }

    // perform the fit
    gsl_multifit_linear_workspace *work = 
        gsl_multifit_linear_alloc(length, order+1);
    gsl_multifit_linear(X, y, c, cov, &chisq, work);
    gsl_multifit_linear_free(work);

    // save the best fit parameters
    for (int i = 0; i <= order; i++)
        best_fit[i] = gsl_vector_get(c, i);

    // free memory
    gsl_matrix_free(X);
    gsl_vector_free(y);
    gsl_vector_free(c);
    gsl_matrix_free(cov);
}

// set the array of fitted power values using best fit parameters
void fit_power(int order, unsigned int length, double *xfreq,\
        double *fitted_power, double *best_fit)
{
    double xi, yi;
    for (unsigned int i = 0; i < length; i++) {
        xi = xfreq[i];
        yi = 0;
        // y(x) = c0 + c1*x + c2*x^2 + ... + cn*x^n
        for (int j = 0; j <= order; j++) {
            double xprod = 1.0;
            for (int k = 0; k < j; k++)
                xprod *= xi;
            yi += best_fit[j]*xprod;
        }
        fitted_power[i] = yi;
    }
}

// fit the spectrum power to a polynomial and subtract
void remove_background(Spectrum &spectrum, double bin_size, int order)
{
    const int polynomial_order = order;
    double best_fit[polynomial_order + 1];
    const unsigned int length = spectrum.length;
    double freq_start = spectrum.freq_start;
    double fitted_power[length];
    double xfreq[length];
    for (unsigned int i = 0; i < length; i++)
        xfreq[i] = freq_start + ((double)i)*bin_size;
    polynomial_fit(polynomial_order, spectrum.power, xfreq, length, best_fit);
    fit_power(polynomial_order, length, xfreq, fitted_power, best_fit); 
    for (unsigned int i = 0; i < length; i++) {
        spectrum.power[i] /= fitted_power[i];
    }
}
