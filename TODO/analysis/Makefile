TARGETS := OrpheusAnalysis
OBJECTS := Spectrum.o
LIBS := -lpq -lgsl -lgslcblas

all: $(OBJECTS) $(TARGETS)

$(OBJECTS) : %.o : %.cc %.hh
	$(CXX) $(CXXFLAGS) -c $< -o $@

$(TARGETS) : % : %.cc $(OBJECTS)
	$(CXX) $(CXXFLAGS) -o $@ $< $(OBJECTS) $(LIBS)

clean:
	rm -f $(OBJECTS)
	rm -f $(TARGETS)

				   
