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
import os
import subprocess
import shutil
import re
import numpy as np
from src.logging_utils import cprint
from src.tempfiles import temp_path


def static_bin_path(bin_name):
	preferred = os.path.join("./dependencies/static_bin", bin_name)
	if os.path.isfile(preferred) and os.access(preferred, os.X_OK):
		return os.path.abspath(preferred)
	fallbacks = [
		os.path.join("./dependencies", bin_name),
		os.path.join("./dependencies/abc", bin_name),
	]
	for candidate in fallbacks:
		if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
			return os.path.abspath(candidate)
	return os.path.abspath(os.path.join("./dependencies", bin_name))

def _wrap_assign(expr, indent="  ", max_terms=200, max_len=4000):
	if " | " in expr:
		terms = [t.strip() for t in expr.split(" | ") if t.strip()]
		sep = " | "
	elif " & " in expr:
		terms = [t.strip() for t in expr.split(" & ") if t.strip()]
		sep = " & "
	else:
		return expr
	if not terms:
		return ""
	rebuilt = sep.join(terms)
	lines = []
	current = ""
	for term in terms:
		if not current:
			next_str = term
		else:
			next_str = current + sep + term
		if (current and (len(next_str) > max_len or (current.count(sep) + 1) >= max_terms)):
			lines.append(current)
			current = term
		else:
			current = next_str
	if current:
		lines.append(current)
	if len(lines) <= 1:
		return rebuilt
	return (sep + "\n" + indent).join(lines)


def _normalize_verilog_module_order(verilog_text):
	# Ensure all declarations appear before assigns/instances within each module.
	lines = verilog_text.splitlines()
	out = []
	i = 0
	while i < len(lines):
		line = lines[i]
		if not line.startswith("module "):
			out.append(line)
			i += 1
			continue
		# Capture one module.
		header = line
		body = []
		i += 1
		while i < len(lines):
			l = lines[i]
			body.append(l)
			if l.strip().startswith("endmodule"):
				break
			i += 1
		i += 1
		decls = []
		assigns = []
		others = []
		endmodule = None
		in_assign_block = False
		assign_block = []
		for l in body:
			ls = l.lstrip()
			if ls.startswith("endmodule"):
				if assign_block:
					assigns.extend(assign_block)
					assign_block = []
					in_assign_block = False
				endmodule = l
				continue
			if in_assign_block:
				assign_block.append(l)
				if ls.rstrip().endswith(";"):
					assigns.extend(assign_block)
					assign_block = []
					in_assign_block = False
				continue
			if ls.startswith("input ") or ls.startswith("output ") or ls.startswith("wire ") or ls.startswith("reg "):
				decls.append(l)
			elif ls.startswith("assign "):
				assign_block = [l]
				in_assign_block = True
				if ls.rstrip().endswith(";"):
					assigns.extend(assign_block)
					assign_block = []
					in_assign_block = False
			else:
				others.append(l)
		if assign_block:
			assigns.extend(assign_block)
		out.append(header)
		out.extend(decls)
		out.extend(others)
		out.extend(assigns)
		if endmodule is not None:
			out.append(endmodule)
	return "\n".join(out) + "\n"




def skolemfunction_preprocess(Xvar, Yvar, PosUnate, NegUnate, UniqueVar, UniqueDef, inputfile_name, output_path=None):
	declare = 'module SkolemFormula ('
	declarevar = ''
	assign = ''
	wire = ''

	for var in Xvar:
		declare += "i%s, " %(var)
		declarevar += "input i%s;\n" %(var)

	for var in Yvar:
		declare += "o%s, " %(var)
		declarevar += "output o%s;\n" %(var)
		if var in PosUnate:
			assign = "assign o%s = 1'b1;\n" %(var)
		if var in NegUnate:
			assign += "assign o%s = 1'b0;\n" %(var)
		if var in UniqueVar:
			assign += "assign o%s = w%s;\n" %(var,var)
			wire += "wire w%s;\n" %(var)

	declare = declare.strip(", ")+");\n"
	skolemformula = declare + declarevar + wire + UniqueDef + assign + "endmodule\n"

	if output_path is None:
		output_path = inputfile_name + "_skolem.v"

	with open(output_path,"w") as f:
		f.write(skolemformula)
	f.close()
	
