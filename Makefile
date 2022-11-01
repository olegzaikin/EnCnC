CPP = g++
CPPFLAGS = -O3 -std=c++20 -fopenmp

conquer: conquer.o
	${CPP} ${CPPFLAGS} conquer.o -o conquer

conquer.o: conquer.cpp
	${CPP} ${CPPFLAGS} conquer.cpp -c

clean:
	rm -rf *.o
	rm conquer
	clear
