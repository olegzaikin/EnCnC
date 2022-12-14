# Created on: 26 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Cube-and-Conquer-based generation of constraints for cryptographic hash
# functions.
#==============================================================================

import sys
import multiprocessing as mp
import time
import random
import os
import logging
from enum import Enum
import find_cnc_threshold as FindCncTr

version = '0.1.0'
script_name = 'autom_constr_gen_crypt_hash.py'

MARCH = 'march_cu'
CDCL_SOLVER = 'kissat_3.0.0'
SIMPLIFIER = 'cadical_1.5'
CDCL_MIN_CONFL_LIMIT = 10000

class CubeType(Enum):
    first = 1
    random = 2
    last = 3

# Input options:
class Options:
  cubetype = CubeType.first # first, random or last cube
  nstep = 50                # decrease step for the cutoff threshold
  maxconfl = 100000000      # Maximal number of conflicts by CDCL solver
  seed = 0                  # random seed
  verb = 0                  # verbosity
  #def __init__(self):
  #  self.seed = round(time.time() * 1000)
  def __str__(self):
    return 'cube type : ' + str(self.cubetype.name) + '\n' +\
    'nstep : ' + str(self.nstep) + '\n' +\
    'maxconflicts : ' + str(self.maxconfl) + '\n' +\
    'seed : ' + str(self.seed) + '\n'
  def read(self, argv) :
    for p in argv:
      if '-cubetype=' in p:
        s = p.split('-cubetype=')[1]
        if s == 'first':
          self.cubetype = CubeType.first
        elif s == 'random':
          self.cubetype = CubeType.random
        elif s == 'last':
          self.cubetype = CubeType.last
        else:
          print('Unknown cube type')
          exit(1)
      if '-nstep=' in p:
        self.nstep = int(p.split('-nstep=')[1])
      if '-maxconfl=' in p:
        self.maxconfl = int(p.split('-maxconfl=')[1])
      if '-seed=' in p:
        self.seed = int(p.split('-seed=')[1])
      if '-verb=' in p:
        self.verb = int(p.split('-verb=')[1])

def print_usage():
	print('Usage : ' + script_name + ' CNF [options]')
	print('options :\n' +\
	'-cubetype=<str> - (default : first)       which cube to choose : first, random, or last' + '\n' +\
	'-nstep=<int>    - (default : 50)          step for decreasing threshold n for lookahead solver' + '\n' +\
  '-maxconfl=<int> - (default : 100 million) limit on number of conflicts for CDCL solver' + '\n' +\
  '-seed=<int>     - (default : time)        seed for pseudorandom generator' + '\n' +\
  '-verb=<int>     - (default : 1)           verbose level')

# Read cubes from file:
def read_cubes(cubes_name : str):
  cubes = []
  with open(cubes_name) as cubes_file:
    lines = cubes_file.read().splitlines()
    for line in lines:
      cube = []
      for x in line.split(' '):
        if x == 'a' or x == '0':
          continue
        cube.append(x)
      if len(cube) > 0:
        cubes.append(cube)
  return cubes

# Read free vars counted by march (they are different from the number of all variables):
def get_march_free_vars_num(cnf_name : str):
  sys_str = MARCH + ' ' + cnf_name + ' -d 1'
  o = os.popen(sys_str).read()
  lines = o.split('\n')
  for line in lines:
    if 'c number of free variables = ' in line:
      return int(line.split('c number of free variables = ')[1])
  return -1

# Generate cubes by lookahead, choose one cube and add it to a given CNF.
# cnf_name - CNF on which march is run;
# orig_cnf_name - is needed only for forming a new CNF name;
# iter_cnf_name - CNF to which a chosen cube is added.
def find_cube_add_to_cnf(op : Options, cnf_name : str, orig_cnf_name : str, itr : int, verb : int):
    if verb:
        print('cnf name : ' + cnf_name)
    free_vars_num = get_march_free_vars_num(cnf_name)
    assert(free_vars_num > 0)
    if verb:
        print('free_vars_num : ' + str(free_vars_num))
    cutoff_threshold = free_vars_num - op.nstep
    cubetype_full_name = op.cubetype.name
    if (op.cubetype.name == 'random'):
      cubetype_full_name += '-seed=' + str(op.seed)
    tmp_cubes_file_name ='tmp_cubes_' + \
    cnf_name.replace('./','').replace('.cnf','') + '_' + cubetype_full_name
    march_sys_str = MARCH + ' ' + cnf_name + ' -n ' +\
        str(cutoff_threshold) + ' -o ' + tmp_cubes_file_name 
    if verb:
        print(march_sys_str)
    o = os.popen(march_sys_str).read()
    cubes = read_cubes(tmp_cubes_file_name)
    remove_file(tmp_cubes_file_name)
    cubes_num = len(cubes)
    if verb:
        print(str(cubes_num) + ' cubes')
    if cubes_num == 0:
        return cubes_num, ''
    cube = []
    if op.cubetype.name == 'first':
        cube = cubes[0]
    elif op.cubetype.name == 'random':
        i = random.randint(0, len(cubes)-1)
        cube = cubes[i]
    elif op.cubetype.name == 'last':
        cube = cubes[-1]
    if verb:
        print('chosen cube : ')
        print(cube)
    iter_cnf_name = orig_cnf_name.split('.cnf')[0] + '_' + cubetype_full_name +\
    '_iter' + str(itr) + '.cnf'
    FindCncTr.add_cube(cnf_name, iter_cnf_name, cube)
    return cubes_num, iter_cnf_name, cube, cutoff_threshold

