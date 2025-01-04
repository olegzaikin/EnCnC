// Created on: 1 Apr 2020
// Author: Oleg Zaikin
// E-mail: zaikin.icc@gmail.com
//
// Adds cubes to a CNF, and solves the resulted subproblems by a CDCL solver.
//
// Usage : conquer solver cnf cubes cube [Options]
// By default all threads are used.
//
// Example:
//     ./conquer ./kissat problem.cnf ./cubes 5000 -cpunum=12
//   adds cubes from the file ./cubes to the CNF problem.cnf and solves them by
//   the solver kissat in 12 threads.
//=============================================================================

#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <cassert>
#include <chrono>
#include <limits>
#include <thread>
#include <random>

#include <omp.h>

std::string version = "0.3.2";

#define cube_t std::vector<int> 
#define time_point_t std::chrono::time_point<std::chrono::system_clock>

bool verb = false;

enum status{ NOT_STARTED = -1, IN_PROGRESS = 0, PROCESSED = 1};
enum result{ UNSAT = 0, SAT = 1, INTERR = 2 };

struct workunit {
	int id;
	status stts;
	result rslt;
	cube_t cube;
	double time;
	workunit() : id(-1), stts(NOT_STARTED), rslt(INTERR), cube(), time(-1) {};
	void print() {
		for (auto &c : cube) std::cout << c << " ";
		std::cout << std::endl;
	}
};

struct cnf {
	long long int var_num;
	long long int clause_num;
	std::vector<std::string> clauses;
	cnf() : var_num(0), clause_num(0), clauses() {}
	cnf(std::string cnf_name) : var_num(0), clause_num(0), clauses() {
		read(cnf_name);
	}
	void read(std::string cnf_name) {
		std::ifstream cnf_file(cnf_name, std::ios_base::in);
		std::string str;
		while (getline(cnf_file, str)) {
			if (str.size() == 0 or str[0] == 'p' or str[0] == 'c')
				continue;
			clauses.push_back(str);
			clause_num++;
			std::stringstream sstream;
			sstream << str;
			long long int ival;
			while (sstream >> ival)	var_num = std::max(llabs(ival), var_num);
		}
		cnf_file.close();
	}
	void print() {
		std::cout << "var_num : " << var_num << std::endl;
		std::cout << "clause_num : " << clause_num << std::endl;
	};
};

std::vector<workunit> read_cubes(const std::string cubes_name);
std::string str_after_prefix(std::string str, std::string prefix);
bool compare_by_cube_size(const workunit &a, const workunit &b);
std::vector<workunit> read_cubes(const std::string cubes_file_name);
result solve_cube(const cnf c, const std::string postfix, const std::string solver_name,
		const std::string param_str, const std::string cnf_name,
		const time_point_t program_start, workunit &wu,
		const unsigned cube_time_lim);
void write_cubes_info(const std::string postfix,
                      const std::vector<workunit> &wu_vec);
void write_stat(const std::string postfix,
                const std::vector<workunit> &wu_vec, const time_point_t start);
void write_interrupted_cubes(const std::string postfix,
                             const std::vector<workunit> &wu_vec);
std::string exec(const std::string cmd_str);
result read_solver_result(const std::string fname);
std::string clear_name(const std::string name);
void kill_solver(std::string solver_name);

void print_usage() {
	std::cout << "Usage : conquer solver CNF cubes cube-time-limit [Options]"
	  	<< std::endl;
	std::cout << "  Options:" << std::endl
		  << "    -cpunum=<int>   : (default = all cores) CPU cores" << std::endl
		  << "    -param=<string> : solver's command-line parameters" << std::endl
                  << "    --verb : increase verbosity." << std::endl
		  << "    --enum : solve all subproblems." << std::endl;
	std::cout << "NB1 : the solver must be a local file, i.e. ./minisat "
			<< "instead of minisat" << std::endl;
	std::cout << "NB2 : the local utility timelimit must be in the directory" << std::endl;
}

void print_version() {
	std::cout << "version: " << version << std::endl;
}

void print_stats(const unsigned long long sat_cubes,
								 const unsigned long long unsat_cubes,
								 const unsigned long long interr_cubes
)
{
	std::cout << "sat-cubes : " << sat_cubes
			      << "  unsat-cubes : " << unsat_cubes
			      << "  interr-cubes : " << interr_cubes
			      << std::endl;
}

