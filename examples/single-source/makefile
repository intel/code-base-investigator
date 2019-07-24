all: histogram

histogram: makefile main.cpp
	icpc -O3 -xHost -qopenmp -o histogram main.cpp -qopenmp-offload=host -g

clean:
	rm *.o histogram
