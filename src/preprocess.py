#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2021 Priyanka Golia, Subhajit Roy, and Kuldeep Meel

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in
all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
THE SOFTWARE.
'''




import tempfile
from subprocess import Popen, PIPE, check_output
import signal
import os
import numpy as np
import networkx as nx

def parse(args):
	with open(args.input) as f:
		lines = f.readlines()
	f.close()

	'''
	Xvar is universally quantified variables
	Yvar is existentially quantified variables

	For DQBF 
	H{} presents Henkin Dependencies
	H[y_i] = [x_1, \ldots,x_a] where x_1,\ldots x_a \subseteq X
	
	'''

	Xvar = []
	Yvar = []
	HenkinDep = {} # for DQBF: it presents variables with explict dependencies.
	qdimacs_list = []

	for line in lines:
		if line.startswith("c"):
			continue
		if (line == "") or (line == "\n"):
			continue
		
		if line.startswith("p"):
			continue
		
		if line.startswith("a"):
			Xvar += line.strip("a").strip("\n").strip(" ").split(" ")[:-1]
			
			continue
		
		if line.startswith("e"):
			Yvar += line.strip("e").strip("\n").strip(" ").split(" ")[:-1]
			continue

		if line.startswith("d"):
			YDep = line.strip("d").strip("\n").strip(" ").split(" ")[:-1]
			dvar = int(YDep[0])
			Yvar.append(dvar)
			HenkinDep[dvar] = list(map(int, list(YDep[1:])))
			continue

		clause = line.strip(" ").strip("\n").strip(" ").split(" ")[:-1]

		if len(clause) > 0:
			clause = list(map(int, list(clause)))
			qdimacs_list.append(clause)

	if (len(Xvar) == 0) or (len(Yvar) == 0) or (len(qdimacs_list) == 0):
		print("problem with the files, can not synthesis Skolem functions")
		exit()
	
	
	
	Yvar = list(map(int, list(Yvar)))
	Xvar = list(map(int, list(Xvar)))
	
	dg = nx.DiGraph()  # dag to handle dependencies

	for yvar in Yvar:
		dg.add_node(yvar)

	if args.henkin:

		for yvar_i in Yvar:
			for yvar_j in Yvar:

				if yvar_j not in list(HenkinDep.keys()):
					HenkinDep[yvar_j] = Xvar

				if (yvar_i != yvar_j) and (set(HenkinDep[yvar_j]).issubset(set(HenkinDep[yvar_i]))):
					
					if not dg.has_edge(yvar_j,yvar_i):
						dg.add_edge(yvar_i, yvar_j)
		
		return Xvar, Yvar, HenkinDep, qdimacs_list, dg
	
	else:
		return Xvar, Yvar, qdimacs_list, dg


def convertcnf(args, cnffile_name, Yvar = []):


	with open(args.input,"r") as f:
		cnfcontent = f.read()
	f.close()

	cnfcontent = cnfcontent.replace("a ", "c ret ")

	if args.henkin:
		dvar_str = "c ind "
		for yvar in Yvar:
			dvar_str += str(yvar)+" "
		dvar_str += "0\n"

		cnfcontent = cnfcontent.replace("e ", "c e")
		cnfcontent = cnfcontent.replace("d ", "c d")
		cnfcontent = cnfcontent.replace("c ret", dvar_str+"c ret")
		

	else:

		cnfcontent = cnfcontent.replace("e ", "c ind ")

	with open(cnffile_name,"w") as f:
		f.write(cnfcontent)
	f.close()

	return cnfcontent


def preprocess(cnffile_name):

	'''
	Preprocess calls Cryptominisat Based framework to find 
	positive and negative unates.
	'''

	cmd = "./dependencies/preprocess %s " % (cnffile_name)
	with Popen(cmd, shell=True, stdout=PIPE, preexec_fn=os.setsid) as process:
		try:
			output = process.communicate(timeout=500)[0]
		except Exception:
			os.killpg(process.pid, signal.SIGINT)
			PosUnate = []
			NegUnate = []
			print("timeout preprocessing..")
			return PosUnate, NegUnate
		else:
			PosUnate = []
			NegUnate = []
			exists = os.path.isfile(cnffile_name + "_vardetails")
			if exists:
				with open(cnffile_name + "_vardetails", 'r') as f:
					lines = f.readlines()
				f.close()

				for line in lines:
					if "Posunate" in line:
						pos = line.split(":")[1].strip(" \n")
						if pos != "":
							PosUnate = list(map(int, list(pos.split(" "))))
						continue
					if "Negunate" in line:
						neg = line.split(":")[1].strip(" \n")
						if neg != "":
							NegUnate = list(map(int, list(neg.split(" "))))
						continue
				os.unlink(cnffile_name + "_vardetails")
			else:
				print("preprocessing error .. contining ")
				exit()
			return PosUnate, NegUnate




