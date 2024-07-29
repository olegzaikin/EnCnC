# Created on: 24 January 2024
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Given a file of hashes and a CNF that encodes a cryptographic hash function,
# for each hash from the file generate a CNF that encodes the preimage finding
# problem by adding the corresponding unit clauses to the main CNF. 
#
# Example:
#   python3 ./gen_hash_preimage_instances.py ./template.cnf ./hashes 128
# for each hash from the file hashes, a CNF will be generated.
#==============================================================================

import sys

script_name = "gen_hash_preimage_instances.py"
version = "0.1.0"

if len(sys.argv) == 2 and sys.argv[1] == '-v':
    print('Script ' + script_name + ' of version : ' + version)
    exit(1)

if len(sys.argv) < 5 or (len(sys.argv) == 2 and sys.argv[1] == '-h'):
    print('Usage: ' + script_name + ' cnf-name hash-file hash-length inst-num [--hashvars=fname] [--random]')
    print('  --hashvars : file name with hash variables in the format from-to')
    print('    optional since e.g. in Transalg the output variables are the last ones.')
    print('  --random : 0hash and 1hash are marked, the remaining are randhashes')
    print('  NB. CNFs made by CBMC must be modifed by add_explicit_output_vars_cbmc.py beforehand.')
    exit(1)

cnf_name = sys.argv[1]
hash_file = sys.argv[2]
hash_len = int(sys.argv[3])
instances_num = int(sys.argv[4])
print('cnf_name : ' + cnf_name)
print('hash_file : ' + hash_file)
print('hash_len : ' + str(hash_len))
print('instances_num : ' + str(instances_num))
is_random_hashes = False
hash_vars_file_name = ''
for i in range(5, len(sys.argv)):
    if sys.argv[i] == '--random':
        is_random_hashes = True
    elif '--hashvars=' in sys.argv[i]:
        hash_vars_file_name = sys.argv[i].split('--hashvars=')[1]
        print('hash_vars_file_name : ' + hash_vars_file_name)

hashes = []
with open(hash_file, 'r') as f:
      lines = f.read().splitlines()
      for line in lines:
            if len(line) <= 1:
                  continue
            assert(len(line) >= hash_len)
            hash = line[:hash_len]
            assert(hash not in hashes)
            hashes.append(hash)

print(str(len(hashes)) + ' hashes were read :')
for h in hashes:
  print(h)

assert(instances_num <= len(hashes))

vars_num = 0
clauses_num = 0

main_clauses = []
with open(cnf_name, 'r') as cnf_file:
		lines = cnf_file.read().splitlines()
		for line in lines:
			if len(line) < 2 or line[0] == 'c':
				  continue
			elif line[0] == 'p':
				  words = line.split()
				  assert(len(words) == 4)
				  vars_num = int(words[2])
				  clauses_num = int(words[3])
			else:
				  main_clauses.append(line)

assert(clauses_num == len(main_clauses))
print('vars_num : ' + str(vars_num))
print('clauses_num : ' + str(clauses_num))
print('main_clauses size : ' + str(len(main_clauses)))

cnf_name_without_ext = cnf_name.split('.cnf')[0]

hash_vars = []
# If Transalg or CBMC (with added explicit output variables):
if hash_vars_file_name == '':
      hash_vars = [i for i in range(vars_num - hash_len + 1, vars_num+1)]
# If hash variables are given in a file:
else:
  with open(hash_vars_file_name, 'r') as hash_vars_file:
    lines = hash_vars_file.read().splitlines()
    line = lines[0]
    assert('-' in line)
    first_var = int(line.split('-')[0])
    last_var = int(line.split('-')[1])
    hash_vars = [i for i in range(first_var, last_var+1)]

assert(len(hash_vars) > 0)

print('hash_vars :')
print(hash_vars)

hash_index = 0
assert(instances_num > 0)
for i in range(instances_num):
    assert(hash_index >= 0)
    k = 0
    literals = []
    #for var in range(vars_num - hash_len + 1, vars_num+1):
    for var in hash_vars:
        lit = ''
        if var >= 0:
            lit = '-' if hashes[i][k] == '0' else ''
        else: # CBMC for some reason sometimes produces negative variables
            lit = '-' if hashes[i][k] == '1' else ''
        lit += str(abs(var))
        literals.append(lit)
        k += 1
        if k >= len(hashes[i]):
            break
    assert(len(literals) == hash_len)
    if is_random_hashes:
        if hash_index == 0:
             tmp = '0hash'
        elif hash_index == 1:
             tmp = '1hash'
        else:
             tmp = 'randhash' + str(i-2)
        cnf_name = cnf_name_without_ext + '_hashlen' + str(hash_len) + '_' + tmp + '.cnf'
    else:
        cnf_name = cnf_name_without_ext + '_hashlen' + str(hash_len) + '_inst' + str(hash_index) + '.cnf'
    with open(cnf_name, 'w') as ofile:
        ofile.write('p cnf ' + str(vars_num) + ' ' + str(clauses_num + len(literals)) + '\n')
        for clause in main_clauses:
            ofile.write(clause + '\n')
        for lit in literals:
            ofile.write(lit + ' 0\n')
    hash_index += 1

print(str(instances_num) + ' instances were generated')
