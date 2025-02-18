# Created on: 5 Apr 2020
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Does sampling to find a cutoff threshold with minimal runtime estimation
# of the conquer phase of Cube-and-Conquer. The threshold is used on the cubing
# phase to split a given problem.
#
# Example of the estimating mode:
#     python3 ./find_cnc_threshold.py problem.cnf -maxcdclt=5000 --stop_time
#  problem.cnf    : CNF.
#  -maxcdclt=5000 : on each subproblem a CDCL solver is limited by 5000 seconds.
#  --stop_time    : if the CDCL solver is interrupted, stop script.
#
# Example of the SAT-solving mode:
#     python3 ./find_cnc_threshold.py problem.cnf --stop_sat
#  problem.cnf    : CNF.
#  --stop_sat     : if a satisfying assignment is found, stop script.
#==============================================================================
#
# TODO:
# 0. Calculate estimation after processing samples.

import sys
import os
import time
import multiprocessing as mp
import random
import collections
import logging
import time
from enum import Enum

version = "1.5.1"

# Input options:
class Options:
	la_solver = 'march_cu'
	cdcl_solvers = ['kissat3']
	sample_size = 1000
	min_cubes = 10000
	max_cubes = 1000000
	max_cubes_parallel = 10000000
	min_refuted_leaves = 1000
	max_la_time = 86400
	max_cdcl_time = 5000
	max_script_time = 864000
	nstep = 10
	stop_sat = False
	stop_time = False
	param_file = ''
	cpu_num = mp.cpu_count()
	seed = 0
	def __str__(self):
		s = 'la_solver : ' + str(self.la_solver) + '\n' +\
    'cdcl_solvers : '
		for solver in self.cdcl_solvers:
			s += str(solver) + ' '
		s += '\n' +\
		'sample_size : ' + str(self.sample_size) + '\n' +\
		'min_cubes : ' + str(self.min_cubes) + '\n' +\
		'max_cubes : ' + str(self.max_cubes) + '\n' +\
		'max_cubes_parallel : ' + str(self.max_cubes_parallel) + '\n' +\
		'min_refuted_leaves : ' + str(self.min_refuted_leaves) + '\n' +\
		'max_la_time : ' + str(self.max_la_time) + '\n' +\
		'max_cdcl_time : ' + str(self.max_cdcl_time) + '\n' +\
		'max_script_time : ' + str(self.max_script_time) + '\n' +\
		'nstep : ' + str(self.nstep) + '\n' +\
		'stop_sat : ' + str(self.stop_sat) + '\n' +\
		'stop_time : ' + str(self.stop_time) + '\n' +\
		'param_file : ' + str(self.param_file) + '\n' +\
		'cpu_num : ' + str(self.cpu_num) + '\n' +\
		'seed : ' + str(self.seed) + '\n'
		return s
	def read(self, argv) :
		for p in argv:
			if '-lasolver=' in p:
				self.la_solver = p.split('-lasolver=')[1]
			# Parse comma-separated solvers:
			if '-cdclsolvers=' in p:
				if ',' not in p:
				  self.cdcl_solvers = [p.split('-cdclsolvers=')[1]]
				else:
					self.cdcl_solvers = []
					word = p.split('-cdclsolvers=')[1]
					for solver in word.split(','):
					  if solver == '':
					    continue
					  self.cdcl_solvers.append(solver)
			if '-sample=' in p:
				self.sample_size = int(p.split('-sample=')[1])
			if '-minc=' in p:
				self.min_cubes = int(p.split('-minc=')[1])
			if '-maxc=' in p:
				self.max_cubes = int(p.split('-maxc=')[1])
			if '-maxcpar=' in p:
				self.max_cubes_parallel = int(p.split('-maxcpar=')[1])
			if '-minref=' in p:
				self.min_refuted_leaves = int(p.split('-minref=')[1])
			if '-maxlat=' in p:
				self.max_la_time = int(p.split('-maxlat=')[1])
			if '-maxcdclt=' in p:
				self.max_cdcl_time = int(p.split('-maxcdclt=')[1])
			if '-maxt=' in p:
				self.max_script_time = int(p.split('-maxt=')[1])
			if '-nstep=' in p:
				self.nstep = int(p.split('-nstep=')[1])
			if '-param=' in p:
				self.param_file = p.split('-param=')[1]
			if '-cpunum=' in p:
				self.cpu_num = int(p.split('-cpunum=')[1])
			if '-seed=' in p:
				self.seed = int(p.split('-seed=')[1])
			if p == '--stop_sat':
				self.stop_sat = True
			if p == '--stop_time':
				self.stop_time = True

