// Created on: 16 March 2020
// Author: Oleg Zaikin
// E-mail: zaikin.icc@gmail.com
//
// Adds cubes to a CNF, and solves the resulted subproblems by a CDCL solver
// on a supercomputer via MPI.
//
// Usage : conquer_mpi solver-name cnf-name cubes-name cube-time-limit [--verb]
// By default all threads are used.
//
// Example:
//     ./conquer_mpi kissat problem.cnf cubes 5000
//   add cubes from file cubes to CNF in problem.cnf, solve them by kissat.
//==============================================================================

#include <mpi.h>
#include <iostream>
#include <string>
#include <fstream>
#include <sstream>
#include <vector>
#include <algorithm>
#include <cassert>

#pragma warning(disable : 4996)

using namespace std;

string prog = "conquer_mpi";
string version = "0.1.12";

struct wu
{
	int id;
	int status;
	int result;
	vector<int> cube;
	double processing_time;
};

const int NOT_STARTED = -1;
const int IN_PROGRESS = 0;
const int PROCESSED = 1;
const int UNSAT = 2;
const int SAT = 3;
const int INDET = 4;
const int REPORT_EVERY_SEC = 100;

bool compare_by_cube_size(const wu &a, const wu &b) {
	return a.cube.size() > b.cube.size();
}

void controlProcess(const int corecount, const string cubes_file_name, const bool is_enum);
vector<wu> readCubes(const string cubes_file_name);
void sendWU(vector<wu> &wu_vec, const int wu_id, const int computing_process_id);
void computingProcess(const int rank, const string solver_file_name, const string cnf_file_name, 
		      const string cubes_file_name, const string cube_cpu_lim_str, const string param_str);
void writeInfoOutFile(const string control_process_ofile_name, vector<wu> wu_vec, const double start_time);
int getResultFromFile(const string out_name);
void writeProcessingInfo(vector<wu> &wu_vec);
string exec(const string cmd_str);
string intToStr(const int x);
string strAfterPrefix(string str, string prefix);

int total_processed_wus = 0;

int main(int argc, char *argv[])
{
	int rank = 0, corecount = 0;
	
	MPI_Init(&argc, &argv);
	MPI_Comm_size(MPI_COMM_WORLD, &corecount);
	MPI_Comm_rank(MPI_COMM_WORLD, &rank);
	
	vector<string> str_argv;
	for (unsigned i=0; i<argc; ++i)
		str_argv.push_back(argv[i]);
	assert((unsigned)argc == str_argv.size());

	if (rank == 0) {
		cout << "corecount " << corecount << endl;
		if ( (argc == 2) && 
		     ((str_argv[1] == "-v") || (str_argv[1] == "--version")) ) {
		    cout << prog << " of version " << version << endl;
		    return 1;
		}
	}

	if (argc < 5) {
		cerr << "Usage : " << prog << " solver cnf cubes cube-cpu-limit [Options]" << endl;
		cerr << "  Options:" << endl <<
		        "    -param=<string> : solver parameters' file name" << endl <<
		        "    --enum          : solve all cubes-based subproblems" << endl;
		return 1;
	}

	string solver_file_name = str_argv[1];
	string cnf_file_name	= str_argv[2];
	string cubes_file_name	= str_argv[3];
	string cube_cpu_lim_str = str_argv[4];
	string param_file_name  = "";
	bool is_enum = false;
	// Try to read solver's parameters:
	if (argc > 5) {
		for (unsigned i=5; i < argc; ++i) {
			if (str_argv[i] == "--enum")
				is_enum = true;
			else {            
				string s = strAfterPrefix(str_argv[i], "-param=");
				if (s != "") param_file_name = s;
			}
		}
	}

	string param_str = "";
	if (param_file_name != "") {
		ifstream param_file(param_file_name, ios_base::in);
		getline(param_file, param_str);
		param_file.close(); 
	}

	// control or computing process
	if (rank == 0) {
		cout << "solver_file_name : " << solver_file_name << endl;
		cout << "cnf_file_name    : " << cnf_file_name << endl;
		cout << "cubes_file_name  : " << cubes_file_name << endl;
		cout << "cube_cpu_limit   : " << cube_cpu_lim_str << endl;
		cout << "param_file_name  : " << param_file_name << endl;
		cout << "is_enum          : " << is_enum << endl;
		if (param_file_name != "")
			cout << "param_str : " << param_str << endl;

		controlProcess(corecount, cubes_file_name, is_enum);
	}
	else
		computingProcess(rank, solver_file_name, cnf_file_name, cubes_file_name, 
		  cube_cpu_lim_str, param_str);

	return 0;
}