int main(const int argc, const char *argv[]) {
	std::vector<std::string> str_argv;
	for (int i=0; i < argc; ++i) str_argv.push_back(argv[i]);
	assert(str_argv.size() == argc);
	if (argc == 2 and str_argv[1] == "-h") {
		print_usage();
		std::exit(EXIT_SUCCESS);
	}
	if (argc == 2 and str_argv[1] == "-v") {
		print_version();
		std::exit(EXIT_SUCCESS);
	}
	if (argc < 5) {
		print_usage();
		std::exit(EXIT_FAILURE);
	}

	std::string solver_name	= str_argv[1];
	std::string cnf_name    = str_argv[2];
	std::string cubes_name  = str_argv[3];
	const unsigned cube_time_lim  = std::stoi(str_argv[4]);
	assert(cube_time_lim > 0);
	bool isEnum = false;
	unsigned cpunum = 0;
	std::string param_file_name = "";
	if (argc > 5) {
	    for (int i=5; i < argc; ++i) {
		    if (str_argv[i] == "--verb")
			    verb = true;
		    else if (str_argv[i] == "--enum")
			    isEnum = true;
		    else {
			std::string s = str_after_prefix(str_argv[i], "-cpunum=");
			if (s != "") std::istringstream(s) >> cpunum;
			param_file_name = str_after_prefix(str_argv[i], "-param=");
		    }
	    }
	}
	std::cout << "solver_name   : " << solver_name   << std::endl;
	std::cout << "cnf_name      : " << cnf_name      << std::endl;
	std::cout << "cubes_name    : " << cubes_name    << std::endl;
	std::cout << "cube_time_lim : " << cube_time_lim << std::endl;
	std::cout << "param_f_name  : " << param_file_name << std::endl;
	std::cout << "cpunum        : " << cpunum        << std::endl;
	std::cout << "verbosity     : " << verb          << std::endl;
	std::cout << "enum          : " << isEnum        << std::endl << std::endl;

	// Generate a random number and add it as string to solver name.
	// To goal it safely killall solver once SAT is found.
	std::random_device dev;
	std::mt19937 rng(dev());
	std::uniform_int_distribution<std::mt19937::result_type> dist(1,1000000);
	int rand = dist(rng);
	std::stringstream sstream;
	sstream << rand;
	std::string new_solver_name = solver_name + "_" + sstream.str();
	std::cout << new_solver_name << std::endl;
	std::string system_str = "cp " + solver_name + " " + new_solver_name;
	exec(system_str);
	solver_name = new_solver_name;
	std::cout << "Updated solver name : " << solver_name << std::endl;

	const unsigned nthreads = cpunum > 0 ? cpunum : std::thread::hardware_concurrency();
	std::cout << "threads       : " << nthreads << std::endl;
	omp_set_num_threads(nthreads);

	const time_point_t program_start = std::chrono::system_clock::now();

	std::vector<workunit> wu_vec = read_cubes(cubes_name);
	assert(wu_vec.size() > 0);
	// Sort cubes by size in descending order:
	//std::stable_sort(wu_vec.begin(), wu_vec.end(), compare_by_cube_size);
	std::cout << "cubes : " << wu_vec.size() << std::endl;
	std::cout << "first cubes : " << std::endl;
	unsigned maxprint = wu_vec.size() >= 3 ? 3 : wu_vec.size(); 
	for (unsigned i = 0; i < maxprint; i++) wu_vec[i].print();

	cnf c(cnf_name);
	c.print();

	std::string param_str = "";
	if (param_file_name != "") {
		std::ifstream param_file(param_file_name, std::ios_base::in);
		getline(param_file, param_str);
		param_file.close();
		std::cout << "param_str : " << param_str << std::endl;
	}


	const std::string postfix = clear_name(solver_name) + "_" + clear_name(cnf_name) +
	                            "_" + clear_name(cubes_name);

	unsigned long long sat_cubes = 0;
	unsigned long long unsat_cubes = 0;
	unsigned long long interr_cubes = 0;
	unsigned long long skipped_cubes = 0;
	
	// Process all workunits in parallel:
	#pragma omp parallel for schedule(dynamic, 1)
	for (auto &wu : wu_vec) {
		if (sat_cubes && !isEnum) {
		    //std::cout << "Skip a cube because SAT is found." << std::endl;
				skipped_cubes++;
				continue;
		}
		result res = solve_cube(c, postfix, solver_name, param_str, cnf_name,
                  program_start, wu, cube_time_lim);
		if (res == SAT) {
			sat_cubes++;
			std::cout << "SAT is found." << std::endl;
			print_stats(sat_cubes, unsat_cubes, interr_cubes);
			// Kill the solver once if the SAT finding mode:
			std::cout << "Killing solver " << solver_name << std::endl;
			if(!isEnum) kill_solver(solver_name);
		}
		else if (res == UNSAT) {
			unsat_cubes++;
			print_stats(sat_cubes, unsat_cubes, interr_cubes);
		}
		else {
			interr_cubes++;
			assert(res == INTERR);
			print_stats(sat_cubes, unsat_cubes, interr_cubes);
		}
	}

	std::cout << "skipped-cubes : " << skipped_cubes << std::endl;

	unsigned long long wus_num = wu_vec.size();
	long long diff_num = wus_num - (sat_cubes + unsat_cubes + interr_cubes + skipped_cubes);
	// diff_num can be > 0 because solver is interrupted when SAT is found:
	assert(diff_num >= 0);
	if (diff_num > 0) {
		interr_cubes += diff_num;
		std::cout << " Statuses of " << diff_num << " are not clear, so they are marked as interrupted" << std::endl;
	}

	std::cout << "\nResult : ";
	if (sat_cubes) {
		assert(unsat_cubes < wus_num);
		assert(interr_cubes < wus_num);
		std::cout << "SAT" << std::endl;
	}
	else if (unsat_cubes == wus_num) {
		assert(interr_cubes == 0);
		std::cout << "UNSAT" << std::endl;
	} 
	else {
		std::cout << "INTERRUPTED" << std::endl;
	}

	// Write statistics:
	write_stat(postfix, wu_vec, program_start);
	write_cubes_info(postfix, wu_vec);

	// Write interrupted cubes to a file:
	write_interrupted_cubes(postfix, wu_vec);

	const time_point_t program_end = std::chrono::system_clock::now();

	std::cout << "Elapsed : "
	<< std::chrono::duration_cast<std::chrono::seconds>(program_end - program_start).count()
	<< " seconds" << std::endl;

	return 0;
}



