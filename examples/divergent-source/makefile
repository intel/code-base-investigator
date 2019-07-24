all: histogram_cpu histogram_gpu

histogram_cpu: makefile main.cpp
	icpc -O3 -xHost -qopenmp -o histogram_cpu main.cpp private_histogram.cpp -qopenmp-offload=host -g

histogram_gpu: makefile main.cpp
	icpc -O3 -xHost -qopenmp -o histogram_gpu main.cpp shared_histogram.cpp -qopenmp-offload=host -g

clean:
	rm *.o histogram_cpu histogram_gpu