def print_usage():
	print('Usage : script cnf-name [options]')
	print('options :\n' +\
	'-lasolver=<str>     - (default : march_cu) lookahead solver' + '\n' +\
	'-cdclsolvers=<str>  - (default : kissat3)  comma-separated CDCL solvers' + '\n' +\
	'-sample=<int>       - (default : 1000)     random sample size' + '\n' +\
	'-minc=<int>         - (default : 10000)    minimal number of cubes' + '\n' +\
	'-maxc=<int>         - (default : 1000000)  maximal number of cubes' + '\n' +\
	'-maxcpar=<int>      - (default : 1000000)  maximal number of cubes processed in parallel' + '\n' +\
	'-minref=<int>       - (default : 1000)     minimal number of refuted leaves' + '\n' +\
	'-maxlat=<int>       - (default : 86400)    time limit in seconds for lookahead solver' + '\n' +\
	'-maxcdclt=<int>     - (default : 5000)     time limit in seconds for CDCL solver' + '\n' +\
	'-maxt=<int>         - (default : 864000)   script time limit in seconds' + '\n' +\
	'-nstep=<int>        - (default : 10)       step for decreasing threshold n for lookahead solver' + '\n' +\
	'-param=<str>        - (default : '')       file with parameters for CDCL solver' + '\n' +\
	'-cpunum=<int>       - (default : ' + str(mp.cpu_count()) + '        number of used CPU cores' + '\n' +\
	'-seed=<int>         - (default : time)     seed for pseudorandom generator' + '\n' +\
	'--stop_time         - (default : False)    stop if CDCL solver is interrupted' + '\n' +\
	'--stop_sat          - (default : False)    stop if a satisfying assignment is found' + '\n')

# Kill unuseful processes after script termination:
def kill_unuseful_processes(la_solver : str):
	sys_str = 'killall -9 ' + la_solver
	o = os.popen(sys_str).read()
	sys_str = 'killall -9 timelimit'
	o = os.popen(sys_str).read()

# Kill a solver:
def kill_solver(solver : str):
	# Kill only a binary solver, let a script solver finisn and clean:
	if '.sh' not in solver:
	    logging.info("Killing solver " + solver)
	    sys_str = 'killall -9 ' + solver.replace('./','')
	    o = os.popen(sys_str).read()

# Remove file:
def remove_file(file_name):
	sys_str = 'rm -f ' + file_name
	o = os.popen(sys_str).read()

# Read free vars counted by march (they are different from the number of all variables):
def get_march_free_vars_num(la_solver : str, cnf_name : str):
  sys_str = la_solver + ' ' + cnf_name + ' -d 1'
  o = os.popen(sys_str).read()
  lines = o.split('\n')
  for line in lines:
    if 'c number of free variables = ' in line:
      return int(line.split('c number of free variables = ')[1])
  return -1

# Parse lookahead solver's log:
def parse_cubing_log(o):
	cubes = -1
	refuted_leaves = -1
	lines = o.split('\n')
	for line in lines:
		if 'c number of cubes' in line:
			cubes = int(line.split('c number of cubes ')[1].split(',')[0])
			refuted_leaves = int(line.split(' refuted leaves')[0].split(' ')[-1])
	return cubes, refuted_leaves

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

# Find a satisfying assignment in CDCL solver's log:
def find_sat_log(o):
	res = False
	lines = o.split('\n')
	for line in lines:
		if len(line) < 12:
			continue
		if 's SATISFIABLE' in line:
			res = True
			break
	return res