// Read cubes from a given file
std::vector<workunit> read_cubes(const std::string cubes_name) {
	std::vector<workunit> wu_cubes;
	std::ifstream cubes_file(cubes_name);
	if (!cubes_file.is_open()) {
		std::cerr << "cubes_file " << cubes_name << " wasn't opened\n";
		std::exit(EXIT_FAILURE);
	}
	
	std::string str;
	std::stringstream sstream;
	std::vector<workunit> wu_vec;
	int id = 0;
	while (getline(cubes_file, str)) {
		sstream << str;
		std::string word;
		workunit wu;
		assert(wu.id == -1);
		assert(wu.stts == NOT_STARTED);
		assert(wu.rslt == INTERR);
		assert(wu.time == -1);
		while (sstream >> word) {
			if (word == "a" or word == "0") continue;
			wu.cube.push_back(std::stoi(word));
		}
		sstream.str(""); sstream.clear();
		wu.id = id++;
		wu_vec.push_back(wu);
	}
	cubes_file.close();
	assert(wu_vec.size() > 0);
	return wu_vec;
}

std::string str_after_prefix(std::string str, std::string prefix) {
    int found = str.find( prefix );
    if ( found != -1 )
	return str.substr( found + prefix.length( ) );
    return "";
}

std::string clear_name(const std::string name) {
	std::string res = name;
	res.erase(remove(res.begin(), res.end(), '.'), res.end());
	res.erase(remove(res.begin(), res.end(), '/'), res.end());
	return res;
}

void write_interrupted_cubes(const std::string postfix,
                             const std::vector<workunit> &wu_vec) {
	std::string fname = "!interrupted_" + postfix;
	std::ofstream inter_file(fname, std::ios_base::out);
	for (auto &wu : wu_vec) {
		if (wu.rslt == INTERR) {
			inter_file << "a ";
			for (auto lit : wu.cube) inter_file << lit << " ";
			inter_file << "0" << std::endl;
		}
	}
	inter_file.close();
}

