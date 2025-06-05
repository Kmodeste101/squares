#!/usr/bin/python3
"""
Created on Tue Mar 4 10:15 2025
@author: modestekatotoka
"""
import numpy as np
import time
import sys
import math
import csv
import numpy as np
from math import sqrt
import matplotlib.pyplot as plt

#load COMSOL xscan_comsol.txt data

fx='xscan_comsol.txt'
fy='yscan_comsol.txt'
fz='zscan_comsol.txt'

#files=[fx,fy,fz]

data_com=np.loadtxt(fx,comments='%',skiprows=6)
pos_com=data_com[:,0] # in m

bx_com=data_com[:,3]*3*(10**9)
by_com=data_com[:,4]*3*(10**9)
bz_com=data_com[:,5]*3*(10**9)#nT
#print(by_com)

#meta data for theoretical field
import json
with open('data.json') as json_file:
    graphdata=json.load(json_file)

#reading in gradient data:
data= np.loadtxt('May28_2.0.csv', delimiter=',', skiprows=19, usecols=(1,2,3,7))
print(data)
bx=data[:,0]
by=data[:,1]
bz=data[:,2]


positions=data[:,3]

pos=[]
bx_ave=[]
by_ave=[]
bz_ave=[]

for i in range(0, len(bx)-1, 2):  # Start at 0, stop at len(bx)-1, step by 2
    try:
        is_length_same=len(bx)==len(by)==len(bz)
        print('prepare for averaging...',)
    except: ValueError
    
    x_ave=(bx[i+1] - bx[i]) / 2
    y_ave=(by[i+1] - by[i]) / 2
    z_ave=(bz[i+1] - bz[i]) / 2
    
    bx_ave=np.append(bx_ave,x_ave)
    by_ave=np.append(by_ave,y_ave)
    bz_ave=np.append(bz_ave,z_ave)
    
for i in range(0, len(positions), 2): 
    pos_metres=positions[i]*(0.01) #in metres
    pos=np.append(pos,pos_metres)
    
bx_meas=bx_ave*(100/10) #field(nT)=field(V)*(100 nT/10 V)
by_meas=by_ave*(100/10)
bz_meas=bz_ave*(100/10)


# Load COMSOL G10 xscan

data_com= np.loadtxt('xscan_comsol.txt',delimiter=None,comments='%',skiprows=6)

pos_com_x=data_com[:,0] # in m
bx_com_x=data_com[:,3]*3*(10**9)
by_com_x=data_com[:,4]*3*(10**9)
bz_com_x=data_com[:,5]*3*(10**9)#nT

'''
scanning direction along x-axis

fluxgate z-axis direction =  x direction in simulation
fluxgate minus y-axis direction =  y-axis direction in simulation
fluxgate x-axis direction =  posi z-axis direction in simulation
'''

#Graphing here

#msr measurement for gradient:
plt.figure(1)

plt.scatter(-pos,bz_meas,color="b",label="$B_x(x,0,0)$",marker='.')
plt.scatter(-pos,-by_meas,color="r",label="$B_y(x,0,0)$",marker='.')
plt.scatter(-pos,bx_meas,color="g",label="$B_z(x,0,0)$",marker='.')

ax=plt.gca()
h,l=ax.get_legend_handles_labels()
ph=[plt.plot([],marker="", ls="")[0]]
handles=[ph[0]]+h[0:3]
labels=[r'\underline{Measured}']+l[0:3]

plt.rc('text',usetex=True)

ax.set_xlabel(f'x(m)')
ax.set_ylabel('magnetic field (T)')
#plt.xlabel("Position along $x$-axis (m)")
#plt.xlim([-1.1,1.1])
#plt.ylim([-35,35])
#plt.ylabel("Magnetic Field (nT)")
plt.legend(handles, labels, ncol=1, fontsize=14)

plt.savefig("gradient_map.png",dpi=300,bbox_inches='tight')

plt.show()

#comparison to models

plt.figure(2)

plt.scatter(-pos,bz_meas,color="b",label="$B_x(x,0,0)$",marker='.')
plt.scatter(-pos,-by_meas,color="r",label="$B_y(x,0,0)$",marker='.')
plt.scatter(-pos,bx_meas,color="g",label="$B_z(x,0,0)$",marker='.')


#COMSOL result

plt.plot(pos_com_x,bx_com_x,color="b",label="$B_x(x,0,0)$")
plt.plot(pos_com,by_com_x,color="r",label='$By(x,0,0)$')
plt.plot(pos_com,bz_com_x,color="g",label='$Bz(x,0,0) $')


ax=plt.gca()
h,l=ax.get_legend_handles_labels()
ph=[plt.plot([],marker="", ls="")[0]]*2
handles=[ph[0]]+h[0:3]+[ph[1]]+h[3:6]
labels=[r'\underline{Measured}']+l[0:3]+[r"\underline{COMSOL}"]+l[3:6]

ax.axvline(x=2.2/2,color='black',linestyle='--')
ax.axvline(x=-2.2/2,color='black',linestyle='--')
ax.axvline(x=0.5/2,color='red',linestyle='--')
ax.axvline(x=-0.5/2,color='red',linestyle='--')

plt.rc('text',usetex=True)
plt.xlabel("x(m)")
plt.ylabel("Magnetic Field (nT)")


plt.legend(handles, labels, ncol=2)
plt.savefig("gradient_com.png",dpi=300)

plt.show()