string strAfterPrefix( string str, string prefix )
{
	int found = str.find( prefix );
	if ( found != -1 )
		return str.substr( found + prefix.length( ) );
	return "";
}

string intToStr(const int x)
{
	stringstream sstream;
	sstream << x;
	return sstream.str();
}

vector<wu> readCubes(const string cubes_file_name)
{
	vector<wu> res_wu_cubes;
	ifstream cubes_file(cubes_file_name);
	if (!cubes_file.is_open()) {
		cerr << "error: cubes_file " << cubes_file_name << " wasn't opened\n";
		exit(-1);
	}
	string str;
	stringstream sstream;
	vector<wu> wu_vec;
	int wu_id = 0;
	while (getline(cubes_file, str)) {
		sstream << str;
		string word;
		wu cur_wu;
		while (sstream >> word) {
			if ((word == "a") || (word == "0"))
				continue;
			int ival;
			istringstream(word) >> ival;
			cur_wu.cube.push_back(ival);
		}
		sstream.str(""); sstream.clear();
		cur_wu.status = NOT_STARTED;
		cur_wu.id = wu_id;
		cur_wu.processing_time = -1;
		cur_wu.result = -1;
		res_wu_cubes.push_back(cur_wu);
		wu_id++;
	}
	cubes_file.close();
	
	if (!res_wu_cubes.size()) {
		cerr << "wu_vec.size() == 0";
		MPI_Abort(MPI_COMM_WORLD, 0);
		exit(1);
	}

        // Sort cubes by size in descending order:
        std::sort(res_wu_cubes.begin(), res_wu_cubes.end(), compare_by_cube_size);

	return res_wu_cubes;
}