void write_cubes_info(const std::string postfix,
                      const std::vector<workunit> &wu_vec) {
	std::string fname = "!cubes_info_" + postfix;
	std::ofstream ofile(fname, std::ios_base::out);
	ofile << "id status result time" << std::endl;
	for (auto &wu : wu_vec)
		ofile << wu.id << " " << wu.stts << " " << wu.rslt << " " <<
				     wu.time << std::endl;
	ofile.close();
}

void write_stat(const std::string postfix, const std::vector<workunit> &wu_vec,
		const time_point_t program_start) {
	assert(wu_vec.size() > 0);
	
	std::string progress_name = "!progress_" + postfix;

	double min_time_unsat = std::numeric_limits<double>::max();
	double max_time_unsat = -1;
	double avg_time_unsat = -1;
	double sum_time_unsat = 0.0;
	double min_time_sat = std::numeric_limits<double>::max();
	double max_time_sat = -1;
	double avg_time_sat = -1;
	double sum_time_sat = 0.0;
	double min_time_interr = std::numeric_limits<double>::max();
	double max_time_interr = -1;
	double avg_time_interr = -1;
	double sum_time_interr = 0.0;
	unsigned long long sat_cubes = 0;
	unsigned long long unsat_cubes = 0;
	unsigned long long interr_cubes = 0;

	unsigned long long processed_wus = 0;
	for (auto wu : wu_vec) {
		if (wu.stts != PROCESSED) continue;
		processed_wus++;
		if (wu.rslt == UNSAT) {
			unsat_cubes++;
			min_time_unsat = std::min(wu.time, min_time_unsat);
			max_time_unsat = std::max(wu.time, max_time_unsat);
			sum_time_unsat += wu.time;
		}
		else if (wu.rslt == INTERR) {
			interr_cubes++;
			min_time_interr = std::min(wu.time, min_time_interr);
			max_time_interr = std::max(wu.time, max_time_interr);
			sum_time_interr += wu.time;
		}
		else if (wu.rslt == SAT) {
			sat_cubes++;
			min_time_sat = std::min(wu.time, min_time_sat);
			max_time_sat = std::max(wu.time, max_time_sat);
			sum_time_sat += wu.time;
		}
	}

	if (sum_time_unsat > 0) avg_time_unsat = sum_time_unsat / unsat_cubes;
	if (sum_time_sat > 0) avg_time_sat = sum_time_sat / sat_cubes;
	if (sum_time_interr > 0) avg_time_interr = sum_time_interr / interr_cubes;
	double percent_val = double(processed_wus * 100) / (double)wu_vec.size();
	const time_point_t program_end = std::chrono::system_clock::now();
	const double elapsed = std::chrono::duration_cast<std::chrono::seconds>(program_end - program_start).count();

	std::ofstream ofile(progress_name, std::ios_base::out);
	ofile << "***" << std::endl
	<< "elapsed time    : " << elapsed       << std::endl
	<< "cubes           : " << wu_vec.size() << std::endl
	<< "processed cubes : " << processed_wus << ", i.e. " << percent_val
	<< " %" << std::endl
	<< "unsat_cubes     : " << unsat_cubes    << std::endl
	<< "sat_cubes       : " << sat_cubes      << std::endl
	<< "interr_cubes    : " << interr_cubes   << std::endl
	<< "min_time_unsat  : " << min_time_unsat << std::endl
	<< "max_time_unsat  : " << max_time_unsat << std::endl
  << "avg_time_unsat  : " << avg_time_unsat << std::endl
	<< "min_time_sat    : " << min_time_sat   << std::endl
	<< "max_time_sat    : " << max_time_sat   << std::endl
  << "avg_time_sat    : " << avg_time_sat   << std::endl
	<< "min_time_interr : " << min_time_interr << std::endl
	<< "max_time_interr : " << max_time_interr << std::endl
	<< "avg_time_interr : " << avg_time_interr << std::endl;
	ofile.close();
}

