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
import subprocess
from src import runtime_env  # noqa: F401
from src.logging_utils import cprint


def computeBias(Xvar,Yvar,sampling_cnf, sampling_weights_y_1, sampling_weights_y_0, inputfile_name, SkolemKnown, args):
	try:
		samples_biased_one = generatesample( args, 500, sampling_cnf + sampling_weights_y_1, inputfile_name, 1)
		samples_biased_zero = generatesample( args, 500, sampling_cnf + sampling_weights_y_0, inputfile_name, 1)
	except RuntimeError as exc:
		cprint("c [computeBias] adaptive bias sampling failed, using default weights")
		if args.verbose >= 2:
			cprint("c [computeBias] adaptive bias sampling error:", exc)
		return sampling_cnf + sampling_weights_y_1

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
	with tempfile.TemporaryDirectory(prefix="manthan_cmsgen_") as tmpdir:
		tempcnffile = os.path.join(tmpdir, "sample.cnf")
		tempoutputfile = os.path.join(tmpdir, "samples.out")

		with open(tempcnffile, "w") as f:
			f.write(sampling_cnf)
		f.close()

		cmsgen = "./dependencies/static_bin/cmsgen"
		if not os.path.isfile(cmsgen):
			cmsgen = "./dependencies/cmsgen"
		cmsgen = os.path.abspath(cmsgen)
		cmd = [cmsgen, "--samples", str(int(num_samples)),
		       "-s", str(args.seed), "--samplefile", "samples.out", "sample.cnf"]
		subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		if not os.path.isfile(tempoutputfile):
			raise RuntimeError("sample generation failed: %s" % (" ".join(cmd)))

		with open(tempoutputfile, "r") as f:
			content = f.read()
		f.close()
	content = content.replace("SAT\n","").replace("\n"," ").strip(" \n").strip(" ")
	models = content.split(" ")
	models = np.array(models)
	if models[len(models)-1] != "0":
		models = np.delete(models, len(models) - 1, axis=0)
	if len(np.where(models == "0")[0]) > 0:
		index = np.where(models == "0")[0][0]
		var_model = np.reshape(models, (-1, index+1)).astype(int)
		var_model = var_model > 1
		var_model = np.delete(var_model, index, axis=1)
		var_model = var_model.astype(int)
	return var_model
