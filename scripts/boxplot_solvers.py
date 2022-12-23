# Created on: 5 Apr 2020
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Calculate runtime estimations given a SAT solver's runtimes on a sample
# and the total amount of cubes.
#==============================================================================

import matplotlib.pyplot as plt
import pandas as pd
import statistics
import numpy as np
import sys
import glob
import os

version = "0.1.11"
script_name = 'boxplot_solvers.py'

PC_CORES = 12
SOLVER_TIME_LIM = 5000.0
y_limit = 5100
EST_STR_WIDTH = 25
SAMPLE_SIZE = 1000
PARSE_TIME = 0.01

solvers_short_names_dict = {'./cnc-cadical.sh' : 'cnc_cad', './cnc-glucose.sh' : 'cnc_gluc',  './rokk' : 'rokk', \
'./minisat2.2' : 'minisat', './slime' : 'slime', './cdclcrypto' : 'cdclcrypto', './kissat_sc2021' : 'kissat-2021', \
'./kissat-unsat' : 'kissat-u', './kissat-sat' : 'kissat-s', './cryptominisat5' : 'cm5', './v3' : 'v3', \
'./MapleLCMDistChrBt-DL-v3' : 'v3', './kissat' : 'kissat', 'kissat_sc2021' : 'kissat', './cadical_1.4.1' : 'cadical', \
'./cube-glucose-min10sec-cad130.sh' : 'igl-10s', './cube-glucose-min1min-cad130.sh' : 'igl-1m', \
'./cube-glucose-min2min-cad130.sh' : 'igl-2m', './cube-cad130-min10sec-cad130.sh' : 'icad130-10s', \
'./cube-cad130-min1min-cad130.sh' : 'icad130-min1m', './cube-cad130-min2min-cad130.sh' : 'icad130-min2m', \
'kissat_3.0.0' : 'kissat3', 'cnc_cadical.sh' : 'cnc_cadical', 'kissat_sc2022-bulky' : 'kissat-bulky'}

def make_medians_upper_whiskers(df):
	medians = dict()
	upper_whiskers = dict()
	for col in df.columns:
		medians[col] = statistics.median(df[col])
		# calculate upper whisker
		q1 = np.percentile(df[col], 25) # q1
		q3 = np.percentile(df[col], 75) # q3
		iqr = q3 - q1
		upper_whisker_bound = q3 + iqr*1.5
		#upper_whisker_bound = np.percentile(df[col], 91, interpolation='higher')
		print('upper_whisker_bound : %.2f' % upper_whisker_bound)
		upper_whisker = -1.0
		rev_sort = sorted(df[col], reverse = True)
		print(rev_sort)
		for x in rev_sort:
			if x <= upper_whisker_bound:
				upper_whisker = x
				break
		upper_whiskers[col] = upper_whisker
		#print('upper_whisker : %.2f' % upper_whisker)
	return medians, upper_whiskers
	
def process_n_stat_file(n_stat_file_name : str):
	n = int(n_stat_file_name.split('_n_')[1].split('.')[0])
	print('\n*** n : %d\n' % n)
	#print('input file : ' + n_stat_file_name)
	df= pd.read_csv(n_stat_file_name, delimiter = ' ')
	#print(df)

	del df['n']
	del df['cnfid']
	del df['march-cu-time']
	del df['cubes']
	del df['refuted-leaves']

	df = df.rename(columns={'cube-glucose-mpi-min2min.sh' : 'gl-min2m', 'cube-glucose-mpi-min1min.sh' : 'gl-min1m', 'cube-glucose-mpi-min10sec.sh' : 'gl-min10s', 'cube-glucose-mpi-nomin.sh' : 'gl-nomin'})
	df = df.rename(columns={'march-cu-time_cube-glucose-mpi-min2min.sh' : 'm-gl-min2m', 'march-cu-time_cube-glucose-mpi-min1min.sh' : 'm-gl-min1m', 'march-cu-time_cube-glucose-mpi-min10sec.sh' : 'm-gl-min10s', 'march-cu-time_cube-glucose-mpi-nomin.sh' : 'm-gl-nomin'})
	# replace -1.0 caused by solving on the minimization phase
	d = {-1.00 : 0.00}
	df = df.replace(d)
	
	medians, upper_whiskers = make_medians_upper_whiskers(df)
	
	myFig = plt.figure();
	plt.ylim(0, y_limit)
	_, bp = pd.DataFrame.boxplot(df, return_type='both')
	n_stat_file_name = n_stat_file_name.replace('./','')
	myFig.savefig("boxplot_" + n_stat_file_name.split('.')[0] + ".pdf", format="pdf")

	#whiskers = [whiskers.get_ydata() for whiskers in bp['whiskers']]
	#print('whiskers :')
	#print(whiskers)
	
	return n, medians, upper_whiskers

