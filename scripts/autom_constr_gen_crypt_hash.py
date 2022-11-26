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
from enum import Enum
import find_cnc_threshold as FindCncTr

version = '0.0.1'
script_name = 'autom_constr_gen_crypt_hash.py'

MARCH_NAME = 'march_cu'
CADICAL_NAME = 'cadical_1.5'

class CubeType(Enum):
    first = 1
    random = 2
    last = 3

# Input options:
class Options:
  leaf = CubeType.first # first, random or last leaf
  nstep = 100 # decrease step for the cutoff threshold
  cpunum = 1 # CPU cores
  seed = 0
  def __init__(self):
    self.seed = round(time.time() * 1000)
  def __str__(self):
    return 'leaf : ' + str(self.leaf.name) + '\n' +\
    'nstep : ' + str(self.nstep) + '\n' +\
    'cpunum : ' + str(self.cpunum) + '\n' +\
    'seed : ' + str(self.seed) + '\n'
  def read(self, argv) :
    for p in argv:
      if '-leaf=' in p:
        s = p.split('-leaf=')[1]
        if s == 'first':
          self.leaf = CubeType.first
        elif s == 'random':
          self.leaf = CubeType.random
        elif s == 'last':
          self.leaf = CubeType.last
        else:
          print('Unknown leaf type')
          exit(1)
      if '-nstep=' in p:
        self.nstep = int(p.split('-nstep=')[1])
      if '-cpunum=' in p:
        self.cpunum = p.split('-cpunum=')[1]
      if '-seed=' in p:
        self.seed = int(p.split('-seed=')[1])

def print_usage():
	print('Usage : ' + script_name + ' CNF [options]')
	print('options :\n' +\
	'-leaf=<str>   - (default : first) which leaf to choose : first, random, or last' + '\n' +\
	'-nstep=<int>  - (default : 100)   step for decreasing threshold n for lookahead solver' + '\n' +\
  '-cpunum=<int> - (default : 1)     CPU cores' + '\n' +\
  '-seed=<int>   - (default : time)  seed for pseudorandom generator' + '\n')

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
  sys_str = MARCH_NAME + ' ' + cnf_name + ' -d 1'
  o = os.popen(sys_str).read()
  lines = o.split('\n')
  for line in lines:
    if 'c number of free variables = ' in line:
      return int(line.split('c number of free variables = ')[1])
  return -1

def find_cube_add_to_cnf(cnf_name : str, itr : int):
    global op
    print('cnf name : ' + cnf_name)
    up_cnf_name = 'tmp_cnf_UP.cnf'
    up_sys_str = CADICAL_NAME + ' -d 0 -f ' + cnf_name + ' -o ' + up_cnf_name
    #print(up_sys_str)
    o = os.popen(up_sys_str).read()
    cubes_name = 'tmp_cubes'
    print('cnf after UP ; ' + up_cnf_name)
    free_vars_num = get_march_free_vars_num(up_cnf_name)
    assert(free_vars_num > 0)
    print('free_vars_num : ' + str(free_vars_num))
    cutoff_threshold = free_vars_num - op.nstep
    print('cutoff_threshold : ' + str(cutoff_threshold))
    march_sys_str = MARCH_NAME + ' ' + up_cnf_name + ' -n ' +\
        str(cutoff_threshold) + ' -o ' + cubes_name
    print(march_sys_str)
    o = os.popen(march_sys_str).read()
    cubes = read_cubes(cubes_name)
    cubes_num = len(cubes)
    print(str(cubes_num) + ' cubes')
    if cubes_num == 0:
        return cubes_num, ''
    cube = []
    if op.leaf.name == 'first':
        cube = cubes[0]
    elif op.leaf.name == 'random':
        i = random.randint(0, len(cubes)-1)
        cube = cubes[i]
    elif op.leaf.name == 'last':
        cube = cubes[-1]
    print('chosen cube : ')
    print(cube)
    cube_cnf_name = 'tmp_cube' + str(itr) + '.cnf'
    FindCncTr.add_cube(up_cnf_name, cube_cnf_name, cube)
    return cubes_num, cube_cnf_name

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

    isLeafReached = False 
    itr = 0
    old_cnf_name = cnf_name
    while not isLeafReached:
        print('\niteration : ' + str(itr))
        res = find_cube_add_to_cnf(old_cnf_name, itr)
        cubes_num = res[0]
        new_cnf_name = res[1]
        if cubes_num == 0:
            #op.nstep += 50
            #print('nstep increased to : ' + str(op.nstep))
            print('0 cubes. break.')
            break
        else:
            old_cnf_name = new_cnf_name
        itr += 1
