# Created on: 4 Dec 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Reports the number of variables, clauses, and literals in a given CNF.
#
#==============================================================================

import sys

script_name = 'cnf_stats.py'
version = '0.0.1'

if len(sys.argv) != 2:
  sys.exit('Usage : ' + script_name + ' CNF')

cnfname = sys.argv[1]

print('Running script ' + script_name + ' of version ' + version)
print('CNF name : ' + cnfname)

vars = set()
clauses_num = 0
literals_num = 0

with open(cnfname, 'r') as cnf:
  lines = cnf.read().splitlines()
  for s in lines:
    #print(line)
    if s[0] == 'c' or s[0] == 'p':
      continue
    clauses_num += 1
    literals = s.split(' ')[:-1] # exclude 0 at the end
    literals_num += len(literals)
    for lit in literals:
      var = abs(int(lit))
      if var not in vars:
        vars.add(var)

print(str(len(vars)) + ' variables')
print(str(clauses_num) + ' clauses')
print(str(literals_num) + ' literals')
