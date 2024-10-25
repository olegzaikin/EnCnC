Estimate-and-Cube-and-Conquer
=========================================================

### About

Sources and benchmarks for the paper

Oleg Zaikin. Inverting Cryptographic Hash Functions via Cube-and-Conquer // Journal of Artificial Intelligence Research. Vol. 81. 2024. pp. 359-399.

### Directories overview

/cnfs - TA-programs and the corresponding CNFs which encode preimage attacks on step-reduced MD4 and MD5 with added Dobbetin-like constraints.

/conquer_mt - a multithreaded C++ implementation of the conquer phase of Cube-and-Conquer.

/conquer_mpi - an MPI C++ implementation of the conquer phase of Cube-and-Conquer.

/scripts - scripts for generating CNFs, choosing the best cubing phase, and extracting a preimage from the found solution.

The main script for finding the best cubing phase is find_cnc_threshold.py.

### Citation

If you use these sources or/and data, please cite:
```
@article{Zaikin-JAIR2024,
  author       = {Oleg Zaikin},
  title        = {Inverting Cryptographic Hash Functions via {Cube-and-Conquer}},
  journal      = {Journal of Artificial Intelligence Research},
  volume       = {81},
  year         = {2024},
  pages        = {359--399}
}

```