def createSkolemfunction(inputfile_name, Xvar, Yvar, output_path=None, selfsub=None, selfsub_dir=None):
	skolemformula = temp_path(inputfile_name + "_skolem.v")
	if output_path is None:
		output_path = inputfile_name + "_skolem.v"
	
	content = ''
	declare = "module SkolemFormula ("
	declare_input = ""
	assign = ""
	for var in Xvar:
		declare += "i%s, " %(var)
		declare_input += "input i%s;\n" %(var)
	for var in Yvar:
		declare += "o%s, " %(var)
		declare_input += "output o%s;\n" %(var)
		assign += "assign o%s = w%s;\n" %(var,var)
	declare = declare.strip(", ")+");\n"

	with open(skolemformula,"r") as f:
		lines = f.readlines()
	f.close()

	skip_out = False
	for line in lines:
		if skip_out:
			if ";" in line:
				skip_out = False
			continue
		if line.startswith("module"):
			continue
		if line.startswith("input ["):
			continue
		if re.match(r"assign i\d+ = i_bus\d+\[", line):
			continue
		if re.match(r"assign o\d+ = o_bus\d+\[", line):
			continue
		if line.startswith("input"):
			continue
		if line.startswith("output"):
			continue
		if line.startswith("assign out"):
			if ";" not in line:
				skip_out = True
			continue
		if line.startswith("endmodule"):
			continue
		if line.startswith("assign beta"):
			var = int(line.strip("assign beta").split("_")[0])
			# Remove explicit o<var> terms and map o<digits> -> w<digits> safely.
			line = re.sub(r"\s*&\s*~o%s\b" % var, "", line)
			line = re.sub(r"\s*&\s*o%s\b" % var, "", line)
			line = re.sub(r"\bo(\d+)\b", r"w\1", line)
		content += line
	extra_modules = ""
	if selfsub and selfsub_dir:
		from src.selfsub import load_selfsub_modules
		extra_modules = load_selfsub_modules(selfsub, selfsub_dir)
	with open(skolemformula,"w") as f:
		f.write(declare + declare_input + content + assign + "endmodule\n")
		if extra_modules:
			f.write(extra_modules)
	f.close()

	shutil.copy(skolemformula, output_path)
	os.unlink(skolemformula)




def createErrorFormula(Xvar, Yvar, UniqueVars, verilog_formula):
	def _bus_ref(prefix, var):
		seg = (var - 1) // 128
		off = (var - 1) % 128
		return f"{prefix}{seg}[{off}]"

	max_var = max([0] + list(Xvar) + list(Yvar))
	max_y = max([0] + list(Yvar))
	v_bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
	ip_bus_cnt = (max_y + 127) // 128 if max_y > 0 else 0

	v_bus_ports = [f"v_bus{i}" for i in range(v_bus_cnt)]
	ip_bus_ports = [f"ip_bus{i}" for i in range(ip_bus_cnt)]
	f2_bus_ports = [f"f2_bus{i}" for i in range(v_bus_cnt)]
	o_bus_ports = [f"o_bus{i}" for i in range(ip_bus_cnt)]

	bus_decl = ""
	for name in v_bus_ports:
		bus_decl += f"input [127:0] {name};\n"
	for name in ip_bus_ports:
		bus_decl += f"input [127:0] {name};\n"
	for name in f2_bus_ports:
		bus_decl += f"wire [127:0] {name};\n"
	for name in o_bus_ports:
		bus_decl += f"wire [127:0] {name};\n"

	assign_inputs = ""
	for var in Xvar:
		assign_inputs += "assign %s = %s;\n" % (_bus_ref("f2_bus", var), _bus_ref("v_bus", var))
	for var in Yvar:
		# Verification must compare Skolem outputs against an independent Y' (ip_bus),
		# even for uniquely defined variables.
		assign_inputs += "assign %s = %s;\n" % (_bus_ref("f2_bus", var), _bus_ref("ip_bus", var))
		assign_inputs += "assign %s = %s;\n" % (_bus_ref("o_bus", var), _bus_ref("ip_bus", var))

	inputformula = "( " + ", ".join(v_bus_ports + ["out1"]) + " );\n"
	inputformula_sk = "( " + ", ".join(f2_bus_ports + ["out3"]) + " );\n"
	inputskolem = "( " + ", ".join(v_bus_ports + o_bus_ports + ["out2"]) + " );\n"

	inputerrorx = "module MAIN (" + ", ".join(v_bus_ports + ip_bus_ports + ["out"]) + " );\n"
	declare = bus_decl + "output out;\n" + "wire out1;\n" + "wire out2;\n" + "wire out3;\n" + assign_inputs
	formula_call = "FORMULA F1 " + inputformula
	skolem_call = "SKOLEMFORMULA F2 " + inputskolem
	formulask_call = "FORMULA F2 " + inputformula_sk
	error_content = inputerrorx + declare + formula_call + skolem_call + formulask_call
	error_content += "assign out = ( out1 & out2 & ~(out3) );\n" + "endmodule\n"
	error_content += verilog_formula
	return error_content