# Generate a random sample of cubes:
def get_random_cubes(cubes_name):
	global op
	lines = []
	random_cubes = []
	remaining_cubes_str = []
	with open(cubes_name, 'r') as cubes_file:
		lines = cubes_file.readlines()
		if len(lines) > op.sample_size:
			random_lines = random.sample(lines, op.sample_size)
			for line in random_lines:
				lst = line.split(' ')[1:-1] # skip 'a' and '0'
				random_cubes.append(lst)
			remaining_cubes_str = [line for line in lines if line not in random_lines]
		else:
			logging.error('skip n: number of cubes is smaller than random sample size')

	if len(random_cubes) > 0 and len(random_cubes) + len(remaining_cubes_str) != len(lines):
		logging.error('incorrect number of of random and remaining cubes')
		exit(1)
	return random_cubes, remaining_cubes_str

# Process a given threshold n:
def process_n(n : int, cnf_name : str, op : Options):
	print('n : %d' % n)
	start_t = time.time()
	cubes_name = './cubes_n_' + str(n) + '_' + cnf_name.replace('./','').replace('.cnf','')
	system_str = 'timelimit -T 1 -t ' + str(int(op.max_la_time)) +  ' ' + op.la_solver + ' ' + cnf_name + \
	' -n ' + str(n) + ' -o ' + cubes_name
	out = os.popen(system_str).read()
	t = time.time() - start_t
	cubes_num = -1
	refuted_leaves = -1
	cubing_time = -1.0
	cubes_num, refuted_leaves = parse_cubing_log(out)
	real_cubes_num = 0
	# Check that the real number of cubes matches with the declared number:
	with open(cubes_name, 'r') as f:
		lines = f.read().splitlines()
		for line in lines:
			if len(line) > 2 and line[:2] == 'a ':
				real_cubes_num += 1
	assert(real_cubes_num == cubes_num)
	cubing_time = float(t)
	return n, cubes_num, refuted_leaves, cubing_time, cubes_name

# Collect result for threshold n:
def collect_n_result(res):
	global op
	global random_cubes_n
	global cubes_num_lst
	global exit_cubes_creating
	n = res[0]
	cubes_num = res[1]
	refuted_leaves = res[2]
	cubing_time = res[3]
	cubes_name = res[4]
	if cubes_num >= op.min_cubes and cubes_num <= op.max_cubes and cubes_num >= op.sample_size and refuted_leaves >= op.min_refuted_leaves:
		logging.info(res)
		ofile = open(stat_name,'a')
		ofile.write('%d %d %d %.2f\n' % (n, cubes_num, refuted_leaves, cubing_time))
		ofile.close()
		random_cubes = []
		random_cubes, remaining_cubes_str = get_random_cubes(cubes_name)
		if len(random_cubes) > 0: # if random sample is small enough to obtain it
			random_cubes_n[n] = random_cubes
	else:
		remove_file(cubes_name)
	if cubes_num > op.max_cubes or cubing_time > op.max_la_time:
		exit_cubes_creating = True
		logging.info('exit_cubes_creating : ' + str(exit_cubes_creating))
	else:
		cubes_num_lst.append(cubes_num)

# Stop CDCL solver:
def stop_solver(solver : str, message : str, res=[]):
	global stopped_solvers
	global start_time
	logging.info('*** Interrupt due to: ' + message)
	logging.info('Result:')
	logging.info(res)
	elapsed_time = time.time() - start_time
	logging.info('elapsed_time : ' + str(elapsed_time))
	stopped_solvers.add(solver)
	logging.info('stopped solvers : ')
	logging.info(stopped_solvers)
	kill_solver(solver)

# Add cube to a CNF as one-literal clauses, run CDCL solver:
def process_cube_solver(cnf_name : str, n : int, cube : list, cube_index : int, task_index : int, solver : str):
	global op
	known_cube_cnf_name = './sample_cnf_n_' + str(n) + '_cube_' + str(cube_index) + '_task_' + str(task_index) + '.cnf'
	add_cube(cnf_name, known_cube_cnf_name, cube)

	# Parse clasp's parameters:
	solver_params = ''
	if 'clasp' in solver:
		clasp_config = 'auto'
		clasp_enum = 'auto'
		words = solver.split('-')
		if len(words) > 1:
			clasp_config = words[1]
			solver = words[0]
		if len(words) > 2:
			clasp_enum = words[2]
		solver_params = '--configuration=' + clasp_config + ' --enum-mode=' \
			+ clasp_enum + ' --models=0'

	if op.param_file != '':
	    with open(op.param_file, 'r') as f:
	      lines = f.read().splitlines()
	      assert(len(lines) > 0)
	      solver_params += lines[0]
	if '.sh' in solver:
		sys_str = solver + ' ' + known_cube_cnf_name + ' ' + str(op.max_cdcl_time)
	else:
		sys_str = 'timelimit -T 1 -t ' + str(op.max_cdcl_time) + ' ' + solver + \
			' ' + solver_params + ' ' + known_cube_cnf_name
	t = time.time()
	cdcl_log = os.popen(sys_str).read()
	t = time.time() - t
	solver_time = float(t)
	isSat = find_sat_log(cdcl_log)
	if not isSat:
		# remove cnf with known cube
		remove_file(known_cube_cnf_name)
		cdcl_log = ''
	return cnf_name, n, cube_index, solver, solver_time, isSat, cdcl_log, known_cube_cnf_name

