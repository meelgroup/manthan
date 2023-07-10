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


def convert_verilog(args, Xvar, Yvar, dg):

	'''
	Converts qdimacs or dqimacs to verilog format.

	From

	a 1 3 0
    e 2 4 0
	1 2 0
	3 4 0
	4 5 0

	to

	module FORMULA(1, 3, 2, 4, out);
	input 1;
	input 3;
	input 2;
	input 4;

	wire t_1;
	assign t_1 = 1 & 2;

	wire t_2;
	assign t_2 = 3 & 4;

	wire t_3;
	assign t_3 = 4 & 5;

	assign out = t_1 & t_2 & t_3;

	endmodule

	'''

	declare = 'module FORMULA( '
	declare_input = ''
	declare_wire = ''
	assign_wire = ''

	
	for xvar in Xvar:
		declare += "%s," %(xvar)
		declare_input += "input %s;\n" %(xvar)
	
	for yvar in Yvar:
		declare += "%s," %(yvar)
		declare_input += "input %s;\n" %(yvar)




	with open(args.input, 'r') as f:
		lines = f.readlines()
	f.close()

	itr = 1
	

	for line in lines:

		line = line.strip(" ")

		if (line == "") or (line == "\n"):
			continue

		if line.startswith("c "):
			continue

		if line.startswith("p "):
			continue


		if line.startswith("a"):
			continue

		if line.startswith("e"):
			continue

		if line.startswith("d "):
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

		assign_wire = assign_wire.strip("| ")+";\n"
		
		'''
		In multiclassification, in order to cluster variable, we need to create primal graph
		in which if y_i and y_j share a clause
		then there is an edge between them. 
		
		'''
		ng = nx.Graph()

		if args.multiclass:
			 # used only if args.multiclass
			for lit_1 in clause_variable:
				lit_1 = abs(int(lit_1))
				if lit_1 in Yvar:
					if lit_1 not in list(ng.nodes):
						ng.add_node(lit_1)
					for lit_2 in clause_variable:
						lit_2 = abs(int(lit_2))
						if (lit_1 != abs(lit_2)) and (lit_2 in Yvar):
							if lit_2 not in list(ng.nodes):
								ng.add_node(lit_2)
							if not ng.has_edge(lit_1, lit_2):
								ng.add_edge(lit_1,lit_2)



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
		outstr += "tcount_%s;\n" %(itr)
	outstr = "assign out = %s" %(outstr)


	verilogformula = declare + declare_input + declare_wire + assign_wire + outstr +"endmodule\n"

	return verilogformula, dg, ng