void controlProcess(const int corecount, const string cubes_file_name, const bool is_enum)
{
	double start_time = MPI_Wtime();
	vector<wu> wu_vec = readCubes(cubes_file_name);
	// Sort cubes by size in descending order:
	//std::sort(wu_vec.begin(), wu_vec.end(), compare_by_cube_size);

	cout << "wu_vec size : " << wu_vec.size() << endl;
	cout << "first cubes : " << endl;
	for (unsigned i = 0; i < 3; i++) {
		for (auto x : wu_vec[i].cube)
			cout << x << " ";
		cout << endl;
	}
	
	// erase progress file
	string control_process_ofile_name = "!total_progress";
	ofstream control_process_ofile(control_process_ofile_name, ios_base::out);
	control_process_ofile.close();
	
	// send a wu to every computing process
	int sending_id = 0;
	for (int i = 0; i < corecount - 1; i++) {
		sendWU(wu_vec, sending_id, i + 1);
		sending_id++;
	}
	
	// receive results and send back new WUs
	int wu_id, res;
	double time;
	double result_writing_time = -1;
	int stop_mes = -1;
	MPI_Status status, current_status;
	bool is_SAT = false;
	while (total_processed_wus < wu_vec.size()) {
		// receive result
		MPI_Recv(&wu_id, 1, MPI_INT, MPI_ANY_SOURCE, 0, MPI_COMM_WORLD, &status);
		current_status = status;
		MPI_Recv(&res,  1, MPI_INT, current_status.MPI_SOURCE, 0, MPI_COMM_WORLD, &status);
		MPI_Recv(&time, 1, MPI_DOUBLE, current_status.MPI_SOURCE, 0, MPI_COMM_WORLD, &status);
		wu_vec[wu_id].status = PROCESSED;
		wu_vec[wu_id].result = res;
		wu_vec[wu_id].processing_time = time;
		total_processed_wus++;
		
		if (res == SAT) {
			is_SAT = true;
			if (not is_enum) break;
		}
	
		// send back a new WU
		if (sending_id < wu_vec.size()) {
			sendWU(wu_vec, sending_id, current_status.MPI_SOURCE);
			sending_id++;
		}
		else {
			cout << "sending stop message to computing process " << current_status.MPI_SOURCE << endl;
			cout << "total_processed_wus : " << total_processed_wus << endl;
			MPI_Send(&stop_mes, 1, MPI_INT, current_status.MPI_SOURCE, 0, MPI_COMM_WORLD);
		}
		// write results to a file not more often than every 100 seconds
		if ((result_writing_time < 0) || (MPI_Wtime() - result_writing_time > REPORT_EVERY_SEC)) {
			writeInfoOutFile(control_process_ofile_name, wu_vec, start_time);
			writeProcessingInfo(wu_vec);
			result_writing_time = MPI_Wtime();
		}
	}
	
	writeInfoOutFile(control_process_ofile_name, wu_vec, start_time);
	cout << "control process finished" << endl;

	writeProcessingInfo(wu_vec);

	string inter_cubes_file_name = "!interrupted_" + cubes_file_name;
	inter_cubes_file_name.erase(remove(inter_cubes_file_name.begin(), inter_cubes_file_name.end(), '.'), inter_cubes_file_name.end());
	inter_cubes_file_name.erase(remove(inter_cubes_file_name.begin(), inter_cubes_file_name.end(), '/'), inter_cubes_file_name.end());
	ofstream inter_cubes_file(inter_cubes_file_name);
	for (auto &cur_wu : wu_vec) {
		/*if (cur_wu.status != PROCESSED) {
			cerr << "cur_wu.status != PROCESSED" << endl;
			MPI_Abort(MPI_COMM_WORLD, 0);
		}*/
		if (cur_wu.result == INDET) {
			inter_cubes_file << "a ";
			for (auto lit : cur_wu.cube)
				inter_cubes_file << lit << " ";
			inter_cubes_file << "0" << endl;
		}
	}
	inter_cubes_file.close();

	// Delete temporary files:
	std::string system_str = "rm ./id-*";
	exec(system_str);
	system_str = "rm ./out_process_*";
	exec(system_str);

	if (is_SAT and not is_enum) {
		MPI_Abort(MPI_COMM_WORLD, 0);
		exit(1);
	}
	
	MPI_Finalize();
}

void sendWU(vector<wu> &wu_vec, const int wu_id, const int computing_process_id)
{
	MPI_Send(&wu_id, 1, MPI_INT, computing_process_id, 0, MPI_COMM_WORLD);
	wu_vec[wu_id].status = IN_PROGRESS;
}

void writeInfoOutFile(const string control_process_ofile_name, vector<wu> wu_vec, const double start_time)
{
	double min_solving_time_unsat = 1e+308;
	double max_solving_time_unsat = -1;
	double avg_solving_time_unsat = -1;
	double sum_time_unsat = 0.0;
	int k = 0;
	int sat_cubes = 0;
	int unsat_cubes = 0;
	int indet_cubes = 0;
	for (auto cur_wu : wu_vec) {
		if (cur_wu.status != PROCESSED)
			continue;
		k++;
		if (cur_wu.result == UNSAT) {
			unsat_cubes++;
			max_solving_time_unsat = cur_wu.processing_time > max_solving_time_unsat ? cur_wu.processing_time : max_solving_time_unsat;
			min_solving_time_unsat = cur_wu.processing_time < min_solving_time_unsat ? cur_wu.processing_time : min_solving_time_unsat;
			sum_time_unsat += cur_wu.processing_time;
		}
		else if (cur_wu.result == INDET)
			indet_cubes++;
		else if (cur_wu.result == SAT) {
			sat_cubes++;
			string ofile_name = "!sat_cube_id_" + intToStr(cur_wu.id);
			ofstream ofile(ofile_name, ios_base::out);
			
			ofile << "SAT" << endl;
			ofile << "time : " << cur_wu.processing_time << " s" << endl;
			ofile << "cube id : " << cur_wu.id << endl;
			ofile << "cube : " << endl;
			for (auto &x : cur_wu.cube)
				ofile << x << " ";
			ofile << endl;
			ofile.close();
		}
	}
	if (k != total_processed_wus) {
		cerr << "k != total_processed_wus" << endl;
		cerr << k << " != " << total_processed_wus << endl;
		MPI_Abort(MPI_COMM_WORLD, 0);
		exit(-1);
	}
	if (sum_time_unsat > 0)
		avg_solving_time_unsat = sum_time_unsat / unsat_cubes;
	
	double percent_val;
	ofstream control_process_ofile(control_process_ofile_name, ios_base::app);
	control_process_ofile << endl << "***" << endl;
	control_process_ofile << "elapsed time : " << MPI_Wtime() - start_time << endl;
	control_process_ofile << "total WUs : " << wu_vec.size() << endl;
	percent_val = double(total_processed_wus * 100) / (double)wu_vec.size();
	control_process_ofile << "total_processed_wus : " << total_processed_wus
		<< ", i.e. " << percent_val << " %" << endl;
	control_process_ofile << "sat_cubes : " << sat_cubes << endl;
	control_process_ofile << "indet_cubes : " << indet_cubes << endl;
	control_process_ofile << "unsat_cubes : " << unsat_cubes << endl;
	control_process_ofile << "min_solving_time_unsat : " << min_solving_time_unsat << endl;
	control_process_ofile << "max_solving_time_unsat : " << max_solving_time_unsat << endl;
	control_process_ofile << "avg_solving_time_unsat : " << avg_solving_time_unsat << endl;
	control_process_ofile << endl;
	control_process_ofile.close();
}

