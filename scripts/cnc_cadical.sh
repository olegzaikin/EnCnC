#!/bin/sh

# Created on: 3 Apr 2020
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Run cubing phase of Cube-and-Conquer and then conquer by incremental solver.
#
#==============================================================================

version="0.0.2"
script="cnc_cadical.sh"

if ([ $# -ne 2 ]) then
  echo "Usage: $script CNF cpulim"
  exit 1
fi

CNF=$1
CPULIM=$2

DIR=.
CDCL="cadical_1.5"
LOOKAHEAD="march_cu"

printf "CNF : %s\n" $CNF
printf "CPULIM : %d\n" $CPULIM

CNFBASE=$(basename -- "$CNF")
CNFNOEXT="${CNFBASE%.*}"
printf "CNF without extension : %s\n" $CNFNOEXT

cubes=$DIR/$CNFNOEXT.cubes
res1=$(date +%s.%N)
timelimit -t $CPULIM -T 1 $LOOKAHEAD $CNF -o $cubes
res2=$(date +%s.%N)
elapsed=$(echo "$res2 - $res1" | bc) # elapsed time in seconds
elapsed=${elapsed%.*}
printf "elapsed : %02.4f\n" $elapsed
rem=$((CPULIM-elapsed))
printf "remaining time after cube phase : %02.4f\n" $rem
if ([ $rem -le 0 ]) then
    exit 1
fi

formula=$DIR/$CNFNOEXT.icnf
echo "p inccnf" > $formula
cat $CNF | grep -v c >> $formula
cat $cubes >> $formula
timelimit -t $rem -T 1 $CDCL $formula -t $rem -q

rm $cubes $formula
