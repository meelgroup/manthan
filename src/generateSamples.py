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
import numpy as np
from numpy import count_nonzero
import os


def computeBias(Xvar,Yvar,sampling_cnf, sampling_weights_y_1, sampling_weights_y_0, inputfile_name, SkolemKnown, args):
	samples_biased_one = generatesample( args, 500, sampling_cnf + sampling_weights_y_1, inputfile_name, 1)
	samples_biased_zero = generatesample( args, 500, sampling_cnf + sampling_weights_y_0, inputfile_name, 1)

	bias = ""

	for yvar in Yvar:
		if yvar in SkolemKnown:
			continue
		count_one = count_nonzero(samples_biased_one[:,yvar-1])
		p = round(float(count_one)/500,2)

		count_zero = count_nonzero(samples_biased_zero[:,yvar-1])
		q = round(float(count_zero)/500,2)

		if 0.35 < p < 0.65 and 0.35 < q < 0.65:
			bias += "w %s %s\n" %(yvar,p)
		elif q <= 0.35:
			if float(q) == 0.0:
				q = 0.001
			bias += "w %s %s\n" %(yvar,q)
		else:
			if float(p) == 1.0:
				p = 0.99
			bias += "w %s %s\n" %(yvar,p)
	
	return sampling_cnf + bias
		





def generatesample(args, num_samples, sampling_cnf, inputfile_name, weighted):
	tempcnffile = tempfile.gettempdir() + '/' + inputfile_name + "_sample.cnf"
	with open (tempcnffile,"w") as f:
		f.write(sampling_cnf)
	f.close()

	tempoutputfile = tempfile.gettempdir() + '/' + inputfile_name + "_.txt"

	if weighted:
		cmd = "./dependencies/cryptominisat5 -n1 --sls 0 --comps 0"
		cmd += " --restart luby  --nobansol --maple 0 --presimp 0"
		cmd += " --polar weight --freq 0.9999 --verb 0 --scc 0"
		cmd += " --random %s --maxsol %s > /dev/null 2>&1" % (args.seed, int(num_samples))
		cmd += " %s" % (tempcnffile)
		cmd += " --dumpresult %s " % (tempoutputfile)
	else:
		cmd = "./dependencies/cryptominisat5 --restart luby"
		cmd += " --maple 0 --verb 0 --nobansol"
		cmd += " --scc 1 -n1 --presimp 0 --polar rnd --freq 0.9999"
		cmd += " --random %s --maxsol %s" % (args.seed, int(num_samples))
		cmd += " %s" % (tempcnffile)
		cmd += " --dumpresult %s > /dev/null 2>&1" % (tempoutputfile)
	
	os.system(cmd)

	with open(tempoutputfile,"r") as f:
		content = f.read()
	f.close()
	os.unlink(tempoutputfile)
	os.unlink(tempcnffile)
	content = content.replace("SAT\n","").replace("\n"," ").strip(" \n").strip(" ")
	models = content.split(" ")
	models = np.array(models)
	if models[len(models)-1] != "0":
		models = np.delete(models, len(models) - 1, axis=0)
	if len(np.where(models == "0")[0]) > 0:
		index = np.where(models == "0")[0][0]
		var_model = np.reshape(models, (-1, index+1)).astype(np.int_)
		var_model = var_model > 0
		var_model = np.delete(var_model, index, axis=1)
		var_model = var_model.astype(np.int_)
	return var_model
