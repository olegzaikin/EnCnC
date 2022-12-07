# Created on: 7 Dec 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Extracts input variables' from CNF constructed by CBMC
#
#==============================================================================

import sys
import binascii

script_name = 'extract_input_vars.py'
version = '0.0.1' 

if len(sys.argv) != 2:
	print('Usage: ' + script_name + ' CNF')
	print('  CNF - file constructed by CBMC')
	exit(1)

cnfname = sys.argv[1]
print('CNF name : ' + cnfname)

input_vars = []
with open(cnfname, 'r') as f:
	lines = f.read().splitlines()
	for line in lines:
		if 'input1' in line and '[[' in line:
			print(line)
			words = line.split(' ')
			assert(len(words) == 34)
			assert(words[0] == 'c')
			assert('[[' in words[1])
			print(words[2:])
			for var in words[2:]:
				input_vars.append(int(var))

input_vars = sorted(input_vars)
#print('input vars:')
#for var in input_vars:
#	print(str(var) + ', ', end = '')


cnfname = cnfname.replace('./', '')
with open('input_vars_' + cnfname.split('.cnf')[0], 'w') as ofile:
    for var in input_vars[:-1]:
        ofile.write(str(var) + ' ')
    ofile.write(str(input_vars[-1]) + '\n')