# Remove file:
def remove_file(file_name):
	sys_str = 'rm -f ' + file_name
	o = os.popen(sys_str).read()

def parse_cdcl_result(o):
	res = 'UNKNOWN'
	lines = o.split('\n')
	for line in lines:
		if len(line) < 12:
			continue
		if 's SATISFIABLE' in line:
			res = 'SAT'
			break
		elif 's UNSATISFIABLE' in line:
			res = 'UNSAT'
			break
	return res

# Simplify a given CNF by preprocessing and update the CNF:
def simplify(cnf_name : str, simpl_cnf_name : str):
  sys_str = SIMPLIFIER + ' -f -P100 -d 0 ' + cnf_name + ' -o ' + simpl_cnf_name
  log = os.popen(sys_str).read()

def cdcl_call(cnf_name : str, maxconfl : int):
    sys_str = CDCL_SOLVER + ' ' + cnf_name + ' ' + '--conflicts=' + str(maxconfl)
    t = time.time()
    log = os.popen(sys_str).read()
    t = float(time.time() - t)
    res = parse_cdcl_result(log)
    return res, t

# Main function:
if __name__ == '__main__':
    if len(sys.argv) < 2:
        print_usage()
        exit(1)
    cnf_name = sys.argv[1]

    op = Options()
    op.read(sys.argv[2:])
    print(op)

    random.seed(op.seed)

    log_name = './log_' + cnf_name.replace('./','').replace('.cnf','') + '_' + \
    op.cubetype.name + '_seed=' + str(op.seed)
    print('log_name : ' + log_name)
    logging.basicConfig(filename=log_name, filemode = 'w', level=logging.INFO)

    logging.info('CNF : ' + cnf_name)
    logging.info(str(op))

    itr = 0
    cur_cnf_name = cnf_name
    orig_cnf_name = cnf_name
    cubetype_full_name = op.cubetype.name
    if (op.cubetype.name == 'random'):
      cubetype_full_name += '-seed=' + str(op.seed)
    cur_cnf_name = cnf_name.split('.cnf')[0] + '_' + cubetype_full_name +\
    '_iter' + str(itr) + '.cnf'
    simplify(cnf_name, cur_cnf_name)
    total_cube = []
    iteration_cnfs = []

    while True:
        itr += 1
        if op.verb:
            print('\n')
        s = 'iteration : ' + str(itr) + ', '
        res = find_cube_add_to_cnf(op, cur_cnf_name, orig_cnf_name, itr, op.verb)
        cubes_num = res[0]
        new_cnf_name = res[1]
        simplify(new_cnf_name, new_cnf_name)
        s += str(cubes_num) + ' cubes, '
        if op.verb:
            print('total cube size : ' + str(len(total_cube)))
        r = cdcl_call(new_cnf_name, CDCL_MIN_CONFL_LIMIT)
        if r[0] in ['SAT', 'UNSAT']:
            print('Solved ' + new_cnf_name + ' ' + r[0] + ' ' + str(r[1]) + ' seconds')
            logging.info('Solved ' + new_cnf_name + ' ' + r[0] + ' ' + str(r[1]) + ' seconds')
            break
        else:
           # Save a CNF for further processing:
           iteration_cnfs.append(new_cnf_name)
        #if cur_cnf_name != orig_cnf_name:
        #    remove_file(cur_cnf_name)
        if cubes_num == 0 or cubes_num == 1:
            print('0 or 1 cubes. break.')
            logging.info('0 or 1 cubes. break.')
            break
        else:
            total_cube.extend(res[2])
            cur_cnf_name = new_cnf_name
        s += 'n : ' + str(res[3])
        print(s)
        logging.info(s)

    print('total cube size : ' + str(len(total_cube)))
    logging.info('total cube size : ' + str(len(total_cube)))
    print('total cube :')
    logging.info('Total cube :')
    print(total_cube)
    logging.info(total_cube)
    logging.info('')

    iteration_cnfs.reverse()
    #print('Iteration CNFS:')
    #print(iteration_cnfs)
    #print('')
    #logging.info('Iteration CNFS:')
    #logging.info(iteration_cnfs)
    #logging.info('')

    # Solve CNFs by a CDCL solver:
    for cnf_name in iteration_cnfs:
      #print('Solving ' + cnf_name)
      s = cnf_name
      res = cdcl_call(cnf_name, op.maxconfl)
      cdcl_res = res[0]
      cdcl_time = res[1]
      isBreak = False
      if cdcl_res == 'UNSAT':
        remove_file(cnf_name)
      else:
        isBreak = True
      s += ' ' + cdcl_res + ' ' + str(cdcl_time) + ' seconds'
      print(s)
      logging.info(s)
      if isBreak:
        break
