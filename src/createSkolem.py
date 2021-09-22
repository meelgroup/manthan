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
import numpy as np

def skolemfunction_preprocess(Xvar,Yvar,PosUnate,NegUnate, UniqueVar, UniqueDef, inputfile_name):
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
			assign = "o%s = 1'b1;\n" %(var)
		if var in NegUnate:
			assign += "assign o%s = 1'b0;\n" %(var)
		if var in UniqueVar:
			assign += "assign o%s = w%s;\n" %(var,var)
			wire += "wire w%s;\n" %(var)

	declare = declare.strip(", ")+");\n"
	skolemformula = declare + declarevar + wire + UniqueDef + assign + "endmodule\n"

	skolemformula = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"

	with open(skolemformula,"w") as f:
		f.write(skolemformula)
	f.close()
	cmd = "./dependencies/file_write_aig %s %s   > /dev/null 2>&1 " % (skolemformula, skolemformula.split("_skolem.v")[0]+"_skolem.aig")
	os.system(cmd)
	os.system("cp %s %s" %(skolemformula.split("_skolem.v")[0]+"_skolem.aig", inputfile_name + "_skolem.aig"))

def createSkolemfunction(inputfile_name, Xvar,Yvar):
	skolemformula = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"
	
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

	for line in lines:
		if line.startswith("module"):
			continue
		if line.startswith("input"):
			continue
		if line.startswith("output"):
			continue
		if line.startswith("assign out"):
			continue
		if line.startswith("endmodule"):
			continue
		if line.startswith("assign beta"):
			var = int(line.strip("assign beta").split("_")[0])
			line = line.replace('& ~o%s' %(var),"")
			line = line.replace('& o%s' %(var), "")
			line = line.replace("o","w")
		content += line
	with open(skolemformula,"w") as f:
		f.write(declare + declare_input + content + assign + "endmodule\n")
	f.close()

	cmd = "./dependencies/file_write_aig %s %s  > /dev/null 2>&1  " % (skolemformula, skolemformula.split("_skolem.v")[0]+"_skolem.aig")
	os.system(cmd)
	os.system("cp %s %s" %(skolemformula.split("_skolem.v")[0]+"_skolem.aig", inputfile_name + "_skolem.aig"))
	os.unlink(skolemformula)
	os.unlink("strash.txt")




def createErrorFormula(Xvar, Yvar, UniqueVars, verilog_formula):
	inputformula = '('
	inputskolem = '('
	inputerrorx = 'module MAIN ('
	inputerrory = ''
	inputerroryp = ''
	declarex = ''
	declarey = ''
	declareyp = ''
	for var in Xvar:
		inputformula += "%s, " % (var)
		inputskolem += "%s, " % (var)
		inputerrorx += "%s, " % (var)
		declarex += "input %s ;\n" % (var)
	for var in Yvar:
		inputformula += "%s, " % (var)
		inputerrory += "%s, " % (var)
		declarey += "input %s ;\n" % (var) 
		inputerroryp += "ip%s, " % (var)
		declareyp += "input ip%s ;\n" % (var)
		if var in UniqueVars:
			inputskolem += "%s, " %(var)
		else:
			inputskolem += "ip%s, " %(var)
	inputformula += "out1 );\n"
	inputformula_sk = inputskolem + "out3 );\n"
	inputskolem += "out2 );\n"
	inputerrorx = inputerrorx + inputerrory + inputerroryp + "out );\n"
	declare = declarex + declarey + declareyp + 'output out;\n' + \
		"wire out1;\n" + "wire out2;\n" + "wire out3;\n"
	formula_call = "FORMULA F1 " + inputformula
	skolem_call = "SKOLEMFORMULA F2 " + inputskolem
	formulask_call = "FORMULA F2 " + inputformula_sk
	error_content = inputerrorx + declare + \
		formula_call + skolem_call + formulask_call
	error_content += "assign out = ( out1 & out2 & ~(out3) );\n" + \
		"endmodule\n"
	error_content += verilog_formula
	return error_content


def addSkolem(error_content,inputfile_name):
	skolemformula = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"
	with open(skolemformula, 'r') as f:
		skolemcontent = f.read()
	f.close()
	errorformula = tempfile.gettempdir() + '/' + inputfile_name + "_errorformula.v"
	f = open(errorformula, "w")
	f.write(error_content)
	f.write(skolemcontent)
	f.close()

def createSkolem(candidateSkf, Xvar, Yvar, UniqueVars, UniqueDef, inputfile_name):
	tempOutputFile = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"  # F(X,Y')
	inputstr = 'module SKOLEMFORMULA ('
	declarestr = ''
	assignstr = ''
	wirestr = 'wire zero;\nwire one;\n'
	wirestr += "assign zero = 0;\nassign one = 1;\n"
	outstr = ''
	itr = 1
	wtlist = []
	
	for var in Xvar:
		declarestr += "input i%s;\n" % (var)
		inputstr += "i%s, " % (var)
	for var in Yvar:
		flag = 0
		declarestr += "input o%s;\n" % (var)
		inputstr += "o%s, " % (var)
		wirestr += "wire w%s;\n" % (var)
		if var not in UniqueVars:
			assignstr += 'assign w%s = (' % (var)
			assignstr += candidateSkf[var].replace(" 1 ", " one ").replace(" 0 ", " zero ") +");\n"
		
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
	assignstr += "assign out = "
	for i in wtlist:
		assignstr += "wt%s & " % (i)
	assignstr = assignstr.strip("& ") + ";\n"
	inputstr += " out );\n"
	declarestr += "output out ;\n"
	f = open(tempOutputFile, "w")
	f.write(inputstr + declarestr + wirestr)
	f.write(UniqueDef.strip("\n")+"\n")
	f.write(assignstr + "endmodule")
	f.close()


def simply(inputfile_name):
	skolemformula = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"  # F(X,Y')

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
	



def verify(Xvar, Yvar, inputfile_name):
	errorformula = tempfile.gettempdir() + '/' + inputfile_name + "_errorformula.v"
	cexfile = tempfile.gettempdir() + '/' + inputfile_name + "_cex.txt"
	exists = os.path.isfile("strash.txt")
	if exists:
		os.system("rm strash.txt")
	cmd = "./dependencies/file_generation_cex %s %s  > /dev/null 2>&1" % (errorformula, cexfile)
	os.system(cmd)
	exists = os.path.isfile("strash.txt")
	if exists:
		os.system("rm strash.txt")
		exists_cex = os.path.isfile(cexfile)
		if exists_cex:
			cexmodels = []
			ret = 1
			with open(cexfile, 'r') as f:
				lines = f.readlines()
			f.close()
			os.unlink(cexfile)
			for line in lines:
				model = line.strip(" \n")
			cex = list(map(int, model))
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
		else:
			return(1, [], 0)
	else:
		return(0, [0], 1)