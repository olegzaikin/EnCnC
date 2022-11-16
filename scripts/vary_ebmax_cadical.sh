#!/bin/bash

# Created on: 16 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Run CaDiCaL SAT solver with different values of the ebmax input parameter.
# It stands for maximum elimination bound for the Bounded Variable Elimination
# (BVE) heuristic, that is used to minimize a CNF on preprocessing.
# For details see
# Niklas Eén, Armin Biere. Effective Preprocessing in SAT Through Variable and
# Clause Elimination // In SAT 2005.
# In CaDiCaL of version 1.5.0, the default value is 16.
# From cadical --help:
#   --elimboundmax=-1..2e6     maximum elimination bound [16]
# Higher value of ebmax usualy leads to more aggressive variable elimination
# though at a high price of greater number of added clauses. Lower values lead
# to minimizing clauses rather than variables.
#
# Three input parameters are requied:
#   CNF         - CNF file name
#   cpu_num     - number of CPU cores
#   start_ebmax - start value of ebmax
# The script generates cpu_num integer values starting from start_ebmax,
# and runs CaDiCaL with the corresponding values of --elimboundmax.
#
# Example:
#   vary_ebmax_cadical.sh problem.cnf 4 5
# starts 4 processes:
#   cadical --elimboundmax=5 problem.cnf &> out_problem_ebmax=5 &
#   cadical --elimboundmax=6 problem.cnf &> out_problem_ebmax=6 &
#   cadical --elimboundmax=7 problem.cnf &> out_problem_ebmax=7 &
#   cadical --elimboundmax=8 problem.cnf &> out_problem_ebmax=8 &
#==============================================================================


version="0.0.1"

script_name="vary_ebmax_cadical.sh"
cadical_name="cadical_1.5"

if ([ $# -ne 4 ]) then
  echo "Usage: $script_name CNF cpu_num conflicts-limit starting_ebmax"
  exit 1
fi

CNF=$1
cpu_num=$2
confl_lim=$3
ebmax_start=$4
echo "CNF           : $CNF"
echo "cpu_num       : $cpu_num"
echo "confl_lim     : $confl_lim"
echo "ebmax_start   : $ebmax_start"

let "ebmax_end = $ebmax_start + $cpu_num - 1"
echo "ebmax_end   : $ebmax_end"

cnfbase=$(basename -- "$CNF" .cnf)
echo "Varying ebmax:"
for (( i=$ebmax_start; i<=$ebmax_end; i++ ))
do
    echo $i
    set -x
    info="ebmax=${i}_confllim=${confl_lim}"
    $cadical_name -c $confl_lim --elimboundmax=$i $CNF -o ${cnfbase}_${info}.cnf -e ext_${cnfbase}_${info} &> simpl_${cnfbase}_$info &
    { set +x; } 2>/dev/null
done
