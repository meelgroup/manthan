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


def convert_verilog(input,cluster,dg):
	ng = nx.Graph() # used only if args.multiclass

	with open(input, 'r') as f:
		lines = f.readlines()
	f.close()
	itr = 1
	declare = 'module FORMULA( '
	declare_input = []
	declare_wire = []
	assign_wire = []
	tmp_array = []
	formula_vars = set()
	def _vname(var):
		s = str(var).strip()
		if s.lstrip("-").isdigit():
			return "v%s" % (abs(int(s)))
		return s
	def _bus_ref(prefix, var):
		seg = (var - 1) // 128
		off = (var - 1) % 128
		return f"{prefix}{seg}[{off}]"

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
				formula_vars.add(int(avar))
			continue

		if line.startswith("e"):
			e_variables = line.strip("e").strip("\n").strip(" ").split(" ")[:-1]
			for evar in e_variables:
				formula_vars.add(int(evar))
				tmp_array.append(int(evar))
				if int(evar) not in list(dg.nodes):
					dg.add_node(int(evar))
			continue

		parts = line.strip().split()
		clause_variable = parts[:-1]
		if not clause_variable:
			continue

		declare_wire.append("wire t_%s;\n" % (itr))
		assign_parts = ["assign t_%s = " % (itr)]
		itr += 1
		for var in clause_variable:
			v = int(var)
			if v < 0:
				assign_parts.append("~%s | " % (_vname(-v)))
			else:
				assign_parts.append("%s | " % (_vname(v)))

		assign_line = "".join(assign_parts).rstrip("| ")
		if len(assign_line) > 4000:
			assign_line = _wrap_assign(assign_line, indent="  ", max_terms=200)
		assign_wire.append(assign_line + ";\n")
		
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

	max_var = max([0] + list(formula_vars))
	bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
	bus_ports = []
	for i in range(bus_cnt):
		name = f"v_bus{i}"
		bus_ports.append(name)
		declare_input.append(f"input [127:0] {name};\n")
	for v in sorted(formula_vars):
		declare_wire.append("wire %s;\n" % (_vname(v)))
	assign_bus = []
	for v in sorted(formula_vars):
		assign_bus.append("assign %s = %s;\n" % (_vname(v), _bus_ref("v_bus", v)))
	declare = "module FORMULA( " + ", ".join(bus_ports + ["out"]) + " );\n"
	declare_input.append("output out;\n")

	temp_assign = ''
	outstr = []

	itr = 1
	while itr < count_tempvariable:
		temp_assign += "t_%s & " %(itr)
		if itr % 100 == 0:
			declare_wire.append("wire tcount_%s;\n" % (itr))
			assign_wire.append("assign tcount_%s = %s;\n" % (itr,temp_assign.strip("& ")))
			outstr.append("tcount_%s" % (itr))
			temp_assign = ''
		itr += 1

	if temp_assign != "":
		declare_wire.append("wire tcount_%s;\n" % (itr))
		assign_wire.append("assign tcount_%s = %s;\n" % (itr,temp_assign.strip("& ")))
		outstr.append("tcount_%s" % (itr))
	out_expr = " & ".join(outstr)
	out_expr = _wrap_assign(out_expr, indent="  ", max_terms=200)
	outstr_line = "assign out = %s;\n" %(out_expr)

	verilogformula = (
		declare +
		"".join(declare_input) +
		"".join(declare_wire) +
		"".join(assign_bus) +
		"".join(assign_wire) +
		outstr_line +
		"endmodule\n"
	)

	return verilogformula, dg, ng