string exec(const string cmd_str)
{
	string result = "";
	char* cmd = new char[cmd_str.size() + 1];
	for (unsigned i = 0; i < cmd_str.size(); i++)
		cmd[i] = cmd_str[i];
	cmd[cmd_str.size()] = '\0';
	FILE* pipe = popen(cmd, "r");
	delete[] cmd;
	if (!pipe) return "ERROR";
	char buffer[128];
	while (!feof(pipe)) {
		if (fgets(buffer, 128, pipe) != NULL)
			result += buffer;
	}
	pclose(pipe);
	return result;
}

int getResultFromFile(const string out_name)
{
	ifstream out_file(out_name);
	string str;
	int result = INDET;
	while (getline(out_file, str)) {
		if ((str.find("s SATISFIABLE") != string::npos) || (str.find("SATISFIABLE") == 0)) {
			result = SAT;
			break;
		}
		else if ((str.find("s UNSATISFIABLE") != string::npos) || (str.find("UNSATISFIABLE") == 0)) {
			result = UNSAT;
			break;
		}
		/*if (str.find("c CPU time") != string::npos) {
			stringstream sstream;
			sstream << str;
			vector<string> vec;
			string word;
			while (sstream >> word)
				vec.push_back(word);
			if (vec.size() < 5) {
				cerr << "error : vec size " << vec.size() << endl;
				MPI_Abort(MPI_COMM_WORLD, 0);
				exit(-1);
			}
			//istringstream(vec[4]) >> time;
		}*/
	}
	out_file.close();
	/*if (time == -1) {
		cerr << "solving time == -1" << endl;
		cerr << endl;
		MPI_Abort(MPI_COMM_WORLD, 0);
		exit(-1);
	}*/
	return result;
}

