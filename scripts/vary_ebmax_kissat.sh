#!/bin/bash

# Created on: 15 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Run kissat SAT solver with different values of the ebmax input parameter.
# It stands for maximum elimination bound for the Bounded Variable Elimination
# (BVE) heuristic, that is used to minimize a CNF on preprocessing.
# For details see
# Niklas Eén, Armin Biere. Effective Preprocessing in SAT Through Variable and
# Clause Elimination // In SAT 2005.
# In kissat of version sc2021, the default value is 16.
# From kissat --help:
#   --eliminatebound=0..2^13   maximum elimination bound [16]
# Higher value of ebmax usualy leads to more aggressive variable elimination
# though at a high price of greater number of added clauses. Lower values lead
# to minimizing clauses rather than variables.
#
# Three input parameters are requied:
#   CNF         - CNF file name
#   cpu_num     - number of CPU cores
#   start_ebmax - start value of ebmax
#   kissat_conf - kissat configuration (default, sat, or unsat)
# The script generates cpu_num even positive numbers starting from start_ebmax,
# and runs kissat with the corresponding values of -eliminatebound and given
# configuration.
#
# Example:
#   vary_ebmax_kissat.sh problem.cnf 4 0 sat
# starts 4 processes:
#   kissat --eliminatebound=0 problem.cnf &> out_problem_conf=sat_ebmax=0 &
#   kissat --eliminatebound=2 problem.cnf &> out_problem_conf=sat_ebmax=2 &
#   kissat --eliminatebound=4 problem.cnf &> out_problem_conf=sat_ebmax=4 &
#   kissat --eliminatebound=6 problem.cnf &> out_problem_conf=sat_ebmax=6 &
#==============================================================================


version="0.0.2"

script_name="vary_ebmax_kissat.sh"
kissat_name="kissat_sc2021"

if ([ $# -ne 4 ]) then
  echo "Usage: $script_name CNF cpu_num start_ebmax kissat_conf"
  exit 1
fi

CNF=$1
cpu_num=$2
ebmax_start=$3
kissat_conf=$4
echo "CNF         : $CNF"
echo "cpu_num     : $cpu_num"
echo "ebmax_start : $ebmax_start"
echo "kissat_conf : $kissat_conf"

let "ebmax_end = $ebmax_start + $cpu_num - 1"
echo "ebmax_end   : $ebmax_end"

cnfbase=$(basename -- "$CNF" .cnf)
ebmax=$ebmax_start
echo "Varying ebmax:"
for (( i=1; i<=$cpu_num; i++ ))
do
    echo $ebmax
    set -x
    $kissat_name --$kissat_conf --eliminatebound=$ebmax $CNF &> out_${cnfbase}_conf=${kissat_conf}_ebmax=$ebmax &
    { set +x; } 2>/dev/null
    ebmax=$(( $ebmax + 2 ))
done