def addSkolem(error_content, inputfile_name, debug_keep=False, selfsub=None, selfsub_dir=None):
	skolemformula = temp_path(inputfile_name + "_skolem.v")
	with open(skolemformula, 'r') as f:
		skolemcontent = f.read()
	f.close()
	if debug_keep:
		errorformula = os.path.abspath(inputfile_name + "_errorformula.v")
	else:
		errorformula = temp_path(inputfile_name + "_errorformula.v")
	with open(errorformula, "w") as f:
		f.write(error_content)
		f.write(skolemcontent)
		if selfsub and selfsub_dir:
			from src.selfsub import load_selfsub_modules
			f.write(load_selfsub_modules(selfsub, selfsub_dir))

def createSkolem(candidateSkf, Xvar, Yvar, UniqueVars, UniqueDef, inputfile_name):
	tempOutputFile = temp_path(inputfile_name + "_skolem.v")  # F(X,Y')
	inputstr = 'module SKOLEMFORMULA ('
	declarestr = ''
	assignstr = ''
	wirestr = 'wire zero;\nwire one;\n'
	assignstr += "assign zero = 0;\nassign one = 1;\n"
	outstr = ''
	itr = 1
	wtlist = []

	def _bus_ref(prefix, var):
		seg = (var - 1) // 128
		off = (var - 1) % 128
		return f"{prefix}{seg}[{off}]"

	max_var = max([0] + list(Xvar) + list(Yvar))
	max_y = max([0] + list(Yvar))
	i_bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
	o_bus_cnt = (max_y + 127) // 128 if max_y > 0 else 0
	i_bus_ports = []
	o_bus_ports = []
	for i in range(i_bus_cnt):
		name = f"i_bus{i}"
		i_bus_ports.append(name)
		declarestr += f"input [127:0] {name};\n"
	for i in range(o_bus_cnt):
		name = f"o_bus{i}"
		o_bus_ports.append(name)
		declarestr += f"input [127:0] {name};\n"
	inputstr = "module SKOLEMFORMULA (" + ", ".join(i_bus_ports + o_bus_ports + ["out"]) + ");\n"

	for var in Xvar:
		declarestr += "wire i%s;\n" % (var)
		assignstr += "assign i%s = %s;\n" % (var, _bus_ref("i_bus", var))
	for var in Yvar:
		flag = 0
		declarestr += "wire o%s;\n" % (var)
		assignstr += "assign o%s = %s;\n" % (var, _bus_ref("o_bus", var))
		wirestr += "wire w%s;\n" % (var)
		if var not in UniqueVars:
			if var not in candidateSkf:
				cprint("c [createSkolem] missing candidate for w%s; defaulting to 0" % (var))
				candidateSkf[var] = " 0 "
			assignstr += 'assign w%s = (' % (var)
			assign_expr = candidateSkf[var].replace(" 1 ", " one ").replace(" 0 ", " zero ")
			assign_expr = _wrap_assign(assign_expr, indent="    ", max_terms=200)
			assignstr += assign_expr +");\n"
		
		outstr += "(~(w%s ^ o%s)) & " % (var,var)
		if itr % 10 == 0:
			flag = 1
			outstr = outstr.strip("& ")
			wirestr += "wire wt%s;\n" % (itr)
			assignstr += "assign wt%s = %s;\n" % (itr, outstr)
			wtlist.append(itr)
			outstr = ''
		itr += 1
	if(flag == 0):
		outstr = outstr.strip("& ")
		wirestr += "wire wt%s;\n" % (itr)
		assignstr += "assign wt%s = %s;\n" % (itr, outstr)
		wtlist.append(itr)
	out_terms = []
	for i in wtlist:
		out_terms.append("wt%s" % (i))
	out_expr = " & ".join(out_terms)
	out_expr = _wrap_assign(out_expr, indent="  ", max_terms=200)
	assignstr += "assign out = " + out_expr + ";\n"
	# inputstr already includes the full module header.
	declarestr += "output out ;\n"
	f = open(tempOutputFile, "w")
	f.write(inputstr + declarestr + wirestr)
	f.write(UniqueDef.strip("\n")+"\n")
	f.write(assignstr + "endmodule")
	f.close()