result solve_cube(const cnf c, const std::string postfix,
    const std::string solver_name, const std::string param_str,
    const std::string cnf_name, const time_point_t program_start,
    workunit &wu, const unsigned cube_time_lim)
{
	std::string wu_id_str = std::to_string(wu.id);
	std::string local_cnf_file_name = "id-" + wu_id_str + "-cnf";

	std::ofstream local_cnf_file(local_cnf_file_name, std::ios_base::out);
	local_cnf_file << "p cnf " << c.var_num << " "
	               << c.clause_num + wu.cube.size() << std::endl;
	for (auto cl : c.clauses) local_cnf_file << cl << std::endl;
	for (auto x : wu.cube) local_cnf_file << x << " 0" << std::endl;
	local_cnf_file.close();

	std::string system_str = "timelimit -t " + std::to_string(cube_time_lim) +
	                         " -T 1 " + solver_name;
	if (param_str != "")
	    system_str += " " + param_str;
	system_str += " " + local_cnf_file_name;
	std::cout << system_str << std::endl;
	std::string local_out_file_name = "id-" + wu_id_str + "-out";
	std::fstream local_out_file;
	local_out_file.open(local_out_file_name, std::ios_base::out);

	if ( verb ) std::cout << "system_str : " << system_str << std::endl;

	const time_point_t solver_start = std::chrono::system_clock::now();
	std::string res_str = exec(system_str);
	const time_point_t solver_end = std::chrono::system_clock::now();
	const double solver_time = std::chrono::duration_cast<std::chrono::milliseconds>(solver_end - solver_start).count() / (double)1000;
	wu.time = solver_time;

	if ( verb ) {
		std::cout << "out : " << res_str << std::endl;
		std::cout << "solver time : " << solver_time << std::endl;
	}

	local_out_file << res_str;
	local_out_file.close(); local_out_file.clear();

	result res = read_solver_result(local_out_file_name);
	wu.rslt = res;
	wu.stts = PROCESSED;

	// Remove temporary files:
	if (res == SAT) {
		const time_point_t program_end = std::chrono::system_clock::now();
		const double elapsed = std::chrono::duration_cast<std::chrono::seconds>(program_end - program_start).count();
		std::string fname = "!sat_info_cube_id_" + std::to_string(wu.id) +
												"_" + postfix;
		std::ofstream ofile(fname, std::ios_base::out);
		ofile << "SAT" << std::endl;
		ofile << "elapsed : " << elapsed << " seconds" << std::endl;
		ofile << "solver time : " << wu.time << " s" << std::endl;
		ofile << "cube id : " << wu.id << std::endl;
		ofile << "cube : " << std::endl;
		for (auto &x : wu.cube) ofile << x << " ";
		ofile << std::endl;
		ofile.close();
		system_str = "cp " + local_out_file_name + " ./!sat_out_cube_id_" +
		             wu_id_str + "_" + postfix;
		exec(system_str);
		system_str = "cp " + local_cnf_file_name +
		             " ./!sat_cnf_cube_id_" + wu_id_str + "_" + postfix;
		exec(system_str);
	}

	system_str = "rm id-" + wu_id_str + "-*";
	exec(system_str);
	return res;
}

std::string exec(const std::string cmd_str) {
	char* cmd = new char[cmd_str.size() + 1];
	for (unsigned i = 0; i < cmd_str.size(); i++)
		cmd[i] = cmd_str[i];
	cmd[cmd_str.size()] = '\0';
	FILE* pipe = popen(cmd, "r");
	delete[] cmd;
	if (!pipe) return "ERROR";
	char buffer[128];
	std::string result = "";
	while (!feof(pipe)) {
		if (fgets(buffer, 128, pipe) != NULL)
			result += buffer;
	}
	pclose(pipe);
	return result;
}

void kill_solver(std::string solver_name) {
	std::string system_str = "killall -9 " + solver_name;
	exec(system_str);
}

result read_solver_result(const std::string fname) {
	result res = INTERR;
	std::ifstream ifile(fname, std::ios_base::in);
	if (!ifile.is_open()) {
		std::cerr << "solver result file " << fname << " wasn't opened\n";
		std::exit(EXIT_FAILURE);
	}
	std::string str;
	while (getline(ifile, str)) {
		if (str.find("s SATISFIABLE") != std::string::npos) {
			res = SAT;
			break;
		}
		else if (str.find("s UNSATISFIABLE") != std::string::npos) {
			res = UNSAT;
			break;
		}
	}
	ifile.close();
	return res;
}