void computingProcess(const int rank, const string solver_file_name, const string cnf_file_name,
		      const string cubes_file_name, const string cube_cpu_lim_str, const string param_str)
{
	vector<wu> wu_vec = readCubes(cubes_file_name);
	
	stringstream cnf_sstream;
	ifstream cnf_file(cnf_file_name);
	string str;
	unsigned cnf_main_clauses = 0;
	unsigned cnf_main_variables = 0;
	while (getline(cnf_file, str)) {
		if ((str.size() == 0) || (str[0] == 'p') || (str[0] == 'c'))
			continue;
		cnf_sstream << str << endl;
		cnf_main_clauses++;
		stringstream sstream;
		sstream << str;
		vector<int> vec;
		int ival;
		while (sstream >> ival) {
			int abs_ival = abs(ival);
			cnf_main_variables = (abs_ival > cnf_main_variables) ? abs_ival : cnf_main_variables;
		}
	}
	cnf_file.close();
	
	/*string base_path = exec("echo $PWD");
	base_path.erase(remove(base_path.begin(), base_path.end(), '\r'), base_path.end());
	base_path.erase(remove(base_path.begin(), base_path.end(), '\n'), base_path.end());
	solver_file_name = base_path + "/" + solver_file_name;
	cnf_file_name = base_path + "/" + cnf_file_name;*/
	
	MPI_Status status;
	int wu_id = -1;
	for (;;) {
		MPI_Recv( &wu_id,    1, MPI_INT,  0, 0, MPI_COMM_WORLD, &status );
		//cout << "received wu_id " << wu_id << endl;
		if (wu_id == -1) {// stop message
			cout << "computing prosess " << rank << " got the stop message" << endl;
			break;
		}

		string wu_id_str = intToStr(wu_id);
		string tmp_cnf_file_name = "id-" + wu_id_str + "-cnf";
		
		stringstream cube_sstream;
		for (auto x : wu_vec[wu_id].cube)
			cube_sstream << x << " 0" << endl;
		
		ofstream tmp_cnf(tmp_cnf_file_name, ios_base::out);
		tmp_cnf << "p cnf " << cnf_main_variables << " " << cnf_main_clauses + wu_vec[wu_id].cube.size() << endl;
		tmp_cnf << cnf_sstream.str();
		tmp_cnf << cube_sstream.str();
		tmp_cnf.close();
		
		string system_str;
		if (solver_file_name.find(".sh") != string::npos) {
			// cube_cpu_lim_str is used as cpu-lim for an incremental SAT solver
			system_str = solver_file_name + " " + tmp_cnf_file_name + " " + wu_id_str + " " + cube_cpu_lim_str;
		}
		else {
			system_str = "./timelimit -t " + cube_cpu_lim_str + " -T 1 " + solver_file_name;
			if (param_str != "")
			    system_str += " " + param_str;
			system_str += " " + tmp_cnf_file_name;
		}
		//if (rank == 1)
		//	cout << system_str << endl;
		string rank_str = intToStr(rank);
		string out_name = "./out_process_" + rank_str;
		fstream out_file;
		out_file.open(out_name, ios_base::out);
		double elapsed_solving_time = MPI_Wtime();
		out_file << exec(system_str);
		elapsed_solving_time = MPI_Wtime() - elapsed_solving_time;
		out_file.close();
		out_file.clear();
		int res = INDET;
		double cube_cpu_lim = -1.0;
		istringstream(cube_cpu_lim_str) >> cube_cpu_lim;
		res = getResultFromFile(out_name);
		// remove the temporary cnf file
		if (res == SAT) {
			system_str = "cp " + out_name + " ./!sat_out_id_" + wu_id_str;
			exec(system_str);
			system_str = "cp " + tmp_cnf_file_name + " ./!sat_cnf_" + tmp_cnf_file_name;
			exec(system_str);
		}
		else if (elapsed_solving_time > cube_cpu_lim + 60.0) {
			system_str = "cp " + out_name + " ./!extra_time_out_id_" + wu_id_str;
			exec(system_str);
		}
		else {
			system_str = "rm ./id-" + wu_id_str + "-*";
			exec(system_str);
			system_str = "rm " + out_name;
			exec(system_str);
		}

		// send calculated result to the control process
		//cout << "sending wu_id " << wu_id << endl;
		//cout << "sending res " << res << endl;
		MPI_Send( &wu_id, 1, MPI_INT,    0, 0, MPI_COMM_WORLD);
		MPI_Send( &res,   1, MPI_INT,    0, 0, MPI_COMM_WORLD);
		MPI_Send( &elapsed_solving_time,  1, MPI_DOUBLE, 0, 0, MPI_COMM_WORLD);
	}
	MPI_Finalize();
}


void writeProcessingInfo(vector<wu> &wu_vec)
{
	ofstream ofile("!processing_info");
	ofile << "cube_id cube_result cube_time" << endl;
	for (auto &cur_wu : wu_vec)
		ofile << cur_wu.id << " " << cur_wu.result << " " << cur_wu.processing_time << endl;
	ofile.close();
	ofile.clear();
}
