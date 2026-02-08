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
import shutil
import subprocess
from src import runtime_env  # noqa: F401
from src.logging_utils import cprint
import psutil


def computeBias(Xvar,Yvar,sampling_cnf, sampling_weights_y_1, sampling_weights_y_0, inputfile_name, SkolemKnown, args):
	try:
		samples_biased_one = generatesample( args, 500, sampling_cnf + sampling_weights_y_1, inputfile_name, 1)
		samples_biased_zero = generatesample( args, 500, sampling_cnf + sampling_weights_y_0, inputfile_name, 1)
	except RuntimeError as exc:
		cprint("c [computeBias] adaptive bias sampling failed, using default weights")
		if args.verbose >= 2:
			cprint("c [computeBias] adaptive bias sampling error:", exc)
		return sampling_cnf + sampling_weights_y_1
	if samples_biased_one.size == 0 or samples_biased_zero.size == 0:
		cprint("c [computeBias] empty samples; using default weights")
		return sampling_cnf + sampling_weights_y_1
	max_idx = max(Yvar) - 1
	if samples_biased_one.shape[1] <= max_idx or samples_biased_zero.shape[1] <= max_idx:
		cprint("c [computeBias] sample dimension mismatch; using default weights")
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
		





def _max_rows_from_memory(row_len, num_samples, frac):
	if frac <= 0:
		return num_samples
	available = psutil.virtual_memory().available
	bytes_per_row = max(row_len - 1, 1)
	max_rows = max(int((available * frac) // bytes_per_row), 1)
	return min(num_samples, max_rows)


def _stream_samples(path, num_samples, frac):
	rows = []
	row = []
	row_len = None
	max_rows = None
	skipped_header = False

	with open(path, "r") as f:
		buf = ""
		for chunk in iter(lambda: f.read(1024 * 1024), ""):
			buf += chunk
			parts = buf.split()
			if not buf.endswith((" ", "\n", "\t")):
				buf = parts.pop() if parts else buf
			else:
				buf = ""
			for tok in parts:
				if not skipped_header and tok == "SAT":
					skipped_header = True
					continue
				try:
					val = int(tok)
				except ValueError:
					continue
				if val == 0:
					if row_len is None:
						row_len = len(row) + 1
						max_rows = _max_rows_from_memory(row_len, num_samples, frac)
					if row_len and len(row) + 1 != row_len:
						row = []
						continue
					if row_len:
						rows.append((np.array(row, dtype=np.int32) > 0).astype(np.uint8))
					row = []
					if max_rows is not None and len(rows) >= max_rows:
						if max_rows < num_samples:
							cprint("c [samples] truncated to", max_rows, "rows due to memory budget")
						return np.vstack(rows) if rows else np.empty((0, 0), dtype=np.uint8)
				else:
					row.append(val)
	if rows:
		return np.vstack(rows)
	return np.empty((0, 0), dtype=np.uint8)


def generatesample(args, num_samples, sampling_cnf, inputfile_name, weighted):
	with tempfile.TemporaryDirectory(prefix="manthan_cmsgen_") as tmpdir:
		tempcnffile = os.path.join(tmpdir, "sample.cnf")
		tempoutputfile = os.path.join(tmpdir, "samples.out")

		with open(tempcnffile, "w") as f:
			f.write(sampling_cnf)
		f.close()

		if getattr(args, "debug_keep", False):
			cmsgen_cnf_path = os.path.abspath(inputfile_name + "_cmsgen_sample.cnf")
			shutil.copyfile(tempcnffile, cmsgen_cnf_path)
			if getattr(args, "verbose", 0) >= 1:
				cprint("c [samples] saved cmsgen cnf:", cmsgen_cnf_path)

		cmsgen = "./dependencies/static_bin/cmsgen"
		if not os.path.isfile(cmsgen):
			cmsgen = "./dependencies/cmsgen"
		cmsgen = os.path.abspath(cmsgen)
		cmd = [cmsgen, "--samples", str(int(num_samples)),
		       "-s", str(args.seed), "--samplefile", "samples.out", "sample.cnf"]
		subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
		if not os.path.isfile(tempoutputfile):
			raise RuntimeError("sample generation failed: %s" % (" ".join(cmd)))

		frac = float(getattr(args, "sample_mem_frac", 0.3))
		return _stream_samples(tempoutputfile, int(num_samples), frac)
