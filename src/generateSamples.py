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


def computeBias(Yvar,sampling_cnf, sampling_weights_y_1, sampling_weights_y_0, inputfile_name, SkolemKnown, args):

	
	
	samples_biased_one = generatesample( args, 500, sampling_cnf + sampling_weights_y_1, inputfile_name)
	samples_biased_zero = generatesample( args, 500, sampling_cnf + sampling_weights_y_0, inputfile_name)

	if args.verbose >=2:
		print(" c generated samples to predict bias for Y")
		print(" c biased towards one", len(samples_biased_one))
		print(" c biased towards zero", len(samples_biased_zero))

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
	
	if args.verbose >= 2:
		print(" c bias computing", bias)
	
	return sampling_cnf + bias
		





def generatesample(args, num_samples, sampling_cnf, inputfile_name):

	
	tempcnffile = tempfile.gettempdir() + '/' + inputfile_name + "_sample.cnf"


	assert(sampling_cnf!="")

	with open (tempcnffile,"w") as f:
		f.write(sampling_cnf)
	f.close()



	tempoutputfile = tempfile.gettempdir() + '/' + inputfile_name + "_.txt"


	cmd =  "./dependencies/cmsgen %s --samplefile %s " %(tempcnffile, tempoutputfile)
	cmd += "--seed %s --samples %s " %(args.seed, int(num_samples))
	

	if args.verbose >= 2:
		print(" c cmsgen cmd", cmd)
		print(" c tempcnffile", tempcnffile)
		print(" c tempoutputfile", tempoutputfile)
		print(" c sampling cnf", sampling_cnf)
	else:
		cmd += "> /dev/null 2>&1"
	
	
	os.system(cmd)

	if args.verbose >= 2:
		print(" c generated samples at %s", tempoutputfile)

	if os.path.exists(tempoutputfile):

		with open(tempoutputfile,"r") as f:
			content = f.read()

		os.unlink(tempoutputfile)
		os.unlink(tempcnffile)

	else:

		print(" c some issue while generating samples..please check your sampler")
		exit()

	
	content = content.replace("SAT\n","").replace("\n"," ").strip(" \n").strip(" ")
	models = content.split(" ")
	models = np.array(models)

	if args.verbose >= 2:
		print(" c models", models)
	
	if models[len(models)-1] != "0":
		models = np.delete(models, len(models) - 1, axis=0)

	if args.verbose >= 2:
		print(" c models after delete", models)

	assert(len(models) > 0)

	if args.verbose >= 2:
		print("c check for np.where", np.where(models == "0"))


	
	if len(np.where(models == "0")[0]) > 0:

		if args.verbose >= 2:
			print("c was able to go inside where condition")
		
		index = np.where(models == "0")[0][0]
		var_model = np.reshape(models, (-1, index+1)).astype(np.int_)

		if args.verbose >= 2:
			print("c was able to go reshape")

		var_model = var_model > 0
		var_model = np.delete(var_model, index, axis=1)
		var_model = var_model.astype(np.int_)
	
		if args.verbose >= 2:
			print("c var_models first row", var_model[0])
	
	return var_model
