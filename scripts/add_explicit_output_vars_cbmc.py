# Created on: 29 July 2024
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Problem: In a CNF produced by CBMC, a variable (or array) from a C or C++
# program can be encoded by literals rather than variables, e.g. by -1 2
# instead of 1 2.  
#
# Solution: given a CNF produced by CBMC, parse comments and collect literals
# for a given output array's name (or an output varible's name). Then for each
# literal add a new (output) variable to the CNF and two clauses which encode 
# that the variable is equal to the literal. As a result, the output arrays
# (or an output variable) are now encoded by last several variables in a CNF.
#
# Example:
#   python3 ./add_output_vars_cbmc.py ./1.cnf output1
# produces CNF 1_explicit_output.cnf
#==============================================================================

import sys

script_name = "add_explicit_output_vars_cbmc.py"
version = "0.0.3"

if len(sys.argv) == 2 and sys.argv[1] == '-v':
    print('Script ' + script_name + ' of version : ' + version)
    exit(1)

if len(sys.argv) < 3 or (len(sys.argv) == 2 and sys.argv[1] == '-h'):
    print('Usage: ' + script_name + ' cnf-name output-array-name')
    print('  cnf-name          : name of a CNF produced by CBMC')
    print('  output-name       : output array (or output variable) name from the C- or C++-file.')
    print('Script produces a CNF where explicit output variables are added.')
    exit(1)

cnfname = sys.argv[1]
output_program_name = sys.argv[2]
print('cnfname    : ' + cnfname)
print('output program name : ' + output_program_name)

varnum = -1
clanum = -1
output_vars_litarals = dict()
clauses = []
# Example of output variable y: c main::1::y!0@1#2 -1 10 12 14 16 18 20 22

print('Trying to find output array ' + output_program_name)
prefix_array = output_program_name + '!0@1#2[['
prefix_variable = output_program_name + '!0@1#1'

with open(cnfname, 'r') as f:
    lines = f.read().splitlines()
    for line in lines:
        if 'p cnf ' in line:
            words = line.split()
            assert(len(words) == 4)
            varnum = int(words[2])
            clanum = int(words[3])
        elif prefix_array in line:
            print('Output program array detected :')
            print(line)
            id = int(line.split(prefix_array)[1].split(']')[0])
            words = line.split(' ')[2:]
            output_vars_litarals[id] = [int(w) for w in words]
        elif prefix_variable in line:
            print('Output program variable detected :')
            print(line)
            words = line.split('0@1#1')[1].split()
            output_vars_litarals[0] = [int(w) for w in words]
        elif 'c ' in line:
            continue
        else:
            clauses.append(line)

assert(varnum > 0 and clanum > 0)
print(str(varnum) + ' vars and ' + str(clanum) + ' clauses.')
assert(len(clauses) == clanum)

literals = []
for id in output_vars_litarals:
    s = str(id) + ' : '
    for lit in output_vars_litarals[id]:
        literals.append(lit)
        s += str(lit) + ' '
    print(s)

literals = sorted(literals, key=abs)
print('Output literals after sorting:')
print(literals)

new_vars_num = len(output_vars_litarals)*len(output_vars_litarals[0])
print(str(new_vars_num) + ' new output variables :')

new_vars = [var for var in range(varnum + 1, varnum + 1 + new_vars_num)]
print(new_vars)

new_clauses = []
for i in range(len(literals)):
    # Two variables are equal: 
    assert(literals[i] != 0)
    if literals[i] > 0:
      new_clauses.append(str(new_vars[i]) + ' -' + str(literals[i]) + ' 0')
      new_clauses.append('-' + str(new_vars[i]) + ' ' + str(literals[i]) + ' 0')
    # Two variables are inequal:
    else:
      new_clauses.append(str(new_vars[i]) + ' ' + str(abs(literals[i])) + ' 0')
      new_clauses.append('-' + str(new_vars[i]) + ' -' + str(abs(literals[i])) + ' 0')

print('The first 10 new clauses:')
for i in range(10):
    print(new_clauses[i])

new_cnfname = cnfname.split('.cnf')[0] + '_explicit_output.cnf'
new_varnum = varnum + new_vars_num
new_clanum = len(clauses) + len(new_clauses)
with open(new_cnfname, 'w') as f:
    f.write('p cnf ' + str(new_varnum) + ' ' + str(new_clanum) + '\n')
    for c in clauses:
        f.write(c + '\n')
    for c in new_clauses:
        f.write(c + '\n')
