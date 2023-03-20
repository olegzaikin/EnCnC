# Created on: 20 Mar 2023
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Given a CNF and its satisfying assignment, produces a new CNF where this
# assignment is forbiddent via addina the corresponding clause.
#
# Example:
#   python3 ./forbid_solution.py problem.cnf solution.txt
# produces CNF problem_forbiddent_sol.cnf
#==============================================================================


import sys

script_name = 'forbid_solution.py'
version = '0.0.1'

if len(sys.argv) < 3:
	print('Usage: cnf solution')
	exit(1)

cnfname = sys.argv[1]
solname = sys.argv[2]

# Read CNF:
var_num = 0
clause_num = 0
main_clauses = []
with open(cnfname, 'r') as f:
	lines = f.read().splitlines()
	for line in lines:
		if line == '' or line[0] == 'c':
			continue
		elif line[0] == 'p':
			print(line)
			words = line.split()
			assert(len(words) == 4)
			var_num = int(words[2])
			clause_num = int(words[3])
		else:
			main_clauses.append(line)

# Read solution:
sat_assignment = []
with open(solname, 'r') as f:
	lines = f.read().splitlines()
	for line in lines:
		if line == '' or line[0] == 's':
			continue
		elif line[:2] == 'v ':
			s = line[2:]
			assert(len(s) > 0)
			lst = s.split(' ')
			for x in lst:
				if x != '0':
					sat_assignment.append(int(x))

assert(len(sat_assignment) <= var_num)
assert(len(main_clauses) == clause_num)
print('var_num           : ' + str(var_num))
print('clause_num        : ' + str(clause_num))
print('main_clauses size : ' + str(len(main_clauses)))
print('solution size     : ' + str(len(sat_assignment)))

fault_sat_assignment = [-x for x in sat_assignment]
print('First 3 literals from the fault assignment :')
for x in fault_sat_assignment[:3]:
  print(x)
#print(fault_sat_assignment)

mod_cnfname = cnfname.split('.cnf')[0] + '_forbidden_solution.cnf'
print('Mod CNF name : ' + mod_cnfname)

with open(mod_cnfname, 'w') as ofile:
  ofile.write('p cnf ' + str(var_num) + ' ' + str(clause_num + 1) + '\n')
  for c in main_clauses:
    ofile.write(c + '\n')
  fault_assignment_clause = ''
  for l in fault_sat_assignment:
    fault_assignment_clause += str(l) + ' '
  fault_assignment_clause += '0'
  ofile.write(fault_assignment_clause + '\n')