def simply(inputfile_name):
	skolemformula = temp_path(inputfile_name + "_skolem.v")  # F(X,Y')

	with open(skolemformula,"r") as f:
		lines = f.readlines()
	f.close()

	content = ''

	for line in lines:
		if line.startswith("assign beta"):
			var = int(line.strip("assign beta").split("_")[0])
			line.replace('& ~o%s' %(var),"")
			line.replace('& o%s' %(var), "")
			line.replace("o","w")
		content += line
	
	with open(skolemformula,"w") as f:
		f.write(content)
	f.close()
	



def verify(Xvar, Yvar, inputfile_name, verbose=0, debug_keep=False):
	errorformula = temp_path(inputfile_name + "_errorformula.v")
	if debug_keep and not os.path.isfile(errorformula):
		errorformula = os.path.abspath(inputfile_name + "_errorformula.v")
	if not os.path.isfile(errorformula):
		cprint("c [verify] missing error formula:", errorformula)
		return(0, [0], 1)
	with tempfile.TemporaryDirectory(prefix="manthan_abc_") as abc_tmpdir:
		cexfile = os.path.join(abc_tmpdir, inputfile_name + "_cex.txt")
		abc_cex = static_bin_path("file_generation_cex")
		cmd = [abc_cex, errorformula, cexfile]
		cprint("c [verify] abc tool: file_generation_cex")
		cprint("c [verify] abc cmd:", " ".join(cmd))
		result = subprocess.run(cmd, cwd=abc_tmpdir,
			stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
		if result.returncode != 0:
			if verbose:
				cprint("c [verify] abc stdout:", result.stdout.strip())
				cprint("c [verify] abc stderr:", result.stderr.strip())
			return(0, [0], 1)

		if os.path.isfile(cexfile):
			with open(cexfile, 'r') as f:
				model = f.read().strip(" \n")
			if model:
				cexmodels = []
				ret = 1
				if (" " not in model) and ("\n" not in model) and all(ch in "01" for ch in model):
					cex = [int(ch) for ch in model]
				else:
					cex = []
					for tok in model.split():
						try:
							val = int(tok)
						except ValueError:
							continue
						if val == 0:
							continue
						cex.append(val)
				if len(cex) < (len(Xvar) + 2 * len(Yvar)):
					return(1, [], 0)
				cex = cex[:len(Xvar) + 2 * len(Yvar)]
				templist = np.split(cex, [len(Xvar), len(Xvar) + len(Yvar)])
				modelx = templist[0]
				modely = templist[1]
				modelyp = templist[2]
				assert(len(modelx) == len(Xvar))
				assert(len(modelyp) == len(Yvar))
				assert(len(modely) == len(Yvar))
				cexmodels.append(modelx)
				cexmodels.append(modely)
				cexmodels.append(modelyp)
				return(1, cexmodels, ret)
		return(1, [], 0)
