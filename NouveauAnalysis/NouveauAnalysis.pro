QT += core
QT -= gui

TARGET = NouveauAnalysis
CONFIG += console
CONFIG -= app_bundle

CONFIG += c++11

QMAKE_CXXFLAGS+= -fopenmp
#QMAKE_CXXFLAGS+= -O3
QMAKE_LFLAGS +=  -fopenmp

TEMPLATE = app

SOURCES += main.cpp \
    flatfileinterface.cpp \
    spectrum.cpp

HEADERS += \
    flatfileinterface.h \
    spectrum.h

