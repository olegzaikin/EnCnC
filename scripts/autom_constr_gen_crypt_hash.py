# Created on: 26 Nov 2022
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Cube-and-Conquer-based generation of constraints for cryptographic hash
# functions.
#==============================================================================

import sys
import time
import random
import os
import logging
from enum import Enum
import os.path

version = '0.3.0'
script_name = 'autom_constr_gen_crypt_hash.py'

LOOKAHEAD_SOLVER = 'march_cu'
LOOHAHEAD_TIMELIM = 60
CDCL_SOLVER = 'kissat4.0.1'

class CubeType(Enum):
    first = 1
    random = 2
    last = 3

# Input options:
class Options:
  cubetype = CubeType.first # first, random, or last cube
  nstep = 50                # decrease step for the cutoff threshold
  cdcl_maxtime = 5000       # CDCL solver's time limit 
  min_cubes = 1000          # Minimal cubes for each iteration
  seed = 0                  # random seed
  verb = 0                  # verbosity
  def __str__(self):
    return 'cube type : ' + str(self.cubetype.name) + '\n' +\
    'nstep : ' + str(self.nstep) + '\n' +\
    'cdcl_maxtime : ' + str(self.cdcl_maxtime) + '\n' +\
    'min_cubes : ' + str(self.min_cubes) + '\n' +\
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
      if '-cdclmaxtime=' in p:
        self.cdcl_maxtime = int(p.split('-cdclmaxtime=')[1])
      if '-mincubes=' in p:
        self.min_cubes = int(p.split('-mincubes=')[1])
      if '-seed=' in p:
        self.seed = int(p.split('-seed=')[1])
      if '-verb=' in p:
        self.verb = int(p.split('-verb=')[1])

def print_usage():
	print('Usage : ' + script_name + ' CNF [options]')
	print('options :\n' +\
	'-cubetype=<str>       - (default : first)        which cube to choose : first, random, or last' + '\n' +\
	'-nstep=<int>          - (default : 50)           step for decreasing threshold n for lookahead solver' + '\n' +\
	'-cdclmaxtime=<int>    - (default : 5000)         CDCL solver time limit in seconds on CNFs' + '\n' +\
	'-mincubes=<int>       - (default : 1000)         Minimal cubes for each iteration' + '\n' +\
	'-seed=<int>           - (default : time)         seed for pseudorandom generator' + '\n' +\
	'-verb=<int>           - (default : 1)            verbose level; quiet if 0')

# Read cubes from file:
def read_cubes(cubes_name : str):
  if not os.path.isfile(cubes_name):
    return []
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
  sys_str = LOOKAHEAD_SOLVER + ' ' + cnf_name + ' -d 1'
  o = os.popen(sys_str).read()
  lines = o.split('\n')
  vars = -1
  for line in lines:
    if 'c number of free variables = ' in line:
      vars = int(line.split('c number of free variables = ')[1])
  assert(vars > 0)
  return vars

# Add cube to a CNF as one-literal clauses:
def add_cube(old_cnf_name : str, new_cnf_name : str, cube : list):
	cnf_var_number = 0
	clauses = []
	with open(old_cnf_name, 'r') as cnf_file:
		lines = cnf_file.readlines()
		for line in lines:
			if len(line) < 2 or line[0] == 'c':
				continue
			if line[0] == 'p':
				cnf_var_number = line.split(' ')[2]
			else:
				clauses.append(line)
	clauses_number = len(clauses) + len(cube)
	#print('clauses_number : %d' % clauses_number)
	with open(new_cnf_name, 'w') as cnf_file:
		cnf_file.write('p cnf ' + str(cnf_var_number) + ' ' + str(clauses_number) + '\n')
		for cl in clauses:
			cnf_file.write(cl)
		for c in cube:
			cnf_file.write(c + ' 0\n')

