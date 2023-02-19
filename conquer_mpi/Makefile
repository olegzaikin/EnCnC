CPP = mpicxx
CPPFLAGS = -cxx=g++ -O3 -std=c++11

conquer_mpi: conquer_mpi.o
	${CPP} ${CPPFLAGS} conquer_mpi.o -o conquer_mpi

conquer_mpi.o: conquer_mpi.cpp
	${CPP} ${CPPFLAGS} conquer_mpi.cpp -c

clean:
	rm -rf *.o
	rm conquer_mpi
	clear
