# Created on: 10 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Sorts a given satisfying assignment by variable number, extracts the first
# 512 bits (preimage), converts to hex, and constructs a CNF with known 512
# variables.
#
# Example of an unsorted input file's input:
# s SATISFIABLE
# v -2027
# v 6456
#. ..
# v 875
# v 0
#
#==============================================================================

import sys
import binascii

script_name = 'sort_solution.py'
version = '0.0.4'

KNOWN_VARS_NUM = 512 

if len(sys.argv) < 2:
	print('Usage: solution [cnf] [input_vars]')
	exit(1)

solname = sys.argv[1]
print('solname : ' + solname)

cnfname = ''
if len(sys.argv) > 2:
		cnfname = sys.argv[2]
		print('cnfname : ' + cnfname)
if len(sys.argv) > 3:
    inputvarsname = sys.argv[3]
    print('inputvarsname : ' + inputvarsname)
    with open(inputvarsname, 'r') as ifile:
        line = ifile.read()
        input_vars = [int(x) for x in line.split(' ')]
else:
    input_vars = [i+1 for i in range(KNOWN_VARS_NUM)]

literals = []
with open(solname, 'r') as f:
	lines = f.read().splitlines()
	for line in lines:
		if line == '' or line[0] == 's':
			continue
		if line[:2] == 'v ':
			s = line[2:]
			assert(len(s) > 0)
			lst = s.split(' ')
			for x in lst:
				if x != '0':
					literals.append(int(x))

literals = sorted(literals, key=abs)
#print(literals)
#for i in range(KNOWN_VARS_NUM):
#	print('%d 0' % literals[i])

s = ''

for lit in literals:
	s += str(lit) + ' '

# Collect 16 input words in binary form:
input_bits = ['']
k = 0	
#for lit in literals:
for var in input_vars:
	if len(input_bits[k]) == 32:
	    k += 1
	    if k == 16:
		    break
	    input_bits.append('')
	input_bits[k] += '0' if literals[var-1] < 0 else '1'

print(s)
print('\n')
k = 0
total_hex_str = ''
for x in input_bits:
    s = x[::-1]
    hex_str = str(hex(int(s, 2)))
    print('X[' + str(k) + '] = ' + hex_str + ';')
    total_hex_str += hex_str + ' '
    k += 1

print('\n' + total_hex_str)

if cnfname == '':
		exit(1)

vars_num = 0
clauses_num = 0
clauses = []
with open(cnfname, 'r') as f:
	lines = f.read().splitlines()
	for line in lines:
		if line == '' or line[0] == 'c':
			continue
		if line[0] == 'p':
			vars_num = int(line.split(' ')[2])
			clauses_num = int(line.split(' ')[3])
		else:
			clauses.append(line)

with open(cnfname.split('.cnf')[0] + '_known' + str(KNOWN_VARS_NUM) + '.cnf', 'w') as f:
	f.write('p cnf %d %d\n' % (vars_num, clauses_num + KNOWN_VARS_NUM))
	for var in input_vars:
		f.write(str(literals[var-1]) + ' 0\n')
	for c in clauses:
		f.write(c + '\n')
