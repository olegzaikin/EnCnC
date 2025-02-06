# Created on: 6 Feb 2025
# Author: Oleg Zaikin
# E-mail: zaikin.icc@gmail.com
#
# Collect final total cubes made by autom_constr_gen_crypt_hash.py
#==============================================================================

import glob

version = '0.0.1'
script_name = 'collect_total_cubes.py'

# Main function:
if __name__ == '__main__':
    log_lst = glob.glob('log_*')
    print(str(len(log_lst)) + ' files with logs')

    cubes = []
    # Total cube : -6902 -6900 -6898
    for log in log_lst:
        print('Processing log ' + log)
        with open(log, 'r') as f:
            lines = f.read().splitlines()
            for line in lines:
                if 'Total cube : ' in line:
                    literals = line.split('Total cube : ')[1].split()
                    print(str(len(literals)) + ' literals in total cube')
                    for i in range(1, len(literals)+1):
                        cube = []
                        for j in range(0, i):
                            assert(j < len(literals))
                            cube.append(literals[j])
                        cubes.append(cube)
                    # Collect reversed cubes:
                    literals.reverse()
                    for i in range(1, len(literals)+1):
                        cube = []
                        for j in range(0, i):
                            assert(j < len(literals))
                            cube.append(literals[j])
                        cubes.append(cube)
    print(str(len(cubes)) + ' cubes were made')

    print('Writing to file cubes')
    with open('cubes', 'w') as f:
        for cube in cubes:
            s = ''
            for x in cube:
                s += x + ' '
            f.write(s[:-1] + '\n')
