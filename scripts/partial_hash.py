# Created on: 4 Oct 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Generates CNFs that encode weakened preimage attack problems
# for cryptographic hash functions.
#
# Example:
#   partial_hash.py hash.cnf 128 30-32
# here hash.cnf encodes a preimage attack problem, that is the
# last 128 clauses are oneliteral and correspond to a hash value.
# 3 CNFs will be generated where only last 30, 31, 32 oneliteral
# clauses will be left.
#
#==============================================================================

version = '0.0.2'

script_name = 'partial_hash.py'

import sys

if len(sys.argv) < 4:
  print('Usage: ' + script_name + ' CNF hashsize knownbits')
  exit(1)

print('Running script ' + script_name + ' of version ' + str(version))
cnf_name = sys.argv[1]
hashsize = int(sys.argv[2])
known_bits_str = sys.argv[3]
print('cnf name   : ' + cnf_name)
print('hash size  : ' + str(hashsize))
print('known bits : ')
if '-' in known_bits_str:
  first = int(known_bits_str.split('-')[0])
  last = int(known_bits_str.split('-')[1])
  known_bits = [i for i in range(first,last+1)]
else:
  known_bits = [int(known_bits_str)]
print(known_bits)
print('Generating ' + str(len(known_bits)) + ' CNFs')

all_clauses = []
main_clauses = []
hash_clauses = []
varnum = 0
with open(cnf_name) as ifile:
  lines = ifile.read().splitlines()
  for line in lines:
    if line[0] == 'c' or line[0] == 'p':
      continue
    literals = line.split(' ')[:-1] # exclude 0 at the end
    for lit in literals:
      varnum = varnum if varnum >= abs(int(lit)) else abs(int(lit))
    all_clauses.append(line)
print(str(len(all_clauses)) + ' clauses were read')
main_clauses = all_clauses[0:-hashsize]
hash_clauses = all_clauses[-hashsize:]
print(str(len(hash_clauses)) + ' oneliteral hash-clauses : ')
for cla in hash_clauses:
  print(cla)

for k in known_bits:
  new_cnf_name = cnf_name.split('.cnf')[0] + '_' + str(k) + 'bithash.cnf'
  print(new_cnf_name)
  clanum = len(main_clauses) + k
  with open(new_cnf_name, 'w+') as ofile:
    ofile.write('p cnf ' + str(varnum) + ' ' + str(clanum) + '\n')
    for s in main_clauses:
      ofile.write(s + '\n')
    for s in hash_clauses[:k]:
      assert(len(s.split()) == 2 and s.split()[-1] == '0')
      ofile.write(s + '\n')
