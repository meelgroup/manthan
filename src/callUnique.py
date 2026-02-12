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
from src.logging_utils import cprint

def unique_function(qdimacs_list, Xvar, Yvar, dg, Unates):

	offset = 5*(len(Yvar)+len(Xvar))+100
	UniqueChecker = DefinabilityChecker(qdimacs_list,Yvar)
	UniqueVars = []
	unique_def_lines = []
	declare_wire_lines = []



	itr = 0

	for yvar in Yvar:

		if yvar in Unates:
			itr += 1
			continue

		definingYvar = Yvar[:itr]
		itr += 1
		countoffset = 0

		defination = UniqueChecker.checkDefinability( Xvar + definingYvar, int(yvar), offset)
		if defination[0] == True:
			definitions = defination[1]
			if isinstance(definitions, tuple):
				definitions = definitions[0]
			UniqueVars.append(yvar)

			for lists in definitions:
				clause = lists[0]
				clause_parts = []

				if isinstance(clause, (list, tuple)):
					for defvar in clause:
						if int(defvar) < 0:
							clause_parts.append("~")
						if abs(defvar) in Yvar:
							if int(yvar) not in list(dg.nodes):
								dg.add_node(int(yvar))
							if abs(int(defvar)) not in list(dg.nodes):
								dg.add_node(abs(int(defvar)))
							dg.add_edge(yvar,abs(int(defvar)))
							clause_parts.append("w%s &" %(abs(defvar)))
							
						elif abs(defvar) in Xvar:
							clause_parts.append("i%s & " %(abs(defvar)))
							
						else:
							clause_parts.append("utemp%s &  " %(abs(defvar)))
							
					clauseString = "".join(clause_parts)
					if len(definitions) > 1:
						if int(lists[1]) not in Yvar:
							countoffset += 1
							declare_wire_lines.append("wire utemp%s;\n" %(lists[1]))
							unique_def_lines.append("assign utemp%s = %s;\n" %(lists[1],clauseString.strip("& ")))
						else:
							unique_def_lines.append("assign w%s = %s;\n" %(yvar, clauseString.strip("& ")))
					else:
						countoffset += 1
						defvar = clause[0]
						clause_parts = []
						if int(defvar) < 0:
							clause_parts.append("~")
						if abs(defvar) in Xvar:
							clause_parts.append("i%s;\n" %(abs(defvar)))
						elif abs(defvar) in Yvar:
							clause_parts.append("w%s;\n" %(abs(defvar)))
						else:
							cprint("c [unique_function] check unique definitions")
							exit()
						clauseString = "".join(clause_parts)
						unique_def_lines.append("assign w%s = %s" %(yvar, clauseString))
				else:
					if int(clause) > 0:
						unique_def_lines.append("assign w%s = 1'b1;\n" %(abs(clause)))
					else:
						unique_def_lines.append("assign w%s = 1'b0;\n" %(abs(clause)))
					countoffset += 1
		offset += countoffset + 100
	return UniqueVars, "".join(declare_wire_lines) + "".join(unique_def_lines)
