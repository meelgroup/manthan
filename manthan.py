#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Copyright (C) 2020 Priyanka Golia, Subhajit Roy, and Kuldeep Meel

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


from __future__ import print_function
import sys
import os
import math
import random
import argparse
import copy
import tempfile
import numpy as np
from numpy import count_nonzero
from sklearn import tree
import collections
import subprocess as subprocess
import time
import networkx as nx
from DefinabilityChecker import DefinabilityChecker
import pydotplus

from collections import OrderedDict

from subprocess import Popen, PIPE, check_output
import signal

SAMPLER_CMS = 1


class cexmodels:

    def __init__(self, modelx, modely, modelyp):
        self.modelx = modelx
        self.modely = modely
        self.modelyp = modelyp


class clist:

    def __init__(self, clistx, clisty):
        self.clistx = clistx
        self.clisty = clisty


def write_to_logfile(text):
    file_log = open("time_details", "a+")
    file_log.write(text + "\n")
    file_log.close()




def preprocess(verilogfile,orderfile,Yvar):
    
    cmd = "./dependencies/preprocess -b %s -v %s >  /dev/null 2>&1" % (verilogfile,orderfile)
    with Popen(cmd, shell=True, stdout=PIPE, preexec_fn=os.setsid) as process:
        try:
            output = process.communicate(timeout=500)[0]
        except Exception:
            os.killpg(process.pid, signal.SIGINT)
            pos_unate = []
            neg_unate = []
            unates = []
            print("timeout preprocessing..")
            return pos_unate, neg_unate, unates
        else:
            pos_unate_tmp = []
            neg_unate_tmp = []
            pos_unate = []
            neg_unate = []
            unates = []
            found_neg = 0
            inputfile_name = verilogfile.split(".v")[0]
            exists = os.path.isfile(inputfile_name + "_vardetails")
            if exists:
                with open(inputfile_name + "_vardetails", 'r') as f:
                    lines = f.readlines()
                f.close()
                for line in lines:
                    
                    if "Posunate" in line:
                        pos = line.split(":")[1].strip(" \n")
                        if pos != "":
                            pos_unate_tmp = pos.split(" ")
                            pos_unate_tmp = np.array(pos_unate_tmp)
                            pos_unate_tmp = pos_unate_tmp.astype(np.int)
                        continue
                    if "Negunate" in line:
                        neg = line.split(":")[1].strip(" \n")
                        if neg != "":
                            neg_unate_tmp = neg.split(" ")
                            neg_unate_tmp = np.array(neg_unate_tmp)
                            neg_unate_tmp = neg_unate_tmp.astype(np.int)
                        continue

                    if "Yvar_map :" in line:
                        Yvar_map = line.split(":")[1].strip(" \n").split(" ")
                        #Yvar_map = np.array(Yvar_map)
                        #Yvar_map = Yvar_map.astype(np.int)
                        continue
                    
                for unate in pos_unate_tmp:
        	        pos_unate.append(Yvar[Yvar_map.index(str(unate))])
        	        unates.append(unate)
                
                for unate in neg_unate_tmp:
                    neg_unate.append(list(Yvar)[Yvar_map.index(str(unate))])
                    unates.append(unate)

                if args.verbose:
                    
                    print("preprocessing ...")
                    print("count positive unate", len(pos_unate))
                    if len(pos_unate) > 0:
                        print("positive unate Y variables", pos_unate)
                    print("count negative unate", len(neg_unate))
                    if len(neg_unate) > 0:
                        print("negative unate Y variables", neg_unate)
                    
                    
                os.unlink(inputfile_name + "_vardetails")
            else:
                print("preprocessing error .. contining ")
                exit()
            return pos_unate, neg_unate, unates
    


def get_sample_cms(allvar_map, cnf_content, no_samples):

	inputfile_name = args.input.split("/")[-1][:-8]
	tempcnffile = tempfile.gettempdir() + '/' + inputfile_name + ".cnf"
	f = open(tempcnffile, "w")
	f.write(cnf_content)
	f.close()
	print(tempcnffile)
	tempoutputfile = tempfile.gettempdir() + '/' + inputfile_name + "_.txt"
	if args.weighted:
		print("weighted samples....")
		cmd = "./dependencies/cryptominisat5 -n1 --sls 0 --comps 0"
		cmd += " --restart luby  --nobansol --maple 0 --presimp 0"
		cmd += " --polar weight --freq 0.9999 --verb 0 --scc 0"
		cmd += " --random %s --maxsol %s > /dev/null 2>&1" % (args.seed, no_samples)
		cmd += " %s" % (tempcnffile)
		cmd += " --dumpresult %s " % (tempoutputfile)
	else:
		print("uniform samples....")
		cmd = "./dependencies/cryptominisat5 --restart luby"
		cmd += " --maple 0 --verb 0 --nobansol"
		cmd += " --scc 1 -n1 --presimp 0 --polar rnd --freq 0.9999"
		cmd += " --random %s --maxsol %s" % (args.seed, no_samples)
		cmd += " %s" % (tempcnffile)
		cmd += " --dumpresult %s > /dev/null 2>&1" % (tempoutputfile)
	if args.verbose:
		print("cmd: ", cmd)
	os.system(cmd)
	with open(tempoutputfile, 'r') as f:
		content = f.read()
	f.close()
	os.unlink(tempoutputfile)
	os.unlink(tempcnffile)
	content = content.replace("SAT\n", "").replace(
		"\n", " ").strip(" \n").strip(" ")
	models = content.split(" ")
	models = np.array(models)
	if(models[len(models) - 1] != '0'):
		models = np.delete(models, len(models) - 1, axis=0)
	index = np.where(models == "0")[0][0]
	var_model = np.reshape(models, (-1, index + 1)).astype(np.int)
	one = np.ones(len(allvar_map), dtype=int)
	allvar_map = np.subtract(allvar_map, one).astype(np.int)
	var_model = var_model[:, allvar_map]
	var_model = var_model > 1
	var_model = var_model.astype(np.int)
	return var_model


