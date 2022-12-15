#!/bin/bash

# Created on: 7 Dec 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Run species of autom_constr_gen_crypt_hash.py:
# for the first cube type, the last cube type, and random ones. 
#==============================================================================

autom_constr_gen_crypt_hash.py

version="0.0.1"
script_name="run_autom_constr_gen.sh"
child_script_name="autom_constr_gen_crypt_hash.py"

if [ $# -ne 2 ]; then
  echo "Usage: $script_name CNF cpu_num"
  exit 1
fi

CNF=$1
cpu_num=$2
echo "CNF         : $CNF"
echo "cpu_num     : $cpu_num"

if [ $cpu_num -le 0 ]; then
  echo "cpu_num must be > 0"
  exit 1
fi

set -x
random_runs=$(( $cpu_num - 2 ))
echo "random_runs : $random_runs"

# > /dev/null 2>&1
python3 $child_script_name $CNF -cubetype=first &
if [ $cpu_num -eq 1 ]; then
  exit 1
fi

python3 $child_script_name $CNF -cubetype=last &
if [ $cpu_num -eq 2 ]; then
  exit 1
fi

for (( i=0; i<$random_runs; i++ ))
do
    python3 $child_script_name $CNF -cubetype=random -seed=$i &
done