# Choose a maximal cutoff threshold that gives a desired number of cubes:
def choose_cutoff_lookahead(op : Options, cnf_name : str):
    free_vars_num = get_march_free_vars_num(cnf_name)
    # Form a temporary CNF name - different for each cube type and seed:
    cubetype_full_name = op.cubetype.name
    if (op.cubetype.name == 'random'):
      cubetype_full_name += '-seed=' + str(op.seed)
    tmp_cubes_file_name ='tmp_cubes_' + cubetype_full_name
    n = free_vars_num - op.nstep
    k = 1
    n_final = 0
    cubes_num_final = 0
    n_prev = 0
    cubes_num_prev = 0
    is_first = True
    while True:
      # Delete file with cubes
      remove_file(tmp_cubes_file_name)
      assert(n > 0 and n < free_vars_num)
      # Do not limit the first call to get at least one cutoff:
      if is_first:
        march_sys_str = LOOKAHEAD_SOLVER + ' ' + cnf_name + ' -n ' + str(n) +\
        ' -o ' + tmp_cubes_file_name 
        is_first = False
      else:
        march_sys_str = 'timeout ' + str(LOOHAHEAD_TIMELIM) + ' ' +\
        LOOKAHEAD_SOLVER + ' ' + cnf_name + ' -n ' + str(n) +\
        ' -o ' + tmp_cubes_file_name 
      # Run cubing:
      os.popen(march_sys_str).read()
      # Get cubes:
      cubes = read_cubes(tmp_cubes_file_name)
      cubes_num = len(cubes)
      s = ' choosing cutoff, ' + str(free_vars_num) + ' vars, n=' + str(n) + ', ' + str(cubes_num) + ' cubes'
      if cubes_num == 0:
          s += ', interrupted'
      print(s)
      logging.info(s)
      if cubes_num > op.min_cubes:
          n_final = n
          cubes_num_final = cubes_num
          break
      elif cubes_num == 0:
          n_final = n_prev
          cubes_num_final = cubes_num_prev
          break
      else:
          n_prev = n
          cubes_num_prev = cubes_num
          if cubes_num <= 2:
            k += 1
            n = n - op.nstep*k
          else:
            n = n - op.nstep
    assert(n_final > 0)
    s = ' final cutoff, n=' + str(n_final)
    print(s)
    logging.info(s)
    return n_final, cubes_num_final

# Generate cubes by lookahead, choose one cube and add it to a given CNF.
# cnf_name - CNF on which march is run;
# orig_cnf_name - is needed only for forming a new CNF name;
# iter_cnf_name - CNF to which a chosen cube is added.
def find_cube_add_to_cnf(n : int, op : Options, cnf_name : str, \
                         orig_cnf_name : str, itr : int, restart_num : int, \
                         verb : int):
    if verb:
        print('cnf name : ' + cnf_name)
    free_vars_num = get_march_free_vars_num(cnf_name)
    assert(free_vars_num > 0)
    if verb:
        print('free_vars_num : ' + str(free_vars_num))
    # Form a new CNF name:
    cubetype_full_name = op.cubetype.name
    if (op.cubetype.name == 'random'):
      cubetype_full_name += '-seed=' + str(op.seed)
    iter_cnf_name = orig_cnf_name.split('.cnf')[0] + '_' + cubetype_full_name +\
    '_restart' + str(restart_num) + '_iter' + str(itr) + '.cnf'
    # Form file name for cubes:
    tmp_cubes_file_name ='tmp_cubes_' + cubetype_full_name
    # Form string for running march:
    march_sys_str = LOOKAHEAD_SOLVER + ' ' + cnf_name + ' -n ' +\
    str(n) + ' -o ' + tmp_cubes_file_name 
    if verb:
        print(march_sys_str)
    # Run cubing:
    os.popen(march_sys_str).read()
    # Get cubes:
    cubes = read_cubes(tmp_cubes_file_name)
    remove_file(tmp_cubes_file_name)
    # Choose a proper cube:
    cubes_num = len(cubes)
    if verb:
        print(str(cubes_num) + ' cubes')
    if cubes_num == 0:
        return cubes_num, ''
    cube = []
    if op.cubetype.name == 'first':
        cube = cubes[0]
    elif op.cubetype.name == 'random':
        j = -1
        assert(len(cubes) >= 2)
        j = random.randint(0, len(cubes)-1)
        assert(j >= 0 and j <= len(cubes)-1)
        cube = cubes[j]
    elif op.cubetype.name == 'last':
        cube = cubes[-1]
    if verb:
        print('chosen cube : ')
        print(cube)
    # Add cube to a new CNF:
    add_cube(cnf_name, iter_cnf_name, cube)
    #
    return cubes_num, iter_cnf_name, cube, n

