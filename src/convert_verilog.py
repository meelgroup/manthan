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


import networkx as nx


def _wrap_assign(expr, indent="  ", max_terms=200):
	if " | " in expr:
		terms = expr.split(" | ")
		sep = " | "
	elif " & " in expr:
		terms = expr.split(" & ")
		sep = " & "
	else:
		return expr
	if len(terms) <= max_terms:
		return expr
	lines = []
	for i in range(0, len(terms), max_terms):
		lines.append(sep.join(terms[i:i + max_terms]))
	return ("\n" + indent + sep).join(lines)


def convert_verilog(input,cluster,dg):
	ng = nx.Graph() # used only if args.multiclass

	with open(input, 'r') as f:
		lines = f.readlines()
	f.close()
	itr = 1
	declare = 'module FORMULA( '
	declare_input = ''
	declare_wire = ''
	assign_wire = ''
	tmp_array = []

	for line in lines:
		line = line.strip(" ")
		if (line == "") or (line == "\n"):
			continue
		if line.startswith("c "):
			continue

		if line.startswith("p "):
			continue


		if line.startswith("a"):
			a_variables = line.strip("a").strip("\n").strip(" ").split(" ")[:-1]
			for avar in a_variables:
				declare += "%s," %(avar)
				declare_input += "input %s;\n" %(avar)
			continue

		if line.startswith("e"):
			e_variables = line.strip("e").strip("\n").strip(" ").split(" ")[:-1]
			for evar in e_variables:
				tmp_array.append(int(evar))
				declare += "%s," %(evar)
				declare_input += "input %s;\n" %(evar)
				if int(evar) not in list(dg.nodes):
					dg.add_node(int(evar))
			continue

		declare_wire += "wire t_%s;\n" %(itr)
		assign_wire += "assign t_%s = " %(itr)
		itr += 1

		clause_variable = line.strip(" \n").split(" ")[:-1]
		for var in clause_variable:
			if int(var) < 0:
				assign_wire += "~%s | " %(abs(int(var)))
			else:
				assign_wire += "%s | " %(abs(int(var)))

		assign_wire = assign_wire.strip("| ")
		assign_wire = _wrap_assign(assign_wire, indent="  ", max_terms=200)
		assign_wire += ";\n"
		
		### if args.multiclass, then add an edge between variables of the clause ###

		if cluster:
			for literal1 in clause_variable:
				literal1 = abs(int(literal1))
				if literal1 in tmp_array:
					if literal1 not in list(ng.nodes):
						ng.add_node(literal1)
					for literal2 in clause_variable:
						literal2 = abs(int(literal2))
						if (literal1 != abs(literal2)) and (literal2 in tmp_array):
							if literal2 not in list(ng.nodes):
								ng.add_node(literal2)
							if not ng.has_edge(literal1, literal2):
								ng.add_edge(literal1,literal2)



	count_tempvariable = itr

	declare += "out);\n"
	declare_input += "output out;\n"

	temp_assign = ''
	outstr = ''

	itr = 1
	while itr < count_tempvariable:
		temp_assign += "t_%s & " %(itr)
		if itr % 100 == 0:
			declare_wire += "wire tcount_%s;\n" %(itr)
			assign_wire += "assign tcount_%s = %s;\n" %(itr,temp_assign.strip("& "))
			outstr += "tcount_%s & " %(itr)
			temp_assign = ''
		itr += 1

	if temp_assign != "":
		declare_wire += "wire tcount_%s;\n" %(itr)
		assign_wire += "assign tcount_%s = %s;\n" %(itr,temp_assign.strip("& "))
		outstr += "tcount_%s & " %(itr)
	out_expr = outstr.strip("& \n")
	out_expr = _wrap_assign(out_expr, indent="  ", max_terms=200)
	outstr = "assign out = %s;\n" %(out_expr)


	verilogformula = declare + declare_input + declare_wire + assign_wire + outstr +"endmodule\n"

	return verilogformula, dg, ng
