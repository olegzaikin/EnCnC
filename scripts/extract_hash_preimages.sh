#!/bin/sh

# Created on: 10 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Use reconstruction-extension-stack to construct a satisfying assignment of the original
# (unsimplified) CNF, and then extract the first 512 bits (preimage) and convert to hex.
#
# NB1: reconstruction-extension-stack is built by CaDiCaL, option -e
# NB2: extend-solution.sh is a script from CaDiCaL sources.
#
#==============================================================================

version="0.0.2"

scriptname="extract_md4_preimages.sh"

[ $# -eq 3 ] || \
{
  echo "Usage: $scriptname solver-output reconstruction-extension-stack original-cnf"
  exit 1
}

solver_output=$1
extension_stack=$2
original_cnf=$3

./extend-solution.sh $solver_output $extension_stack > ext_sol
python3 ./sort_solution.py $original_cnf ./ext_sol | tee hex_$(basename -- $solver_output)
rm ext_sol