# Remove file:
def remove_file(file_name):
	sys_str = 'rm -f ' + file_name
	os.popen(sys_str).read()

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

def cdcl_call(cnf_name : str, maxmeasure : int, type : str):
    assert(type == 'time' or type == 'confl')
    if type == 'confl':
      sys_str = CDCL_SOLVER + ' ' + cnf_name + ' ' + '--conflicts=' + str(maxmeasure)
    else:
      sys_str = CDCL_SOLVER + ' ' + cnf_name + ' ' + '--time=' + str(maxmeasure)
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
    orig_cnf_name = sys.argv[1]

    op = Options()
    op.read(sys.argv[2:])
    print(op)

    random.seed(op.seed)

    cubetype_full_name = op.cubetype.name
    if (op.cubetype.name == 'random'):
      cubetype_full_name += '-seed=' + str(op.seed)

    log_name = './log_' + orig_cnf_name.replace('./','').replace('.cnf','') + \
    '_' + cubetype_full_name
    print('log_name : ' + log_name)
    logging.basicConfig(filename=log_name, filemode = 'w', level=logging.INFO)

    logging.info('CNF : ' + orig_cnf_name)
    logging.info(str(op))

    start_time = time.time()
    s = 'Original CNF, ' + str(get_march_free_vars_num(orig_cnf_name)) + ' vars'
    print(s)
    itr = 0
    restart_num = 0
    cur_cnf_name = orig_cnf_name
    total_cube = []

    cubes_num = 0
    while True:
        if op.verb:
            print('\n')
        s = 'restart ' + str(restart_num) + ', iteration ' + str(itr) + ', '
        s += str(get_march_free_vars_num(cur_cnf_name)) + ' vars'
        n, cubes_num = choose_cutoff_lookahead(op, cur_cnf_name)
        assert(cubes_num >= 0)
        if cubes_num == 0 or cubes_num == 1:
            print('<= 0 or 1 cubes. break.')
            logging.info('<= 0 or 1 cubes. break.')
            break
        res = find_cube_add_to_cnf(n, op, cur_cnf_name, orig_cnf_name, itr, restart_num, op.verb)
        assert(res[0] > 0 and len(res[2]) > 0)
        cubes_num = res[0]
        new_cnf_name = res[1]
        cube = res[2]
        assert(n == res[3])
        s += ', n=' + str(res[3]) + ', ' + str(cubes_num) + ' cubes'
        s += '\ncube with ' + str(len(cube)) + ' literals :'
        for x in cube:
          s += ' ' + str(x)
        total_cube.extend(cube)
        s += '\ntotal cube size : ' + str(len(total_cube))
        print(s)
        logging.info(s)
        res = cdcl_call(new_cnf_name, op.cdcl_maxtime, 'time')
        # Break if SAT is found:
        if res[0] == 'SAT':
            is_SAT = True
            s0 = '\n*** SAT ' + new_cnf_name + ' ' + res[0] + ' ' + str(res[1]) + ' seconds'
            print(s0)
            logging.info(s0)
            break
        elif res[0] == 'UNSAT':
            s0 = '\n** UNSAT ' + new_cnf_name + ' ' + res[0] + ' ' + str(res[1]) + ' seconds'
            s0 += '\n** Restart after ' + str(int(time.time() - start_time)) + ' seconds'
            print(s0)
            logging.info(s0)
            itr = 0
            restart_num += 1
            remove_file(new_cnf_name)
            cur_cnf_name = orig_cnf_name
            total_cube = []
        else:
            if cur_cnf_name != orig_cnf_name:
              remove_file(cur_cnf_name)
            cur_cnf_name = new_cnf_name
            itr += 1

    s = 'Total cube size : ' + str(len(total_cube))
    s += '\nTotal cube :'
    for x in total_cube:
      s += ' ' + str(x)
    s += '\n'
    print(s)
    logging.info(s)

    total_time = float(time.time() - start_time)
    s = '\nTotal time : ' + str(total_time)
    print(s)
    logging.info(s)