# Collect a result obtained by CDCL solver on a CNF with cube:
def collect_cube_solver_result(res):
	global results
	global op
	global start_time
	cnf_name = res[0]
	n = res[1]
	cube_index = res[2]
	solver = res[3]
	solver_time = res[4]
	isSat = res[5]
	cdcl_log = res[6]
	known_cube_cnf_name = res[7]
	results[n].append((cube_index,solver,solver_time)) # append a tuple
	logging.info('n : %d, got %d results - cube_index %d, solver %s, time %f' % (n, len(results[n]), cube_index, solver, solver_time))
	if isSat:
		logging.info('*** SAT. Writing satisfying assignment to a file.')
		elapsed_time = time.time() - start_time
		logging.info('elapsed_time : ' + str(elapsed_time))
		sat_name = cnf_name.replace('./','').replace('.cnf','') + '_n' + str(n) + '_' + solver + '_cube_index_' + str(cube_index) 
		sat_name = sat_name.replace('./','')
		with open('!sat_' + sat_name, 'w') as ofile:
			ofile.write('*** SAT found\n')
			ofile.write(cdcl_log)
		# Copyt the SAT-CNF to a file that will not be deleted:
		sat_cnf_name = '!cnf_' + sat_name
		sys_str = 'cp ' + known_cube_cnf_name + ' ' + sat_cnf_name
		os.popen(sys_str).read()
		# Stop solver if needed:
		if op.stop_sat:
			stop_solver(solver, 'SAT was found', res)
	elif solver_time > op.max_cdcl_time and op.stop_time:
		stop_solver(solver, 'CDCL solver reached time limit', res)

