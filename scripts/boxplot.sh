#!/bin/bash

for f in stat_*; do
    echo $f
    a="${f:5}"
    echo $a
    python3 boxplot_solvers.py $f sample_results_${a}.csv
done