def process_sat_samples(sat_samples_files_mask : str, cubes_dict : dict, unsat_samples : dict):
	os.chdir('./')
	n_stat_file_names = []
	for fname in glob.glob(sat_samples_files_mask):
		n_stat_file_names.append(fname)

	print('n_stat_file_names : ')
	print(n_stat_file_names)

	n_solvers_upper_whiskers = dict()
	n_solvers_medians = dict()
	for fname in n_stat_file_names:
		n, n_solvers_medians[n], n_solvers_upper_whiskers[n] = process_n_stat_file(fname)
	
	if len(unsat_samples) > 0:
		samples_comb_est = dict()
		for n in unsat_samples:
			samples_comb_est[n] = dict()
			print('n : %d' % n)
			for s in unsat_samples[n]:
				lst_val_less_median = [x for x in unsat_samples[n][s] if x <= n_solvers_medians[n][s]]
				lst_val_greater_median = [x for x in unsat_samples[n][s] if x > n_solvers_medians[n][s]]
				frac_less_median = len(lst_val_less_median) / len(unsat_samples[n][s])
				frac_greater_median = len(lst_val_greater_median) / len(unsat_samples[n][s])
				print('frac_less_median : %.2f' % frac_less_median)
				print('frac_greater_median : %.2f' % frac_greater_median)

	with open('total_stat_' + sat_samples_files_mask.replace('*',''), 'w') as ofile:
		s_names = []
		for n in cubes_dict:
			for s in n_solvers_upper_whiskers[n]:
				s_names.append(s)
			break
		
		ofile.write('n cubes')
		for s in s_names:
			ofile.write(' m_' + s)
		for s in s_names:
			ofile.write(' up_wh_' + s)
		ofile.write('\n')
		for n in cubes_dict:
			if n not in n_solvers_upper_whiskers:
				continue
			ofile.write('%d %d' % (n, cubes_dict[n]))
			for s in s_names:
				ofile.write(' %.2f' % n_solvers_medians[n][s])
			for s in s_names:
				ofile.write(' %.2f' % n_solvers_upper_whiskers[n][s])
			ofile.write('\n')
		
def read_unsat_samples(unsat_samples_file_name : str):
	df_unsat_samples = pd.read_csv(unsat_samples_file_name, delimiter = ' ')
	samples = dict()
	for index, row in df_unsat_samples.iterrows():
		n = int(row['n'])
		t = float(row['time'])
		if t >= SOLVER_TIME_LIM:
			t = -1
		s = solvers_short_names_dict[row['solver']]
		if n not in unsat_samples:
			unsat_samples[n] = dict()
		if s not in unsat_samples[n]:
			unsat_samples[n][s] = []
		unsat_samples[n][s].append(t)

	unsat_samples_mean = dict()
	for n in unsat_samples:
		unsat_samples_mean[n] = dict()
		for s in unsat_samples[n]:
			unsolved_num = unsat_samples[n][s].count(-1) # count unsolved instances
			if unsolved_num > 0:
				unsat_samples_mean[n][s] = -unsolved_num # show number of unsolved
			else:
				unsat_samples_mean[n][s] = statistics.mean(unsat_samples[n][s])
	return unsat_samples, unsat_samples_mean

