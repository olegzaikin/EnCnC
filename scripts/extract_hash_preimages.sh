#!/bin/bash

# Created on: 10 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Use reconstruction-extension-stack to construct a satisfying assignment of the original
# (unsimplified) CNF, and then extract the first 512 bits (preimage) and convert to hex.
#
# NB1: reconstruction-extension-stack is built by CaDiCaL, option -e
# NB2: extend-solution.sh is a script from CaDiCaL sources.
# NB3: extend-solution.sh also needs color.sh from CaDiCaL sources.
#
#==============================================================================

version="0.0.3"

scriptname="extract_md4_preimages.sh"

if (($# < 3)); then
  echo "Usage: $scriptname solver-output reconstruction-extension-stack original-cnf [input-vars]"
  exit 1
fi

solver_output=$1
extension_stack=$2
original_cnf=$3

#set -x

if [ $# == 4 ]; then
  input_vars=$4
fi

./extend-solution.sh $solver_output $extension_stack > ext_sol
python3 ./sort_solution.py $original_cnf ./ext_sol $input_vars | tee hex_$(basename -- $solver_output)
rm ext_sol
