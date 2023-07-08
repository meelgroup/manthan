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

from src.DefinabilityChecker import DefinabilityChecker
import networkx as nx

def find_unique_function(args, qdimacs_list, Xvar, Yvar, dg, Unates, HenkinDep = {}):

	
	'''
	Calling Unique to find uniquely defined functions.
	'''

	offset = 5*(len(Yvar)+len(Xvar))+100  #introducting new variables after each defination
	
	UniqueChecker = DefinabilityChecker(qdimacs_list,Yvar)
	UniqueVars = []  # list of uniquely defined variables
	UniqueDef = ''  # definations of uniquely defined variables
	declare_wire = '' # defination will be  wire w_y_i = unique defination

	itr = 0

	for yvar in Yvar:

		if yvar in Unates:
			itr += 1
			continue

		if not args.henkin:

			Ydependent = list(nx.ancestors(dg,yvar))
			Ydependent.append(yvar)
			'''
			There could be two ways to deciding depended variables at this stage, 
			find dependencies on the fly or use a predefined Yorder.
			for our set of benchmarks, later one performed better.
			'''
			#definingYvar = list(set(Yvar) - set(Ydependent))
			definingYvar = Yvar[:itr]
			defination = UniqueChecker.checkDefinability( Xvar + definingYvar, int(yvar), offset)
			
		else:
			definingYvar = list(nx.descendants(dg,yvar))
			if yvar in definingYvar:
				definingYvar.remove(yvar)
			defination = UniqueChecker.checkDefinability( HenkinDep[yvar] + definingYvar, int(yvar), offset)
			
			
		itr += 1

		countoffset = 0

		
		if defination[0] == True:  #yvar is uniquely defined. 

			'''
			Defination is a list of lists that represents the defination of yvar
			Each individual list represents a conjuction, where last literals is defined as the conjuction 
			of all the literals before.

			Example [2,3,8] corresponds to 8 = 2 & 3
			
			Defination might introduce new variables in between, which will considered as wires 
			in the verilog format and they have exact definiation listed.
			'''
			
			UniqueVars.append(yvar)

			for lists in defination[1]:
				clause = lists[0]
				clauseString = ''

				if isinstance(clause,list):
					for defvar in clause:

						if int(defvar) < 0:
							clauseString += "~"

						if abs(defvar) in Yvar:

							if abs(defvar) != yvar:
								dg.add_edge(yvar,abs(int(defvar))) 

							clauseString += "w%s &" %(abs(defvar))
							
						elif abs(defvar) in Xvar:
							clauseString += "i%s & " %(abs(defvar))
							
						else:
							clauseString += "utemp%s &  " %(abs(defvar))
							
					if len(defination[1]) > 1:

						if int(lists[1]) not in Yvar:

							countoffset += 1
							declare_wire += "wire utemp%s;\n" %(lists[1])
							UniqueDef += "assign utemp%s = %s;\n" %(lists[1],clauseString.strip("& "))

						else:

							UniqueDef += "assign w%s = %s;\n" %(yvar, clauseString.strip("& "))
					else:

						countoffset += 1
						defvar = clause[0]
						clauseString = ''

						if int(defvar) < 0:
							clauseString += "~"

						if abs(defvar) in Xvar:
							clauseString += "i%s;\n" %(abs(defvar))
						elif abs(defvar) in Yvar:
							clauseString += "w%s;\n" %(abs(defvar))
						else:
							print("check unique defination")
							exit()

						UniqueDef += "assign w%s = %s" %(yvar, clauseString)
				else:

					if clause > 0:
						UniqueDef += "assign w%s = 1'b1;\n" %(abs(clause))
					else:
						UniqueDef += "assign w%s = 1'b0;\n" %(abs(clause))
					countoffset += 1

		offset += countoffset + 100
	
	return UniqueVars, declare_wire+UniqueDef, dg
