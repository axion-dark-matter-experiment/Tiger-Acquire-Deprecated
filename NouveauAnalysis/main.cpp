#include "flatfileinterface.h"
#include "spectrum.h"

#include <iostream>

#include <chrono>

int main(int argc, char *argv[]) {

    auto start = std::chrono::high_resolution_clock::now();

    for (int i = 0 ; i < 1 ; i++) {
        FlatFileReader("/home/bephillips2/workspace/Electric_Tiger_Control_Code/data/45_12_12_11.08.2016/");
    }

    auto end = std::chrono::high_resolution_clock::now();
    std::chrono::duration<double, std::milli> fp_ms = end - start;
    auto time_taken = fp_ms.count();

    std::cout<<"Took "<<time_taken<<" ms."<<std::endl;
}