def process_unsat_samples(unsat_samples_file_name : str, cubes_dict : dict ):
	unsat_samples, unsat_samples_mean = read_unsat_samples(unsat_samples_file_name)
	print('unsat_samples_mean : ')
	print(unsat_samples_mean)
	unsat_samples_est = dict()
	solvers = []
	for n in unsat_samples_mean:
		if n not in cubes_dict:
			continue
		unsat_samples_est[n] = dict()
		for s in unsat_samples_mean[n]:
			if s not in solvers:
				solvers.append(s)

			if unsat_samples_mean[n][s] < 0:
				unsat_samples_est[n][s] = 'inter_' + str(abs(unsat_samples_mean[n][s])) + '/' + str(len(unsat_samples[n][s]))
			elif len(unsat_samples[n][s]) < SAMPLE_SIZE:
				unsat_samples_est[n][s] = 'solved_' + str(len(unsat_samples[n][s])) + '/' + str(SAMPLE_SIZE)
			else:
				remaining_cubes_num = cubes_dict[n] - SAMPLE_SIZE
				unsat_samples_est[n][s] = (unsat_samples_mean[n][s] + PARSE_TIME) * remaining_cubes_num
		with open('est_' + unsat_samples_file_name, 'w') as unsat_samples_est_file:
			unsat_samples_est_file.write('n'.ljust(5))
			for s in solvers:
				st = s + '_sec_1core'
				unsat_samples_est_file.write(st.ljust(EST_STR_WIDTH))
				st = s + '_days_' + str(PC_CORES) + "cores"
				unsat_samples_est_file.write(st.ljust(EST_STR_WIDTH))
				unsat_samples_est_file.write('cubes')
			unsat_samples_est_file.write('\n')
			lst_n = []
			for n in unsat_samples_est:
				lst_n.append(n)
			lst_n.reverse()
			for n in lst_n:
				unsat_samples_est_file.write(('%d' % n).ljust(5))
				#for s in samples_unsat_est[n]:
				for s in solvers:
					if isinstance(unsat_samples_est[n][s], str):
						unsat_samples_est_file.write(unsat_samples_est[n][s].ljust(EST_STR_WIDTH))
						unsat_samples_est_file.write(unsat_samples_est[n][s].ljust(EST_STR_WIDTH))
					else:
						int_sec = int(unsat_samples_est[n][s])
						m_s = str(int_sec).ljust(EST_STR_WIDTH)
						unsat_samples_est_file.write(m_s)
						float_days = unsat_samples_est[n][s] / 86400 / PC_CORES
						m_s = ('%.3f' % float_days).ljust(EST_STR_WIDTH)
						unsat_samples_est_file.write(m_s)
				unsat_samples_est_file.write(str(cubes_dict[n]))
				unsat_samples_est_file.write('\n')
	print('unsat_samples_est : ')
	print(unsat_samples_est)

if __name__ == '__main__':
	if len(sys.argv) < 3:
			sys.exit('Usage: ' + script_name + ' stat_file sample_runtimes|-s=sat_logs_mask')

	cubes_stat_file_name = sys.argv[1]
	print('cubes_stat_file_name : ' + cubes_stat_file_name)
	unsat_samples_file_name = ''
	sat_samples_files_mask = ''
	word = sys.argv[2]
	assert(len(word) > 2)
	if word[:2] == '-s=':
		sat_samples_files_mask = word.split('-s=')[1].replace('./', '')
		print('sat_samples_files_mask : ' + sat_samples_files_mask)
	else:
		assert('-u=' not in word)
		unsat_samples_file_name = word.replace('./', '')
		print('unsat_samples_file_name : ' + unsat_samples_file_name)

	cubes_dict = dict()
	df = pd.read_csv(cubes_stat_file_name, delimiter = ' ')
	for index, row in df.iterrows():
		cubes_dict[int(row['n'])] = int(row['cubes'])
	print('cubes_dict : ')
	print(cubes_dict)

	unsat_samples = dict()
	if unsat_samples_file_name != '':
		unsat_samples = process_unsat_samples(unsat_samples_file_name, cubes_dict)

	if sat_samples_files_mask != '':
		process_sat_samples(sat_samples_files_mask, cubes_dict, unsat_samples)