# Main function:
if __name__ == '__main__':
	exit_cubes_creating = False

	if len(sys.argv) < 2:
		print_usage()
		exit(1)
	cnf_name = sys.argv[1]

	op = Options()
	op.read(sys.argv[2:])
	print(op)

	random.seed(op.seed)

	log_name = './log_' + cnf_name.replace('./','').replace('.','')
	print('log_name : ' + log_name)
	logging.basicConfig(filename=log_name, filemode = 'w', level=logging.INFO)

	logging.info('cnf : ' + cnf_name)
	logging.info('total number of CPU cures: %d' % mp.cpu_count())
	logging.info('used CPU cores : %d' % op.cpu_num)
	logging.info('Options: \n' + str(op))

	start_time = time.time()

	# Count free variables:
	free_vars_num = get_march_free_vars_num(op.la_solver, cnf_name)
	logging.info('free vars : %d' % free_vars_num)
	n = free_vars_num
	while n % op.nstep != 0 and n > 0:
		n -= 1
	logging.info('start n : %d ' % n)

	# Prepare an output file:
	stat_name = 'stat_' + cnf_name
	stat_name = stat_name.replace('.','')
	stat_name = stat_name.replace('/','')
	stat_file = open(stat_name,'w')
	stat_file.write('n cubes refuted-leaves cubing-time\n')
	stat_file.close()

	random_cubes_n = dict()
	cubes_num_lst = []
	# Use 1 CPU core if many cubes (too much RAM):
	if op.max_cubes > op.max_cubes_parallel:
		pool = mp.Pool(1)
	else:
		pool = mp.Pool(op.cpu_num)
	# Find required n and their cubes numbers:
	while not exit_cubes_creating:
		pool.apply_async(process_n, args=(n, cnf_name, op), callback=collect_n_result)
		while len(pool._cache) >= op.cpu_num: # wait until any cpu is free
			time.sleep(2)
		n -= op.nstep
		if len(cubes_num_lst) >= 2:
			next_predicted_cubes_num = cubes_num_lst[-1] / cubes_num_lst[-2]
			next_predicted_cubes_num *= cubes_num_lst[-1]
			s = '2 last cubes_num_lst : ' + str(cubes_num_lst[-2]) + ' , ' + str(cubes_num_lst[-1])
			s += ' ; next_predicted_cubes_num : ' + str(next_predicted_cubes_num)
			logging.info(s)
			print(s)
			if next_predicted_cubes_num > op.max_cubes or next_predicted_cubes_num <= 0:
				logging.info('Stop due to high next cubes num')
				print('Stop due to high next cubes num')
				exit_cubes_creating = True
		if exit_cubes_creating or n <= 0:
			time.sleep(2) # wait for la completion
			#pool.terminate()
			logging.info('Stop cubing phase. Last cubes nums are ' + str(cubes_num_lst[-2]) + ', ' + str(cubes_num_lst[-1]))
			print('Stop cubing phase')
			logging.info('killing unuseful processes')
			#kill_unuseful_processes(op.la_solver)
			time.sleep(2) # wait for processes' termination
			break

	elapsed_time = time.time() - start_time
	logging.info('elapsed_time : ' + str(elapsed_time))
	logging.info('random_cubes_n : ')

	pool.close()
	pool.join()

	pool2 = mp.Pool(op.cpu_num)

	# Prepare file for results:
	sample_name = 'sample_results_' + cnf_name
	sample_name = sample_name.replace('.','')
	sample_name = sample_name.replace('/','')
	sample_name += '.csv'
	with open(sample_name, 'w') as sample_file:
		sample_file.write('n cube-index solver time\n')
	# Sort dict by n in descending order:
	sorted_random_cubes_n = collections.OrderedDict(sorted(random_cubes_n.items()))

	logging.info('sorted_random_cubes_n : ')
	logging.info(sorted_random_cubes_n)
	# for evary n solve cube-problems from the random sample:
	logging.info('')
	logging.info('processing random samples')
	logging.info('')

	solvers = op.cdcl_solvers

	stopped_solvers = set()
	results = dict()
	isExit = False
	for n, random_cubes in sorted_random_cubes_n.items():
		if isExit:
				break
		logging.info('*** n : %d' % n)
		logging.info('random_cubes size : %d' % len(random_cubes))
		results[n] = []
		task_index = 0

		for solver in solvers:
			print('CDCL solver : ' + solver)
			logging.info('CDCL solver : ' + solver)
			if isExit:
				break
			if solver in stopped_solvers:
				continue
			cube_index = 0
			exit_solving = False
			for cube in random_cubes:
				while len(pool2._cache) >= op.cpu_num:
					time.sleep(2)
				# Break if solver becomes a stopped one.
				if solver in stopped_solvers:
					break
				# Break if script time limit is reached:
				if time.time() - start_time > op.max_script_time:
					logging.info('Script time limit it reached, stop.')
					isExit = True
					break
				pool2.apply_async(process_cube_solver, args=(cnf_name, n, cube, cube_index, task_index, solver), callback=collect_cube_solver_result)
				task_index += 1
				cube_index += 1
		time.sleep(2)
		logging.info('results[n] len : %d' % len(results[n]))
		#logging.info(results[n])
		elapsed_time = time.time() - start_time
		logging.info('elapsed_time : ' + str(elapsed_time) + '\n')

		if len(stopped_solvers) == len(solvers):
			logging.info('stop main loop')
			break

	pool2.close()
	pool2.join()

	# Kill remaining processes if any:
	kill_unuseful_processes(op.la_solver)
	for solver in solvers:
		kill_solver(solver)

	# Write results:
	for n, res in results.items():
		with open(sample_name, 'a') as sample_file:
			for r in res:
				sample_file.write('%d %d %s %.2f\n' % (n, r[0], r[1], r[2])) # tuple (cube_index,solver,solver_time)

	# Remove tmp files from solver's script:
	remove_file('./*.mincnf')
	remove_file('./*.cubes')
	remove_file('./*.ext')
	remove_file('./*.icnf')

	elapsed_time = time.time() - start_time
	logging.info('elapsed_time : ' + str(elapsed_time))
