#!/usr/bin/env python

from __future__ import division
import sys, os
import numpy as np
import readnew
from glob import glob

import yaml
import os.path
import time # Need to wait some time if file is being written
import argparse
import pandas as pd

parser = argparse.ArgumentParser(description =
    """
        This script functions by reading in yaml files from a given directory
        and comparing with a given reference .DAT file. The heat capacity
        is computed and compared to the reference.
        
        EXAMPLE USAGE:
        python3 scripts-python/ising-cv-save-csv.py
        --file_dir=../ising-cp-data/
        --reference=../deft/papers/histogram/data/ising-32-reference-lndos.dat
        --save_dir=ising/data/heat-capacity
        --filename ising-sad-32
        --N=32
        --Emin=2048
        --Emax=0
        --seed_avg=1
    """)

parser.add_argument('--file_dir', required=True,
                    help='The directory where the files are located. \
                          Example:/home/jordan/ising-cp-data/')
parser.add_argument('--reference', required=True,
                    help='The directory where the reference file is located. \
                          Exmaple:data/ising-32-reference-lndos.dat')
parser.add_argument('--save_dir', required=True,
                    help='The directory where the data will be saved. \
                          Exmaple:data/comparison/N32')
parser.add_argument('--N', type=int, required=True,
                    help='The length of the ising model. Used to divide \
                          the number of moves.')
parser.add_argument('--Emin', type=int, required=True,
                    help='The energy at the entropy minimum.')
parser.add_argument('--Emax', type=int, required=True,
                    help='The energy at the entropy maximum.')
parser.add_argument('--seed_avg', type=int, required=True,
                    help='The number of seed files to average over.')
parser.add_argument('--filename', required=True, nargs='+',
                    help='The filename to perform analysis on. \
                          Exmaple:ising-sad-32')

args = parser.parse_args()

# Rename all argparse parameters.
file_dir = args.file_dir
ref = args.reference
save_dir = args.save_dir
N = args.N
Emin = args.Emin
Emax = args.Emax
seed_avg = args.seed_avg

# The correct way to handle accepting multiple arguments using nargs
# to create a list.
# '+' == 1 or more.
# '*' == 0 or more.
# '?' == 0 or 1.
filename = args.filename

def heat_capacity(T, E, S):
    """
        This function calculates the heat capacity by taking in
        the temperature 'T', energy 'E', and entropy 'S' as NumPy
        arrays.  The number 'Num' is also necessary to complete
        the heat capacity calculation.
    """
    C = np.zeros_like(T)
    for i in range(len(T)):
        boltz_arg = S - E/T[i]
        P = np.exp(boltz_arg - boltz_arg.max())
        P = P/P.sum()
        U = (E*P).sum()
        C[i] = ((E-U)**2*P).sum()/T[i]**2
    return C

T = np.arange(1.5, 5, 0.01)

# Compute the reference energy, entropy, and heat capacity once.
try:
    eref, lndosref, Nrt_ref = readnew.e_lndos_ps(ref)
except:
    eref, lndosref = readnew.e_lndos(ref)

#cvref = heat_capacity(T, eref, lndosref)
cvref = heat_capacity(T, eref[0:Emin-Emax+1], lndosref[0:Emin-Emax+1])

# form a dictionary to place into a pandas dataframe.
mydictionary = {'Temperature': T,
	'cvref': cvref,}
df = pd.DataFrame(mydictionary)

for f in filename:
    name = '%s.yaml' % (f)

    for n in range(1, seed_avg+1):
        #try:
            name = '%s-s%s.yaml' % (f, n)
            print(('trying filename ', name))

            # Read YAML file
            if os.path.isfile(file_dir + name):
                with open(file_dir + name, 'r') as stream:
                    yaml_data = yaml.load(stream)
            else:
                print(('unable to read file', file_dir + name))
                raise ValueError("%s isn't a file!" % (file_dir + name))

            data = yaml_data
            # data['bins']['histogram'] = np.array(data['bins']['histogram'])
            # data['bins']['lnw'] = np.array(data['bins']['lnw'])

            # data['movies']['entropy'] = np.array(data['movies']['entropy'])
            lndos = data['movies']['entropy']
            energies = data['movies']['energy']
            my_time = np.array(data['movies']['time'])
            try:
                maxyaml = energies.index(-Emin)
            except:
                my_minE = energies[0]
                num_new_energies = int(my_minE - (-Emin))
                print(('num_new_maxyaml', num_new_energies))
                lndos_new = np.zeros((lndos.shape[0], lndos.shape[1]+num_new_energies))
                lndos_new[:, num_new_energies:] = lndos[:,:]
                lndos = lndos_new
                energies = [0]*num_new_energies + energies
                maxyaml = 0

            try:
                minyaml = energies.index(-Emax)
            except:
                my_maxE = energies[-1]
                num_new_energies = -int(my_maxE - (-Emax))
                print(('num_new_minyaml', num_new_energies))
                lndos_new = np.zeros((lndos.shape[0], lndos.shape[1]+num_new_energies))
                lndos_new[:, :lndos.shape[1]] = lndos[:,:]
                lndos = lndos_new
                minyaml = lndos.shape[1]-1

            
            times = [1000000000, 1333521432, 1778279410,2371373716,3162277660, 4216965034, 5623413252, 7498942093]
            index = np.argwhere(my_time == times[0])[0][0]
            # below just set average S equal between lndos and lndosref
            if 'ising' in save_dir:
                
                ising_lndos = np.flip(np.copy(lndos[index][maxyaml:minyaml+1])) # remove impossible state
                # the states are counted backward hence the second to last state would be at index = 1
                ising_lndos = np.delete(ising_lndos, [len(ising_lndos)-2])
                
                # invoke np.flip since ising_E and ising_lndos are indexed backward!
                # this is critical for my_cv_error or you get wrong answer.
                ising_E = np.flip(np.copy(energies[maxyaml:minyaml+1]))
                ising_E = np.delete(ising_E, [len(ising_E)-2])

                my_cv = heat_capacity(T, ising_E, ising_lndos)
                        
                # add column
                df['%s' % f] = my_cv
                print('\n\nDataFrame after adding "%s" column\n--------------' % f)
                print(df.head(10))
            else:
                print('Error! ising must be in save_dir pathname.')


print('saving to', save_dir)
try:
    os.mkdir(save_dir)
except OSError:
    pass
else:
    print("Successfully created the directory %s " % save_dir)

# opening the file with w+ empties the file I am creating
open(('%s/N%s-heat-capacity.csv' % (save_dir, N)), "w+").close()


df.to_csv(('%s/N%s-heat-capacity.csv' % (save_dir, N)), sep='\t', encoding='utf-8', index=False, mode='a')

# # Begin plotting the heat capacity
# plt.figure('heat capacity plot')
# colors.plot(1/T, cvref / N**2, method='cvref')

#             colors.plot(1/T, my_cv / N**2, method='%s' % (name.replace('-s%s.yaml' %seed_avg, '')))
#             colors.legend(loc='best')

# #print(cv_store)
# plt.xlabel(r'$\beta$')
# plt.ylabel(r'$c_V$ / $ k_B$')
# plt.xlim(0.3,0.6)
# if N == 32:
#     plt.ylim(0,2.5)

# plt.savefig('ising/N%i-Cv.pdf' % N)

# plt.show()