def treepaths(root, is_leaves, children_left, children_right, data_feature_names, feature, values, dependson,leave_label,index,size):
    if (is_leaves[root]):
    	temp = values[root]
    	temp = temp.ravel()
    	if(temp[1] < temp[0]):
    		return(['val=0'], dependson)
    	else:
    		return(['1'], dependson)

    left_subtree, dependson = treepaths(
        children_left[root], is_leaves, children_left,
        children_right, data_feature_names, feature, values, dependson,leave_label,index,size)
    right_subtree, dependson = treepaths(
        children_right[root], is_leaves, children_left,
        children_right, data_feature_names, feature, values, dependson,leave_label,index,size)

    # conjunction of all the literal in a path where leaf node has label 1
    # Dependson is list of Y variables on which candidate SKF of y_i depends
    list_left = []
    for leaf in left_subtree:
        if leaf != "val=0":
            dependson.append(data_feature_names[feature[root]])
            # the left part
            list_left.append("~i" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
    list_right = []
    for leaf in right_subtree:
        if leaf != "val=0":
            dependson.append(data_feature_names[feature[root]])
            # the right part
            list_left.append("i" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
            #list_right.append("i" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
    dependson = list(set(dependson))
    return(list_left + list_right, dependson)


def create_decision_tree(feat_name, feat_data, label, e_var):
    clf = tree.DecisionTreeClassifier(
        criterion='gini',
        min_impurity_decrease=args.gini, random_state=args.seed)
    clf = clf.fit(feat_data, label)
    if args.showtrees:
        dot_data = tree.export_graphviz(clf,
                                        feature_names=feat_name,
                                        out_file=None,
                                        filled=True,
                                        rounded=True)
        graph = pydotplus.graph_from_dot_data(dot_data)
        colors = ('turquoise', 'orange')
        edges = collections.defaultdict(list)
        for edge in graph.get_edge_list():
            edges[edge.get_source()].append(int(edge.get_destination()))
        for edge in edges:
            edges[edge].sort()
            for i in range(2):
                dest = graph.get_node(str(edges[edge][i]))[0]
                dest.set_fillcolor(colors[i])
        graph.write_png(str(e_var) + ".png")

    values = clf.tree_.value
    n_nodes = clf.tree_.node_count
    children_left = clf.tree_.children_left
    children_right = clf.tree_.children_right
    feature = clf.tree_.feature
    threshold = clf.tree_.threshold
    leaves = children_left == -1
    leaves = np.arange(0, n_nodes)[leaves]
    node_depth = np.zeros(shape=n_nodes, dtype=np.int64)
    leave_label = np.zeros(shape=n_nodes, dtype=np.int64)
    is_leaves = np.zeros(shape=n_nodes, dtype=bool)
    stack = [(0, -1)]  # seed is the root node id and its parent depth


    while len(stack) > 0:
        node_id, parent_depth = stack.pop()
        node_depth[node_id] = parent_depth + 1
        if (children_left[node_id] != children_right[node_id]):
            stack.append((children_left[node_id], parent_depth + 1))
            stack.append((children_right[node_id], parent_depth + 1))
        else:
            is_leaves[node_id] = True
            leave_label[node_id]=clf.classes_[np.argmax(clf.tree_.value[node_id])]
    D = []
    if (is_leaves[0]):
    	#print("yes")
    	len_one = count_nonzero(label)
    	if len_one >= int(len(label)/2):
    		paths = ["1"] # Maximum label for class 1: tree no split
    	else:
    		paths = ["0"] # Maximum label for class 0: tree no split
    else:
    	paths, D = treepaths(0, is_leaves, children_left, children_right , feat_name, feature, values, D, leave_label,0,0)
    psi_i = ''
    if len(paths) == 0:
    	paths.append('0')
    	D = []
    for path in paths:
    	psi_i += "( " + path + " ) | "
    return psi_i.strip("| "), D
    
def divide_chunks(lst,n):
	x = [lst[i:i + n] for i in range(0, len(lst), n)]
	return x

def binary_to_int(lst):
	lst = np.array(lst)
	# filling the begining with zeros to form bytes
	diff = 8 - lst.shape[1] % 8
	if diff > 0 and diff != 8:
		lst = np.c_[np.zeros((lst.shape[0],diff),int),lst]

	label = np.packbits(lst,axis=1)

	return label


def learn_skf(samples, Xvar, Yvar, pos_unate, neg_unate, unique_var, dg, def_unique, Xvar_name, Yvar_name):
    '''x_data, indices = np.unique(samples[:, Xvar], axis=0, return_index=True)
    samples = samples[indices, :]'''

    if args.verbose:
        print("candidateskf ..")

    # For create decision tree, we need feature names, feature data and label data
    inputfile_name = args.input.split('/')[-1][:-8]
    
    candidateskf = {}
    for i in Yvar:
        if i in neg_unate:
            candidateskf[i] = ' 0 '
            continue
        if i in pos_unate:
            candidateskf[i] = ' 1 '
            continue
        if i in unique_var:
            continue
        feat = list(Xvar)
        feat_name = list(Xvar_name.values())
        hop_neighbour = Yvar
        dependson = list(nx.ancestors(dg,i))
        for j in hop_neighbour:
            if i != j:
                if (j not in dependson):
                    feat.append(j)
                    feat_name.append(Yvar_name[j])
        feat_data = samples[:,feat]
        label = samples[:,i]
        psi_i, D = create_decision_tree(feat_name, feat_data, label, Yvar_name[i])
        candidateskf[i] = psi_i
        for j in D:
        	if j in list(Yvar_name.values()):
        		temp = list(Yvar_name.keys())[list(Yvar_name.values()).index(j)]
        		dg.add_edge(i, temp)
   

    if args.verbose:
        print("generated candidateskf for all Y")

    if args.verbose == 2:
        print("candidate Skolem functions:", candidateskf)
    #exit()

    # we have candidate skolem functions for every y in Y
    # Now, lets generate Skolem formula F(X,Y') : input X and output Y'
    tempOutputFile = tempfile.gettempdir() + \
        '/' + inputfile_name + \
        "_skolem.v"  # F(X,Y')

    inputstr = 'module SKOLEMFORMULA ('
    declarestr = ''
    assignstr = ''
    wirestr = 'wire zero;\nwire one;\n'
    wirestr += "assign zero = 0;\nassign one = 1;\n"
    outstr = ''
    itr = 1
    wtlist = []
    for var in range(len(Xvar) + len(Yvar)):
        
        if var in Xvar:
            declarestr += "input i%s;\n" % (Xvar_name[var])
            inputstr += "i%s, " % (Xvar_name[var])
        if var in Yvar:
            flag = 0
            declarestr += "input i%s;\n" % (Yvar_name[var])
            inputstr += "i%s, " % (Yvar_name[var])
            wirestr += "wire wi%s;\n" % (Yvar_name[var])
            if var not in unique_var:
	            assignstr += 'assign wi%s = (' % (Yvar_name[var])
	            temp = candidateskf[var].replace(
	                " 1 ", " one ").replace(" 0 ", " zero ")
	            assignstr += temp + ");\n"
            outstr += "(~(wi%s ^ i%s)) & " % (Yvar_name[var], Yvar_name[var])
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
    f.write(inputstr)
    f.write(declarestr)
    f.write(wirestr)
    f.write(def_unique.strip("\n")+"\n")
    f.write(assignstr)
    f.write("endmodule")
    f.close()
    return dg



def call_maxsat(refine_maxsat_content, Yvar, Yvar_map, modelyp, modely, unates, unique_var, Yvar_order, selfsub, maxsat_wt):

    maxsatstr = ''
    itr = 0
    for i in Yvar:
        yindex = np.where(i == Yvar_order)[0][0]
        if i not in unates:
            
            if (i in selfsub) or (i in unique_var):
                if (modely[itr] == 0):
                    maxsatstr += str(maxsat_wt) + " -" + str(
                        Yvar_map[i]) + " 0\n"
                else:
                    maxsatstr += str(maxsat_wt) + " " + str(
                        Yvar_map[i]) + " 0\n"
            else:
                weight = 1
                if (modelyp[itr] == 0):
                    maxsatstr += str(weight) + " -" + str(Yvar_map[i]) + " 0\n"
                else:
                    maxsatstr += str(weight) + " " + str(Yvar_map[i]) + " 0\n"
        itr = itr + 1
    refine_maxsat_content += maxsatstr
    inputfile_name = args.input.split('/')[-1][:-8]
    maxsatformula = inputfile_name + "_maxsat.cnf"
    
    # outputfile = tempfile.gettempdir()+'/'+"o" #openwbo has a limit on
    # characters of filename

    outputfile = "o.txt"
    f = open(maxsatformula, "w")
    f.write(refine_maxsat_content)
    f.close()

    cmd = "./dependencies/open-wbo %s -print-unsat-soft=%s > /dev/null 2>&1 " % (
        maxsatformula, outputfile)
    if args.verbose:
        print("maxsat :", cmd)
    os.system(cmd)
    with open(outputfile, 'r') as f:
        lines = f.readlines()
    f.close()
    os.unlink(maxsatformula)
    os.unlink(outputfile)

    indlist = []
    for line in lines:
        if line.split(' ')[0].startswith("p"):
            continue
        else:
            ymap = int(line.split(" ")[1])
            if ymap < 0:
                ymap = -1 * ymap
            if ymap in Yvar_map.values():
                index = list(Yvar_map.keys())[list(Yvar_map.values()).index(ymap)]
                indlist.append(index)
    indlist = np.array(indlist)
    indlist = np.unique(indlist)

    # to add variables in indlist according to Y order.
    Yvar_order_ind = []
    for i in indlist:
        yindex = np.where(i == Yvar_order)[0][0]
        Yvar_order_ind.append(yindex)
    indlist = []
    Yvar_order_ind.sort(reverse=True)
    for i in Yvar_order_ind:
        indlist.append(Yvar_order[i])
    indlist = np.array(indlist)
    return indlist


def add_skolem_to_errorformula(error_content, selfsub):
	inputfile_name = args.input.split('/')[-1][:-8]
	skolemformula = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"
	with open(skolemformula, 'r') as f:
		skolemcontent = f.read()
	f.close()
	errorformula = tempfile.gettempdir() + '/' + inputfile_name + "_errorformula.v"
	skolemcontent_write = ''
	if len(selfsub) != 0:
		for all_selfsub_var in selfsub:
			file_open = open(
				tempfile.gettempdir()+"/selfsub/formula%s_true.v" % (all_selfsub_var), "r")
			content = file_open.read()
			file_open.close()
			skolemcontent_write += "\n" + content
	f = open(errorformula, "w")
	f.write(error_content)
	f.write(skolemcontent)
	f.write(skolemcontent_write)
	f.close()


def create_error_formula(Xvar, Yvar, unique_var, verilog_formula):
    refine_var_log = {}
    inputformula = '('
    inputskolem = '('
    inputerrorx = 'module MAIN ('
    inputerrory = ''
    inputerroryp = ''
    declarex = ''
    declarey = ''
    declareyp = ''
    for var in range(len(Xvar) + len(Yvar)):
        if var in Xvar:
            inputformula += "i%s, " % (var)
            inputskolem += "i%s, " % (var)
            inputerrorx += "i%s, " % (var)
            declarex += "input i%s ;\n" % (var)
        if var in Yvar:
            refine_var_log[var] = 0
            inputformula += "i%s, " % (var)
            inputerrory += "i%s, " % (var)
            declarey += "input i%s ;\n" % (var)
            if var in unique_var:
                inputskolem += "i%s, " % (var)
                inputerroryp += "ip%s, " % (var)
                declareyp += "input ip%s ;\n" %(var)
            else:    
                inputskolem += "ip%s, " % (var)
                inputerroryp += "ip%s, " % (var)
                declareyp += "input ip%s ;\n" % (var)
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
    return error_content, refine_var_log


def verify(Xvar, Yvar, unique_var):
    inputfile_name = args.input.split("/")[-1][:-8]
    errorformula = tempfile.gettempdir() + '/' + inputfile_name + "_errorformula.v"
    cexfile = tempfile.gettempdir() + '/' + inputfile_name + "_cex.txt"
    e = os.path.isfile("strash.txt")
    if e:
        os.system("rm strash.txt")
    cmd = "./dependencies/file_generation_cex %s %s  > /dev/null 2>&1" % (
        errorformula, cexfile)
    if args.verbose:
        print("verify:", cmd)
    os.system(cmd)
    e = os.path.isfile("strash.txt")
    if e:
        os.system("rm strash.txt")
        exists = os.path.isfile(cexfile)
        if exists:
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
            modelyp_tmp = templist[2]
            modelyp=[]
            itr_out = 0
            for itr in range(len(Yvar)):
                if Yvar[itr] in unique_var:
                    modelyp.append(modely[itr])
                else:
                    modelyp.append(modelyp_tmp[itr_out])
                    itr_out += 1
            assert(len(modelx) == len(Xvar))
            assert(len(modelyp) == len(Yvar))
            assert(len(modely) == len(Yvar))
            model_cex = cexmodels(modelx, modely, modelyp)
            return(1, model_cex, ret)
        else:
            return(1, [], 0)
    else:
        return(0, [0], 1)


def find_unsat_core(refine_cnf_content, yi, yi_map, yi_model, yj_map, yj_model, Xvar_map, Yvar_map):
    Yvar = sorted(Yvar_map.keys())
    Xvar = sorted(Xvar_map.keys())
    Yvar_mapping = []
    for var in Yvar:
    	Yvar_mapping.append(Yvar_map[var])
    n_x = len(Xvar_map.keys())
    lines = refine_cnf_content.split("\n")
    for line in lines:
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            str_tmp = "p cnf " + str(numVar) + " " + str(numCls)
            break
    refine_cnf_content = refine_cnf_content.replace(
        str_tmp, "p cnf " + str(numVar) + " " + str(numCls + len(yj_model) + 1 + n_x))
    cnf_str = ''
    yj_model.append(yi_model)
    y_map = np.append(yj_map, yi_map).astype(
        np.int)  # last entry in model_y is model of y_i
    for i in range(len(y_map)):
        if yj_model[i] == 0:
            cnf_str += "-%s 0\n" % (y_map[i])
        else:
            cnf_str += "%s 0\n" % (y_map[i])
    refine_cnf_content += cnf_str.strip("\n")

    inputfile_name = args.input.split('/')[-1][:-8]

    cnffile = inputfile_name+"_unsat.cnf"

    f = open(cnffile, "w")
    f.write(refine_cnf_content)
    f.close()
    unsatcorefile = tempfile.gettempdir() + \
        '/' + inputfile_name + "_unsatcore.txt"
    satfile = tempfile.gettempdir() + '/' + inputfile_name + "_sat.txt"
    
    exists = os.path.isfile(unsatcorefile)
    if exists:
        os.remove(unsatcorefile)
    cmd = "./dependencies/picosat -s %s -V %s %s >  %s" % (
        args.seed, unsatcorefile, cnffile, satfile)
    if args.verbose == 2:
        print("unsatcore :", cmd)
    os.system(cmd)
    exists = os.path.isfile(unsatcorefile)
    if exists:
        ret = 1
        with open(unsatcorefile, 'r') as f:
            lines = f.readlines()
        f.close()
        clistx = []
        clisty = []
        for line in lines:
            C = int(line.strip(" \n"))
            if C in Xvar_map.values():
                #clistx.append(list(Xvar_map.values()).index(C))
                clistx.append(Xvar.index(list(Xvar_map.keys())[list(Xvar_map.values()).index(C)]))
                continue
            if C in Yvar_map.values():
                if C != yi_map:
                	clisty.append(Yvar.index(list(Yvar_map.keys())[list(Yvar_map.values()).index(C)]))
                    #clisty.append(list(Yvar_map.values()).index(C))
                continue
        os.unlink(cnffile)
        os.unlink(unsatcorefile)
        os.unlink(satfile)
        if args.verbose == 1:
            print('formula is unsat for', yi)
        return (ret, [], clist(clistx, clisty))
    else:
        ret = 0
        beta = ''
        one = np.ones(len(Yvar_mapping), dtype=int)
        Yvar_mapping = np.subtract(list(Yvar_mapping), one).astype(np.int)
        with open(satfile, 'r') as f:
            content = f.read()
        f.close()
        os.unlink(satfile)
        #os.unlink(cnffile)
        content = content.replace("s SATISFIABLE\n", "").replace(
            "v", "").replace("\n", "").strip(" \n")

        models = content.split(" ")
        models = np.array(models).astype(np.int)
        models = models[Yvar_mapping] > 1
        models = models.astype(np.int)
        if args.verbose == 1:
            print('formula is sat for', yi)
        return ret, models, beta


  
def selfsubstitute(Xvar, Yvar, var, yi, selfsub, verilog_formula,Xvarnames,Yvarnames):

    Yvar = np.array(Yvar)
    index_selfsub = selfsub.index(var)
    if index_selfsub == 0:
        inputstr = "FORMULA F" + str(var) + "_ ( "
        selfsub_inputstr = ''
        selfsub_declarestr = ''
        for i in range(len(Xvar) + len(Yvar)):
            if i == var:
                inputstr += "# ,"
            else:
                if i in Yvar:
                    #yj = np.where(Yvar == i)[0][0]
                    ij = Yvarnames[i]
                else:
                	ij = Xvarnames[i]

                inputstr += "i%s ," % (ij)
                selfsub_inputstr += "i%s ," % (ij)
                selfsub_declarestr += "input i%s;\n" % (ij)
        inputstr += "out );\nendmodule"
        write_str_true = "module FORMULA" + \
            str(var) + "_true ( " + selfsub_inputstr + " out);\n"
        write_str_false = "module FORMULA" + \
            str(var) + "_false ( " + selfsub_inputstr + " out);\n"
        write_str = selfsub_declarestr + "output out;\n"
        write_str += "wire one;\n" + "assign one = 1;\n"
        write_str += "wire zero;\n" + "assign zero = 0;\n"
        formula_true = inputstr.replace("#", "one")
        formula_false = inputstr.replace("#", "zero")
        file = open(tempfile.gettempdir()+"/selfsub/formula%s_true.v" % (var), "w")
        file.write(write_str_true + write_str + formula_true + "\n")
        file.write(verilog_formula)
        file.close()
        file = open(tempfile.gettempdir()+"/selfsub/formula%s_false.v" % (var), "w")
        file.write(write_str_false + write_str + formula_false + "\n")
        file.write(verilog_formula)
        file.close()
        cmd = "./dependencies/file_write_verilog %s/selfsub/formula%s_true.v %s/selfsub/formula%s_true.v  > /dev/null 2>&1" % (
            tempfile.gettempdir(), var, tempfile.gettempdir(),var)
        os.system(cmd)
        cmd = "./dependencies/file_write_verilog %s/selfsub/formula%s_false.v %s/selfsub/formula%s_false.v > /dev/null 2>&1" % (
            tempfile.gettempdir(), var, tempfile.gettempdir(),var)
        os.system(cmd)
        return_string = 'wire outsub%s ;\nFORMULA%s_true F%s_ ( %s outsub%s);\n' % (
            var, var, var, selfsub_inputstr, var)
    else:
        last_update = selfsub[index_selfsub - 1]
        file = open(tempfile.gettempdir()+"/selfsub/formula%s_true.v" % (last_update), "r")
        file_content_true = file.read()
        file.close()
        file = open(tempfile.gettempdir()+"/selfsub/formula%s_false.v" % (last_update), "r")
        file_content_false = file.read()
        file.close()
        os.remove(tempfile.gettempdir()+"/selfsub/formula%s_false.v" % (last_update))
        inputstr = ''
        selfsub_inputstr = ''
        selfsub_declarestr = ''
        for i in range(len(Xvar) + len(Yvar)):
            if i == var:
                inputstr += "# ,"
            else:
                if i not in selfsub:
                    if i in Yvar:
                        ij = Yvarnames[i]
                    else:
                        ij = Xvarnames[i]

                    inputstr += "i%s ," % (ij)
                    selfsub_inputstr += "i%s ," % (ij)
                    selfsub_declarestr += "input i%s;\n" % (ij)

        write_str_true = "module FORMULA" + \
            str(var) + "_true ( " + selfsub_inputstr + " out);\n"
        write_str_false = "module FORMULA" + \
            str(var) + "_false ( " + selfsub_inputstr + " out);\n"
        write_str = selfsub_declarestr + "output out;\n"
        write_str += "wire one;\n" + "assign one = 1;\n"
        write_str += "wire zero;\n" + "assign zero = 0;\n"
        write_str += "wire out1;\n" + "wire out2;\n"
        formula_true = inputstr.replace("#", "one")
        formula_true1 = "FORMULA%s_true F%s ( %sout1 );\n" % (
            last_update, last_update, formula_true)
        formula_true2 = "FORMULA%s_false F%s ( %sout2 );\n" % (
            last_update, last_update, formula_true)
        formula_false = inputstr.replace("#", "zero")
        formula_false1 = "FORMULA%s_false F%s( %sout2 );\n" % (
            last_update, last_update, formula_false)
        formula_false2 = "FORMULA%s_true F%s( %sout1 );\n" % (
            last_update, last_update, formula_false)
        file = open(tempfile.gettempdir()+"/selfsub/formula%s_true.v" % (var), "w")
        file.write(write_str_true + write_str + formula_true1 + formula_true2)
        file.write("assign out = out1 | out2 ;\n" + "endmodule\n")
        file.write(file_content_true + "\n")
        file.write(file_content_false + "\n")
        file.close()
        file = open(tempfile.gettempdir()+"/selfsub/formula%s_false.v" % (var), "w")
        file.write(write_str_false + write_str +
                   formula_false1 + formula_false2)
        file.write("assign out = out1 | out2 ;\n" + "endmodule\n")
        file.write(file_content_true + "\n")
        file.write(file_content_false + "\n")
        file.close()
        cmd = "./dependencies/file_write_verilog %s/selfsub/formula%s_true.v %s/selfsub/formula%s_true.v  > /dev/null 2>&1" % (
            tempfile.gettempdir(),var, tempfile.gettempdir(),var)
        os.system(cmd)
        cmd = "./dependencies/file_write_verilog %s/selfsub/formula%s_false.v %s/selfsub/formula%s_false.v  > /dev/null 2>&1" % (
            tempfile.gettempdir(), var, tempfile.gettempdir(),var)
        os.system(cmd)
        return_string = 'wire outsub%s ;\nFORMULA%s_true F%s_ ( %s outsub%s);\n' % (
            var, var, var, selfsub_inputstr, var)
    return return_string


class Experiment:

    def __init__(self, Yvar_map, Xvar_map, unates, Yvar_order, refine_var_log, selfsub, verilog_formula, dg):
        self.Yvar_map = Yvar_map
        self.Xvar_map = Xvar_map
        self.unates = unates
        self.Yvar_order = Yvar_order
        self.refine_var_log = refine_var_log
        self.selfsub = selfsub
        self.verilog_formula = verilog_formula
        self.dg = dg

    def refine(self, Experiment, refine_cnf_content, ind_var, modelx, modely, modelyp, unique_var):
        Yvar = sorted(self.Yvar_map.keys())
        Xvar = sorted(self.Xvar_map.keys())
        refineformula = {}
        itr = 0
        sat_var = []
        ind_var_list = ind_var.copy()
        beta_ind = {}
        mostly_sat = []
        while itr < len(ind_var):

            var = ind_var[itr]
            itr += 1
            self.refine_var_log[var] += 1
            
            yi = np.where(Yvar == var)[0][0]
            yi_model = modelyp[yi]

            yj_model = []
            yj_map = []
            allowed_y = []

            if var in sat_var:
            	continue

            if var in self.selfsub:
                continue

            if var in unique_var:
                continue

            if self.refine_var_log[var] > args.selfsubthres:
                if var not in self.selfsub:
                    if len(self.selfsub) == 0:
                        os.system("mkdir "+tempfile.gettempdir()+"/selfsub")
                    self.selfsub.append(var)
                    if len(self.selfsub) > 2:
                        print("self sub more than 2")
                        exit()
                    refineformula[var] = selfsubstitute(
                        self.Xvar_map.keys(), Yvar, var, yi, self.selfsub, self.verilog_formula,self.Xvar_map, self.Yvar_map)
                    continue

            # to constrain  G(X,Y) formula over \hat{Y},
            # \hat{Y}=\sigma[\hat{Y}]
            index = np.where(self.Yvar_order == var)[0][0]
            
            for tmp in range(index, len(Yvar)):
                
                temp_var = self.Yvar_order[tmp]
                yj = np.where(Yvar == temp_var)[0][0]
                if Yvar[yj] == var or Yvar[yj] in self.unates:
                    continue

                

                if Yvar[yj] in ind_var:
                    if Yvar[yj] in sat_var:
                        yj_model.append(modelyp[yj])
                    else:
                        if modelyp[yj] == 0:
                            yj_model.append(1)
                        else:
                            yj_model.append(0)
                else:
                    yj_model.append(modelyp[yj])
                yj_map.append(self.Yvar_map[Yvar[yj]])
                allowed_y.append(Yvar[yj])


            ret, models, beta_varlist = find_unsat_core(
                refine_cnf_content, var, self.Yvar_map[var], yi_model, yj_map, yj_model, self.Xvar_map, self.Yvar_map)

            if ret == 0:
                # formula G(X,Y) is sat and ind_var list is updated.
                sat_var.append(Yvar[yi])
                models = np.array(models)
                diff = np.bitwise_xor(modelyp, models)
                index = np.where(diff == 1)[0]
                temp = []
                for yk in index:
                	if (Yvar[yk] not in ind_var) and (Yvar[yk] not in self.unates):
                		temp.append(Yvar[yk])
                index = np.where(self.Yvar_order == Yvar[yi])[0][0]
                l = itr
                for tmp in range(index - 1, -1, -1):
                	var1 = self.Yvar_order[tmp]
                	if var1 in temp:
                		if var1 not in ind_var:
                			flag = 0
                			while (l < len(ind_var)):
                				temp_yvar = ind_var[l]
                				index1 = np.where(self.Yvar_order == temp_yvar)[0][0]
                				if index1 < tmp:
                					flag = 1
                					ind_var = np.insert(ind_var, l, var1)
                					break
                				l = l + 1
                			if flag == 0:
                				ind_var = np.append(ind_var, var1).astype(np.int)
                continue
            else:
                # generate Beta formula from unsat core variable list:
                betaformula = ''
                if args.verbose == 2:
                    print("in unsat core of %s X var %s and Y var %s",
                          var, beta_varlist.clistx, beta_varlist.clisty)
                for betavar in beta_varlist.clistx:
                    if modelx[betavar] == 0:
                        betaformula += "~i%s & " % (self.Xvar_map[Xvar[betavar]])
                    else:
                        betaformula += "i%s & " % (self.Xvar_map[Xvar[betavar]])
                for betavar in beta_varlist.clisty:
                    if Yvar[betavar] not in allowed_y:
                        continue

                    if Yvar[betavar] in ind_var:
                    	if Yvar[betavar] in sat_var:
                    		if(modelyp[betavar] == 0):
                    			betaformula += "~i%s & " % (self.Yvar_map[Yvar[betavar]])
                    		else:
                    			betaformula += "i%s & " % (self.Yvar_map[Yvar[betavar]])
                    		continue
                    	if itr-1 < np.where(ind_var == Yvar[betavar])[0][0]:
                    		sat_var.append(Yvar[betavar])
                    	if var in list(beta_ind.keys()):
                    		beta_ind[var].append(betavar)
                    	else:
                    		beta_ind[var] = [betavar]
                    	continue
                    if(modelyp[betavar] == 0):
                    	betaformula += "~i%s & " % (self.Yvar_map[Yvar[betavar]])
                    else:
                    	betaformula += "i%s & " % (self.Yvar_map[Yvar[betavar]])
                betaformula = betaformula.strip("& ")
                if var not in list(beta_ind.keys()):
                	assert(betaformula != "")
                refineformula[var] = betaformula
                del beta_varlist

        if args.verbose == 2:
            print(refineformula)

        for var in list(beta_ind.keys()):
        	for yvar_index in list(beta_ind[var]):
        		yvar = Yvar[yvar_index]
        		if yvar in sat_var:
        			if modelyp[yvar_index] == 0:
        				refineformula[var] += "& ~i%s " % (self.Yvar_map[Yvar[yvar_index]])
        			else:
        				refineformula[var] += "& i%s " % (self.Yvar_map[Yvar[yvar_index]])
        		else:
        			if modelyp[yvar_index] == 0:
        				refineformula[var] += "& ~i%s " % (self.Yvar_map[Yvar[yvar_index]])
        			else:
        				refineformula[var] += "& i%s " % (self.Yvar_map[Yvar[yvar_index]])
        		refineformula[var] = refineformula[var].strip("& ")
        	assert(refineformula[var]!= "")
        
        return refineformula, self.refine_var_log, self.selfsub


def maxsat_content(cnf_content, n):
    lines = cnf_content.split("\n")
    maxsat_cnf_content = ''
    for line in lines:
        line = line.strip("\n")
        if line == '':
            continue
        if line.startswith("c"):
            maxsat_cnf_content += line + "\n"
            continue
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            weight = numVar + 100
            line = line.replace("p cnf " + str(numVar) + " " + str(
                numCls), "p wcnf " + str(numVar) + " " + str(numCls + n) + " " + str(weight))
            maxsat_cnf_content += line + "\n"
            continue
        maxsat_cnf_content += str(weight) + " " + line + "\n"
    return weight, maxsat_cnf_content


def add_x_models(cnf_content, maxsat_cnf_content, maxsat_wt, Xvar_map, modelx):
    maxsatstr = ''
    cnfstr = ''
    itr = 0
    Xvar = Xvar_map.keys()
    Xvar = sorted(Xvar)
    for i in Xvar:
        if (modelx[itr] == 0):
            maxsatstr += str(maxsat_wt) + " -" + str(Xvar_map[i]) + " 0\n"
            cnfstr += "-" + str(Xvar_map[i]) + " 0\n"
        else:
            maxsatstr += str(maxsat_wt) + " " + str(Xvar_map[i]) + " 0\n"
            cnfstr += str(Xvar_map[i]) + " 0\n"
        itr += 1
    cnf_content = cnf_content.strip("\n") + "\n" + cnfstr
    maxsat_cnf_content += "\n" + maxsatstr
    return cnf_content, maxsat_cnf_content



def unate_skolemfunction(Xvar, Yvar, pos_unate, neg_unate):
    if args.qdimacs:
    	inputfile_name = args.input.split('/')[-1][:-8]
    else:
    	inputfile_name = args.input.split('/')[-1][:-2]
    candidateskf = {}

    skolemformula = tempfile.gettempdir() + \
        '/' + inputfile_name + \
        "_skolem.v"  # F(X,Y')
    inputstr = 'module SKOLEMFORMULA ('
    declarestr = ''
    assignstr = ''
    itr = 1
    for var in range(len(Xvar) + len(Yvar)):
        inputstr += "i%s, " % (var)
        if var in Xvar:
            declarestr += "input i%s;\n" % (var)
        if var in Yvar:
            declarestr += "output i%s;\n" % (var)
            if var in neg_unate:
                assignstr += "assign i%s = 0;\n" % (var)
            if var in pos_unate:
                assignstr += "assign i%s = 1;\n" % (var)
    inputstr += ");\n"
    f = open(skolemformula, "w")
    f.write(inputstr)
    f.write(declarestr)
    f.write(assignstr)
    f.write("endmodule")
    f.close()
    cmd = "./dependencies/file_write_verilog %s %s > /dev/null 2>&1  " % (
        skolemformula, skolemformula)
    os.system(cmd)

def unate_unique_skolemfunction(Xvar, Yvar, pos_unate, neg_unate, unique_var,def_unique, Xvar_name,Yvar_name):
    
    inputfile_name = args.input.split('/')[-1][:-8]
    candidateskf = {}

    skolemformula = tempfile.gettempdir() + \
        '/' + inputfile_name + \
        "_skolem.v"  # F(X,Y')
    inputstr = 'module SKOLEMFORMULA ('
    declarestr = ''
    assignstr = ''
    itr = 1
    for v in range(len(Xvar) + len(Yvar)):
        
        if v in Xvar:
            inputstr += "i%s, " % (Xvar_name[v])
            declarestr += "input i%s;\n" % (Xvar_name[v])
        if v in Yvar:
            declarestr += "output i%s;\n" % (Yvar_name[v])
            if v in neg_unate:
                assignstr += "assign i%s = 0;\n" % (Yvar_name[v])
            if v in pos_unate:
                assignstr += "assign i%s = 1;\n" % (Yvar_name[v])
    inputstr += ");\n"
    unique_assign = ''
    wire_assign = ''
    for v in unique_var:
        wire_assign += "wire wi%s;\n" %(Yvar_name[v])
        unique_assign += "assign i%s = wi%s;\n" %(Yvar_name[v],Yvar_name[v])

    f = open(skolemformula, "w")
    f.write(inputstr)
    f.write(declarestr)
    f.write(assignstr)
    f.write(wire_assign)
    f.write(def_unique)
    f.write(unique_assign)
    f.write("endmodule")
    f.close()
    cmd = "./dependencies/file_write_verilog %s %s > /dev/null 2>&1  " % (
        skolemformula, skolemformula)
    os.system(cmd)


def adaptive_samples(sample_cnf_content, Yvar_map, allvar_map):
    sample_cnf_content_one = ''
    sample_cnf_content_zero = ''
    bias = {}
    for var in Yvar_map.keys():
        sample_cnf_content_one += "w %d 0.9\n" % (Yvar_map[var])
        sample_cnf_content_zero += "w %d 0.1\n" % (Yvar_map[var])
    samples_one = get_sample_cms(
        allvar_map, sample_cnf_content + sample_cnf_content_one, 500)
    samples_zero = get_sample_cms(
        allvar_map, sample_cnf_content + sample_cnf_content_zero, 500)
    for var in Yvar_map.keys():
        len_one = count_nonzero(samples_one[:, var])
        p = round(float(len_one) / 500, 2)
        len_zero = count_nonzero(samples_zero[:, var])
        q = round(float(len_zero) / 500, 3)
        if 0.35 < p < 0.65 and 0.35 < q < 0.65:
            bias[var] = p
        else:
            bias[var] = 0.9
    return bias

def get_key(val,dicts):
    for key,value in dicts:
        if val == value:
            return key
    return(-1)

def gen_weighted_cnf(cnf_content, Xvar_map, Yvar_map, allvar_map,unique_var):

    lines = cnf_content.split("\n")
    sample_cnf_content = ''
    for line in lines:
        line = line.strip("\n")
        if line == '':
            continue
        if line.startswith("c"):
            sample_cnf_content += line + "\n"
            continue
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            line = line.replace("p cnf " + str(numVar) + " " + str(numCls), "p cnf " + str(
                numVar) + " " + str(numCls + len(Xvar_map.keys()) + len(Yvar_map.keys())))
            sample_cnf_content += line + "\n"
            continue
        sample_cnf_content += line + "\n"
    for var in Xvar_map.keys():
        sample_cnf_content += "w %d 0.5\n" % (Xvar_map[var])
    if args.adaptivesample:
        bias_y = adaptive_samples(sample_cnf_content, Yvar_map, allvar_map)
        for var in Yvar_map.keys():
            sample_cnf_content += "w %d %f\n" % (Yvar_map[var], bias_y[var])
    else:
        for var in Yvar_map.keys():
        	if var in unique_var:
        		sample_cnf_content += "w %d 0.5\n" % (Yvar_map[var])
        	else:
        		sample_cnf_content += "w %d 0.9\n" % (Yvar_map[var])
    return sample_cnf_content


def convert_verilog(input):
    inputfile_name = args.input.split('/')[-1][:-8]
    verilogfile = inputfile_name+".v"
    orderfile = inputfile_name+"._varstoelim.txt"


    with open(args.input, 'r') as f:
        qdimacs_formula = f.read()
    f.close()


    with open(args.input, 'r') as f:
        lines = f.readlines()
    f.close()
    
    qdimacs_formula = qdimacs_formula.replace('a ','c ret ')
    qdimacs_formula = qdimacs_formula.replace('e ','c ind ')

    wire_clause=''
    assign_wire=''
    declare="module FORMULA ("
    declare_input=""
    clause=[]
    qdimacs_list = []
    count_var = 0
    Xvar_map = {}
    Yvar_map = {}
    dg = nx.DiGraph()  # dag to handle dependencies
    
    e_var_list=''
    H_set = {}
    dqbf_Y_var = []
    qbf_Y_var = []
    i=1
    for line in lines:
        line = line.strip(" ")
        
        if (line == "") or (line == "\n"):
            continue
        
  
        if line.startswith("c "):
        	continue
        
        if line.startswith("p cnf"):
            continue
        
        if line.startswith('a'):
            all_var=line.strip("a").strip(" ").strip("\n").split(" ")[:-1]
            for var in all_var:
                declare +="v_%s, " %(var)
                declare_input +="input v_%s;\n" %(var)
                Xvar_map[count_var] = int(var)
                count_var += 1
            continue
        
        if line.startswith('e'):
            e_var=line.strip("e").strip(" ").strip("\n").split(" ")[:-1]
            for var in e_var:
                e_var_list += "v_%s\n" %(var)
                declare +="v_%s, " %(var)
                declare_input +="input v_%s;\n" %(var)
                Yvar_map[count_var] = int(var)
                dg.add_node(count_var)
                count_var += 1
            continue    
        
        qdimacs_clause = []
        wire_clause += "wire x_%s;\n" %(i)
        clause.append("x_%s" %(i))
        assign_wire += "assign x_%s = " %(i)
        i=i+1
        line_vars=line.strip(" \n").split(" ")[:-1]
        polarity={}
        for var in line_vars:
            qdimacs_clause.append(int(var))
            flag=0
            
            if "-" in var:
                flag=1
                var=var.strip("-")
                polarity[int(var)]=-1
            else:
                polarity[int(var)]=1

            if (int(var) in Xvar_map.values()) or (int(var) in Yvar_map.values()):
                if flag == 1:
                    assign_wire += "~v_%s | " %(var)
                else:
                    assign_wire += "v_%s | " %(var)
            else:
            	print(int(var))

        assign_wire = assign_wire.strip("| ")+";\n"
        if len(qdimacs_clause)>0:
        	qdimacs_list.append(qdimacs_clause)

    x_string=''
    xassign=''
    outstr=''
    temp_wire=""
    itr=1
    while(itr<=len(clause)):
        flag=0
        x_string += clause[itr-1]+" & "
        if itr% 100 ==0:
            flag=1
            temp_wire +="wire xt_%s;\n" %(itr)
            x_string = x_string.strip("& ")
            xassign += "assign xt_"+str(itr)+" = "+x_string+";\n"
            outstr += "xt_%s & " %(itr)
            x_string=''
        itr +=1
    if flag==0:
        temp_wire +="wire xt_%s;\n" %(itr)
        x_string = x_string.strip("& ")
        xassign += "assign xt_"+str(itr)+" = "+x_string+";\n"
        outstr += "xt_%s & " %(itr)
    outstr = "assign out = "+outstr.strip("& ")+";\n"

    declare += "out);\n"
    declare_input +="output out;\n"
    verilog_formula = declare + declare_input + wire_clause + assign_wire + temp_wire + xassign + outstr + "endmodule\n"
    file_write = open(verilogfile,"w")
    file_write.write(verilog_formula.strip("\n"))
    file_write.close()

    file_write=open(orderfile,"w")
    file_write.write(e_var_list)
    file_write.close()
    return verilogfile, verilog_formula, qdimacs_formula, qdimacs_list, orderfile,  Xvar_map, Yvar_map, dg
    


def call_unique(qdimacs_list, Xvar_name, Yvar_name, dg, unates):
    declare_wire = ''
    defination_unique_var = ''
    Yvar_value = list(map(int, list(Yvar_name.values())))
    Xvar_value = list(map(int,list(Xvar_name.values())))   
    offset = 5*(len(Yvar_value)+len(Xvar_value))+100
    unique = []
    count_unique = 0
    Yvar = sorted(list(Yvar_name.keys()))
    checker = DefinabilityChecker(qdimacs_list,Yvar_value)
    max_len = 0
    start = time.time()
    defining_y_variables = []
    
    for j in Yvar:
	    defining_y_variables.append(int(Yvar_name[j]))


    for i in range(len(Yvar)):
    	var = Yvar[i]

    	defining_y_variables_var = defining_y_variables[:i]

    	if var in unates:
    		continue

    	defination = checker.checkDefinability(Xvar_value+defining_y_variables_var,int(Yvar_name[var]),offset)
    	count_offset = 0
    	if defination[0] == True:
            unique.append(var)
            if len(defination[1]) > max_len:
            	max_len = len(defination[1])
            
            for lists in defination[1]:
                clause = lists[0]
                    
                if isinstance(clause,list):
                    temp_str = ''
                    for def_var in clause:
                        if abs(def_var) in Yvar_value:
                            def_y_var = list(Yvar_name.keys())[Yvar_value.index(abs(def_var))]
                            dg.add_edge(var,abs(def_y_var))
                            if def_var > 0:
                                temp_str += "wi%s & " %(abs(def_var))
                            else:
                                temp_str += "~wi%s & " %(abs(def_var))
                        else:
                            if abs(def_var) in Xvar_value:
                                if def_var > 0:
                                    temp_str += "i%s & " %(abs(def_var))
                                else:
                                    temp_str += "~i%s & " %(abs(def_var))
                            else:
                                if def_var > 0:
                                    temp_str += "utemp%s & " %(abs(def_var))
                                else:
                                    temp_str += "~utemp%s & " %(abs(def_var))
                    

                    if len(defination[1]) > 1:
                        

                        if lists[1] not in Yvar_value:
                            count_offset += 1
                            declare_wire += "wire utemp%s;\n" %(lists[1])
                            defination_unique_var += "assign utemp%s = %s;\n " %(lists[1],temp_str.strip("& "))
                        else:
                            defination_unique_var += "assign wi%s = %s;\n" %(lists[1],temp_str.strip("& "))
                    else:
                    	count_offset += 1
                    	def_var  = clause[0]
                    	temp_str = ''
                    	if def_var < 0:
                    		temp_str += "~"
                    	
                    	if abs(def_var) in Xvar_value:
                    		temp_str += "i%s;\n" %(abs(def_var))
                    	else:
                    		if abs(def_var) in Yvar_value:
                    			temp_str += "wi%s;\n" %(abs(def_var))
                    		else:
                    			print("problem\n",defination)
                    			exit()

                    	defination_unique_var += "assign wi%s = %s" %(int(Yvar_name[var]),temp_str)
                    	
                else:
                	if clause > 0:
                		defination_unique_var += "assign wi%s = one ;\n" %(abs(clause))
                	else:
                		defination_unique_var += "assign wi%s = zero ;\n" %(abs(clause))
                	count_offset += 1
    	offset += count_offset+100

    if args.verbose:
    	print("Total unates",len(unates))
    	print("Total unique variable",len(unique))
    	print("Total Y variable",len(Yvar))
    	print("unique/total_y",round(len(unique)/len(Yvar),2))
    	print("maximum interpolant size",max_len)
    	print("total time taken %s seconds" %(round(time.time()-start,2)))
    if args.logtime:
    	write_to_logfile("Total-unates: "+str(len(unates)))
    	write_to_logfile("Total-unique: "+str(len(unique)))
    	write_to_logfile("Total-Y-var: "+str(len(Yvar)))
    	write_to_logfile("Unique/Total-Y-var: "+str(round(len(unique)/len(Yvar),2)))
    	write_to_logfile("maximum interpolant size: "+str(max_len))
    	write_to_logfile("total unique-finding-time: "+str(round(time.time()-start,2)))
    f = open("check_unique","w")
    f.write(defination_unique_var)
    f.close()
    return declare_wire.strip("\n")+defination_unique_var, unique, dg



def sub_skolem(skolemformula, Xvar, Yvar, def_unique, Xvar_map, Yvar_map):
    with open(skolemformula, 'r') as f:
        lines = f.readlines()
    f.close()

    declare = ''
    assign = ''
    for var in range(len(Xvar) + len(Yvar)):
        if var in Xvar:
            declare += "input i%s;\n" % (Xvar_map[var])
        if var in Yvar:
            declare += "output i%s;\n" % (Yvar_map[var])
            assign += "assign i%s = wi%s;\n" % (Yvar_map[var], Yvar_map[var])
    skolemcontent = ""
    flag = 0
    for line in lines:
        if line.startswith("input"):
            if flag == 0:
                skolemcontent += declare
                skolemcontent += def_unique
                flag = 1
            continue
        if line.startswith("output"):
            continue
        if line.startswith('assign out'):
            skolemcontent += assign
        else:
            skolemcontent += line

    f = open(skolemformula, "w")
    f.write(skolemcontent)
    f.close()
    cmd = "./dependencies/file_write_verilog %s %s > /dev/null 2>&1  " % (
        skolemformula, skolemformula)
    os.system(cmd)







def manthan():

    verilogfile, verilog_formula, qdimacs_formula, qdimacs_list, orderfile, Xvar_map, Yvar_map, dg = convert_verilog(args.input)

    inputfile_name = args.input.split('/')[-1][:-8]
    allvar_map = list(Xvar_map.values()) + list(Yvar_map.values())
    Xvar = list(Xvar_map.keys())
    Yvar = list(Yvar_map.keys())
    pos_unate = []
    neg_unate = []
    unates = []
    Xvar = np.array(Xvar)
    Yvar = np.array(Yvar)
    
    if args.logtime:
    	write_to_logfile("file : " + str(args.input))
    start = time.time()
   
    if args.preprocess:
    	print("preprocessing...")
    	pos_unate, neg_unate, unates = preprocess(verilogfile, orderfile, Yvar)

    if args.logtime:
        write_to_logfile("preprocesing time : " + str(time.time() - start))
    

    # if all Y variables are unate
    if len(pos_unate) + len(neg_unate) == len(Yvar):
        print(len(pos_unate) + len(neg_unate))
        print("positive unate", len(pos_unate))
        print("all Y variables are unates")
        print("Solved !! done !")
        unate_skolemfunction(Xvar, Yvar, pos_unate, neg_unate)
        
        skolemformula = tempfile.gettempdir() + \
            '/' + inputfile_name + "_skolem.v"
        exists = os.path.isfile(skolemformula)
        
        if exists:
            os.system("cp " + skolemformula +
                      " " + inputfile_name + "_skolem.v")
        
        if args.logtime:
        	write_to_logfile("Total-unates: "+str(len(Yvar)))
        	write_to_logfile("Total-unique: "+str(0))
        	write_to_logfile("Total-Y-var: "+str(len(Yvar)))
        	write_to_logfile("Unique/Total-Y-var: "+str(0))
        	write_to_logfile("maximum interpolant size: "+str(0))
        	write_to_logfile("total unique-finding-time: "+str(0))
        	write_to_logfile("sampling time : " + str(0))
        	write_to_logfile("Candidate time : " + str(0))
        	write_to_logfile("refinement time : " + str(0))
        	write_to_logfile("rev sub time : " + str(0))
        	write_to_logfile("total time : " + str(time.time() - start))
        exists = os.path.isfile("strash.txt")
        if exists:
            os.unlink("strash.txt")
        exists = os.path.isfile("variable_mapping.txt")
        if exists:
            os.unlink("variable_mapping.txt")
        return

    Xvar = np.sort(Xvar)
    Yvar = np.sort(Yvar)

    if args.unique:
    	print("finding defination...")
    	for i in pos_unate:
    		var = int(Yvar_map[i])
    		qdimacs_list.append([var])
    	for i in neg_unate:
    		var = int("-"+str(Yvar_map[i]))
    		qdimacs_list.append([var])
    	def_unique, unique_var, dg = call_unique(qdimacs_list, Xvar_map, Yvar_map, dg, pos_unate + neg_unate)
    else:
        def_unique = ''
        unique_var = []
        if args.logtime:
            write_to_logfile("Total-unates: 0")
            write_to_logfile("Total-unique: 0")
            write_to_logfile("Total-Y-var: 0")
            write_to_logfile("Unique/Total-Y-var: 0")
            write_to_logfile("maximum interpolant size: 0")
            write_to_logfile("total unique-finding-time: 0")

    if len(pos_unate)+ len(neg_unate)+len(unique_var) == len(Yvar):
        print("all variables either unate or unique. Found Skolem functions\n")
        if args.logtime:
            write_to_logfile("sampling time : " + str(0))
            write_to_logfile("Candidate time : " + str(0))
            write_to_logfile("refinement time : " + str(0))
            write_to_logfile("rev sub time : " + str(0))
            write_to_logfile("total time : " + str(time.time() - start))
            unate_unique_skolemfunction(Xvar, Yvar, pos_unate, neg_unate,unique_var,def_unique, Xvar_map, Yvar_map)
        
            skolemformula = tempfile.gettempdir() + \
                '/' + inputfile_name + "_skolem.v"
            exists = os.path.isfile(skolemformula)
            
            if exists:
                os.system("cp " + skolemformula +
                          " " + inputfile_name + "_skolem.v")

            return


        

    # to sample, we need a cnf file and variable mapping coressponding to


    cnffile = args.input.split('/')[-1][:-8] + ".cnf"

    # to add c ind and positive and negative unate in cnf
    qdimacs_formula = qdimacs_formula.replace("c ret ", "c ind ")
    fixedvar = ''
    unates = []
    for i in pos_unate:
        fixedvar += "%s 0\n" % (Yvar_map[i])
        unates.append(i)
    for i in neg_unate:
        fixedvar += "-%s 0\n" % (Yvar_map[i])
        unates.append(i)
    
    '''if flag != 1:
        fixedvar += "%s 0\n" % (1)  # output variable always true.'''


    lines = qdimacs_formula.split("\n")
    cnf_content = ''
    for line in lines:
        line = line.strip(" \n")
        if line.startswith("c"):
        	continue
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            line = line.replace("p cnf " + str(numVar) + " " + str(
                numCls), "p cnf " + str(numVar) + " " + str(numCls  + len(unates)))
            cnf_content += line + "\n"
            continue
        cnf_content += line + "\n"
    cnf_content = cnf_content.strip("\n")
    cnf_content = cnf_content + "\n" + fixedvar 

    #print("cnf_content",cnf_content)
    

    # generate sample
    start_t = time.time()
    if SAMPLER_CMS:
        sample_cnf_content = cnf_content
        if args.samples:
            no_samples = args.maxSamples
        else:
            if(len(Yvar) + len(Xvar) < 1200):
                no_samples = 10000
            if(len(Yvar) + len(Xvar) > 1200 and len(Yvar) + len(Xvar) < 4000):
                no_samples = 5000
            if(len(Yvar) + len(Xvar) > 4000):
                no_samples = 1000

        print("generating samples ", no_samples)
        if args.weighted:
            sample_cnf_content = gen_weighted_cnf(
                cnf_content, Xvar_map, Yvar_map, allvar_map,unique_var)
        samples = get_sample_cms(allvar_map, sample_cnf_content, no_samples)

    if args.logtime:
    	write_to_logfile("sampling time : " + str(time.time() - start_t))

    # phase two : learn candidate skolem functions using decision tree based
    # algo
    print("leaning candidate skolem functions..")
    start_t = time.time()

    dg = learn_skf(samples, Xvar, Yvar, pos_unate, neg_unate, unique_var, dg, def_unique, Xvar_map, Yvar_map)
    
    if args.logtime:
    	write_to_logfile("Candidate time : " + str(time.time() - start_t))

    # find order
    Yvar_order = np.array(list(nx.topological_sort(dg)))

    assert(len(Yvar_order) == len(Yvar))
    if args.verbose == 2:
        print("total order of Y variables", Yvar_order)

    # create error formula : E(X,Y,Y') = F(X,Y) \land \lnot F(X,Y')
    error_content, refine_var_log = create_error_formula(
        Xvar, Yvar, unique_var, verilog_formula)

    # phase 3: refinement and verfiy
    maxsat_wt, maxsat_cnf_content = maxsat_content(
        cnf_content, (len(Xvar) + len(Yvar) - len(unates)))

    refine_itr = 0
    selfsub = []
    ref = Experiment(Yvar_map=Yvar_map, Xvar_map=Xvar_map, unates=unates,
                     Yvar_order=Yvar_order, refine_var_log=refine_var_log,
                     selfsub=selfsub, verilog_formula=verilog_formula, dg=dg)
    start_t = time.time()
    refine_repeat_var = np.zeros(len(Yvar), dtype=int)
    first_refine = 0
    while True:
        add_skolem_to_errorformula(error_content, ref.selfsub)

        # sat call to errorformula:
        check, sigma, ret = verify(Xvar, Yvar, unique_var)
        # phase three : Refinement

        if check == 0:
            print("error...ABC network read fail")
            print("Skolem functions not generated")
            print("not solved !!")
            break

        if ret == 0:
            print("total number of refinement needed", refine_itr)
            print('error formula unsat.. skolem functions generated')
            print("number of selfsub",len(selfsub))

            if args.logtime:
            	write_to_logfile("refinement time : " + str(time.time() - start_t))

            start_t = time.time()
            skolemformula = tempfile.gettempdir(
            ) + '/' + inputfile_name + "_skolem.v"
            
            #sub_skolem(skolemformula, Xvar, Yvar, Yvar_order, verilog_formula, ref.selfsub, def_unique)
            if len(ref.selfsub) == 0:
                print("self sub zero")
                print("Skolem function")
                sub_skolem(skolemformula, Xvar, Yvar, def_unique, Xvar_map, Yvar_map)

            exists = os.path.isfile(skolemformula)
            print("skolem function: %s_skolem.v" %(inputfile_name))
            if exists:
                os.system(
                    "cp " + skolemformula + " " + inputfile_name + "_skolem.v")
            if args.logtime:
            	write_to_logfile(
                	"reverse sub time : " + str(time.time() - start_t))
            os.system("rm -rf selfsub")
            break

        else:

            if args.verbose == 2:
                print("x models", sigma.modelx)
                print("y models", sigma.modely)
                print("yp models", sigma.modelyp)
                print("ymap", Yvar_map.values())
                print("xmap", Xvar_map.values())

            if args.verbose:
                print("error formula is sat.. refining skolem functions..")
                print("calling MaxSAT to find candidate error skolem functions..")


            refine_itr = refine_itr + 1



            assert len(sigma.modelx) == len(Xvar)
            assert len(sigma.modely) == len(Yvar)
            assert len(sigma.modelyp) == len(Yvar)

            refine_cnf_content, refine_maxsat_content = add_x_models(
                cnf_content, maxsat_cnf_content, maxsat_wt, Xvar_map, sigma.modelx)

            print("calling open-wbo:maxsat to find candidates to repair")
            ind_var = call_maxsat(refine_maxsat_content, Yvar, Yvar_map,
                                  sigma.modelyp, sigma.modely, unates, unique_var, Yvar_order, ref.selfsub, maxsat_wt)


            assert len(ind_var) > 0

            print("refinement number", refine_itr)
            print("no of variables undergoing refinement:", len(ind_var))
            if args.verbose:
                print("variables undergoing refinement", ind_var)

            refineformula, ref.refine_var_log, ref.selfsub = ref.refine(
                Experiment, refine_cnf_content, ind_var, sigma.modelx, sigma.modely, sigma.modelyp, unique_var)

            skolemformula = tempfile.gettempdir(
            ) + '/' + inputfile_name + "_skolem.v"

            with open(skolemformula, 'r') as f:
                lines = f.readlines()
            f.close()
            skolemcontent = "".join(lines)

            # refine the candidates with refineformula(beta)
            for refine_var_yvar in refineformula.keys():
                refine_var = Yvar_map[int(refine_var_yvar)]
                if refine_var_yvar in ref.selfsub:
                    psi_refine_var_old = [line for line in lines if "assign wi" + str(refine_var)+" " in line][0]
                    psi_refine_var = refineformula[
                        refine_var_yvar] + "assign wi%s = outsub%s;\n" % (refine_var, refine_var_yvar)
                    skolemcontent = skolemcontent.replace(
                        psi_refine_var_old, psi_refine_var)
                    continue

                psi_refine_var_old = [
                    line for line in lines if "assign wi" + str(refine_var)+" " in line][0]

                psi_refine_var = psi_refine_var_old.rstrip(
                    ';\n').lstrip("assign wi%s = " % (refine_var))

                psi_refine_var = "wire beta%s_%s;\nassign beta%s_%s = %s;\nassign wi%s = (%s " \
                    % (refine_var, refine_itr, refine_var, refine_itr, refineformula[refine_var_yvar], refine_var, psi_refine_var)
                


                if sigma.modelyp[np.where(Yvar == refine_var_yvar)[0][0]] == 0:
                    psi_refine_var += "| (beta%s_%s));\n" \
                        % (refine_var, refine_itr)

                else:
                    psi_refine_var += "& ~(beta%s_%s));\n" \
                        % (refine_var, refine_itr)

                skolemcontent = skolemcontent.replace(
                    psi_refine_var_old, psi_refine_var)

            f = open(skolemformula, "w")
            f.write(skolemcontent)
            f.close()

            if refine_itr == args.refineitr:
            	print("Did not construct correct Skolem function---stoping due to number of refinement reached %s" %(args.refineitr))
            	print("consructing learned functions so far...")
            	sub_skolem(skolemformula, Xvar, Yvar, def_unique, Xvar_map, Yvar_map)
            	exists = os.path.isfile(skolemformula)
            	if exists:
            		os.system("cp " + skolemformula + " " + inputfile_name + "_skolem.v")
            		print("Find skolem function at %s_skolem.v" %(inputfile_name))
            	break
    if args.logtime:
    	write_to_logfile("total number of refinement: "+str(refine_itr))
    	write_to_logfile("total time : " + str(time.time() - start))
    exists = os.path.isfile("strash.txt")
    if exists:
    	os.unlink("strash.txt")
    exists = os.path.isfile("variable_mapping.txt")
    if exists:
    	os.unlink("variable_mapping.txt")
    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    
    parser.add_argument('--seed', type=int, default=1, dest='seed')
    parser.add_argument('--verb', type=int, help="0 ,1 ,2", dest='verbose')
    parser.add_argument(
        '--gini', type=float, help="minimum impurity drop, default = 0.005", default=0.005, dest='gini')
    parser.add_argument('--weighted', type=int, default=1,
                        help="weighted sampling: 1; uniform sampling: 0; default 1", dest='weighted')
    parser.add_argument('--refineitr', type=int, default=1000,
                        help="maximum allowed refinement iterations; default 1000", dest='refineitr')
    parser.add_argument('--selfsubthres', type=int, default=30,
                        help="self substitution threshold", dest='selfsubthres')
    parser.add_argument('--adaptivesample', type=int, default=0,
                        help="required --weighted to 1: to enable/disable adaptive weighted sampling ", dest='adaptivesample')
    parser.add_argument('--showtrees', action='store_true',
                        help="To see the decision trees")
    parser.add_argument('--samples', action='store_true')
    parser.add_argument('--maxsamp', type=int, default=1000,
                        help="samples used to learn: manthan will use this only if --samples is used", dest='maxSamples')
    parser.add_argument('--logtime', type=int, default=1,
                        help="to log the time taken by individual module", dest='logtime')
    parser.add_argument("--preprocess",action='store_true')
    parser.add_argument("--unique", action='store_true')
    parser.add_argument("input", help="input file")
    args = parser.parse_args()
    
    print("starting Manthan")
    
    manthan()
