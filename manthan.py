#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2020 Priyanka Golia, Subhajit Roy, and Kuldeep Meel
#
# This program is free software; you can redistribute it and/or
# modify it under the terms of the GNU General Public License
# as published by the Free Software Foundation; version 2
# of the License.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston, MA
# 02110-1301, USA.


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
import pydotplus
import time
import networkx as nx


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


def preprocess(varlistfile):
    inputfile_name = args.input.split(".v")[0]
    cmd = "./dependencies/preprocess -b %s -v %s > /dev/null 2>&1 " % (
        args.input, varlistfile)
    os.system(cmd)
    pos_unate = []
    neg_unate = []
    Xvar = []
    Yvar = []
    Xvar_map = []
    Yvar_map = []
    found_neg = 0
    exists = os.path.isfile(inputfile_name + "_vardetails")
    if exists:
        with open(inputfile_name + "_vardetails", 'r') as f:
            lines = f.readlines()
        f.close()
        for line in lines:
            if "Xvar " in line:
                Xvar = line.split(":")[1].strip(" \n").split(" ")
                Xvar = np.array(Xvar)
                Xvar = Xvar.astype(np.int)
                # first variable is 0 now, not 1
                Xvar = np.subtract(Xvar, 1)
                continue
            if "Yvar " in line:
                Yvar = line.split(":")[1].strip(" \n").split(" ")
                Yvar = np.array(Yvar)
                Yvar = Yvar.astype(np.int)
                # first variable is 0 now, not 1
                Yvar = np.subtract(Yvar, 1)
                continue
            if "Yvar_map " in line:
                Yvar_map = line.split(":")[1].strip(" \n").split(" ")
                Yvar_map = np.array(Yvar_map)
                Yvar_map = Yvar_map.astype(np.int)
                continue
            if "Xvar_map " in line:
                Xvar_map = line.split(":")[1].strip(" \n").split(" ")
                Xvar_map = np.array(Xvar_map)
                Xvar_map = Xvar_map.astype(np.int)
                continue
            if "Posunate" in line:
                pos = line.split(":")[1].strip(" \n")
                if pos != "":
                    pos_unate = pos.split(" ")
                    pos_unate = np.array(pos_unate)
                    pos_unate = pos_unate.astype(np.int)
                continue
            if "Negunate" in line:
                neg = line.split(":")[1].strip(" \n")
                if neg != "":
                    neg_unate = neg.split(" ")
                    neg_unate = np.array(neg_unate)
                    neg_unate = neg_unate.astype(np.int)
                continue
        if args.verbose:
            print("count X variables", len(Xvar))
            print("X variables", Xvar)
            print("count Y variables", len(Yvar))
            print("Y variables", Yvar)
            print("Xvar", Xvar)
            print("Yvar", Yvar)
            print("Xvar_map", Xvar_map)
            print("Yvar_map", Yvar_map)
            print("preprocessing ...")
            print("count positive unate", len(pos_unate))
            if len(pos_unate) > 0:
                print("positive unate Y variables", pos_unate)
            print("count negative unate", len(neg_unate))
            if len(neg_unate) > 0:
                print("negative unate Y variables", neg_unate)
            print("preprocess done")
            print("creating cnf file..")
        os.unlink(inputfile_name + "_vardetails")
    else:
        print("preprocessing error .. contining ")
    return(pos_unate, neg_unate, Xvar, Yvar, Xvar_map, Yvar_map)


def get_sample_cms(allvar_map, cnf_content, no_samples):
    inputfile_name = args.input.split('/')[-1][:-2]
    tempcnffile = tempfile.gettempdir() + '/' + inputfile_name + ".cnf"
    f = open(tempcnffile, "w")
    f.write(cnf_content)
    f.close()
    tempoutputfile = tempfile.gettempdir() + '/' + inputfile_name + "_.txt"
    if args.weighted:
        print("weighted samples....")
        cmd = "./dependencies/cryptominisat5 -n1 --sls 0 --comps 0"
        cmd += " --restart luby  --nobansol --maple 0 --presimp 0"
        cmd += " --polar weight --freq 0.9999 --verb 0 --scc 0"
        cmd += " --random %s --maxsol %s" % (args.seed, no_samples)
        cmd += " %s" % (tempcnffile)
        cmd += " --dumpresult %s > /dev/null 2>&1" % (tempoutputfile)
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


def treepaths(root, is_leaves, children_left, children_right, data_feature_names, feature, values, dependson):
    if (is_leaves[root]):
        temp = values[root]
        temp = temp.ravel()
        if(temp[1] < temp[0]):
            return(['val=0'], dependson)
        else:
            return(['1'], dependson)
    left_subtree, dependson = treepaths(
        children_left[root], is_leaves, children_left,
        children_right, data_feature_names, feature, values, dependson)
    right_subtree, dependson = treepaths(
        children_right[root], is_leaves, children_left,
        children_right, data_feature_names, feature, values, dependson)

    # conjunction of all the literal in a path where leaf node has label 1
    # Dependson is list of Y variables on which candidate SKF of y_i depends
    list_left = []
    for leaf in left_subtree:
        if leaf != "val=0":
            dependson.append(data_feature_names[feature[root]])
            # the left part
            list_left.append(
                "~i" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
    list_right = []
    for leaf in right_subtree:
        if leaf != "val=0":
            dependson.append(data_feature_names[feature[root]])
            # the right part
            list_right.append(
                "i" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
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
    D = []  # y_i does not depend on any y_j
    if (is_leaves[0]):
        len_one = count_nonzero(label)
        if len_one >= int(len(label) / 2):
            paths = ["1"]  # Maximum label for class 1: tree no split
        else:
            paths = ["0"]  # Maximum label for class 0: tree no split
    else:
        paths, D = treepaths(
            0, is_leaves, children_left, children_right,
            feat_name, feature, values, D)
    psi_i = ''
    if len(paths) == 0:
        paths.append('0')
        D = []
    for path in paths:
        psi_i += "( " + path + " ) | "
    return(psi_i.strip("| "), D)


def learn_skf(samples, Xvar, Yvar, pos_unate, neg_unate, dg):

    # finding samples unique with respect to X variables.
    x_data, indices = np.unique(samples[:, Xvar], axis=0, return_index=True)
    samples = samples[indices, :]

    if args.verbose:
        print("candidateskf ..")

    # For create decision tree, we need feature names, feature data and label data
    inputFile = args.input
    inputfile_name = inputFile.split('/')[-1][:-2]
    candidateskf = {}
    for i in Yvar:
        feat_name = np.arange(len(Xvar) + len(Yvar))
        if i in neg_unate:
            candidateskf[i] = ' 0 '
            continue
        if i in pos_unate:
            candidateskf[i] = ' 1 '
            continue

        # In dag all ancestors of i^th node; depends on i^th node.
        # all y_j variables that depends on y_i
        dependent = list(nx.ancestors(dg, i))

        # selecting feature name, data and label
        dependent.append(i)
        feat_name = np.delete(feat_name, dependent, axis=0)
        feat_data = np.delete(samples, dependent, axis=1)

        label = samples[:, i]
        psi_i, D = create_decision_tree(feat_name, feat_data, label, i)
        D = list(set(D) - set(Xvar))
        # cyclic dependencies due to only Y variables
        candidateskf[i] = psi_i

        # update dependenciess:
        for j in D:
            dg.add_edge(i, j)

    if args.verbose:
        print("generated candidateskf for all Y")

    if args.verbose == 2:
        print("candidate Skolem functions:", candidateskf)

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
        inputstr += "i%s, " % (var)
        if var in Xvar:
            declarestr += "input i%s;\n" % (var)
        if var in Yvar:
            flag = 0
            declarestr += "input i%s;\n" % (var)
            wirestr += "wire wi%s;\n" % (var)
            assignstr += 'assign wi%s = (' % (var)
            temp = candidateskf[var].replace(
                " 1 ", " one ").replace(" 0 ", " zero ")
            assignstr += temp + ");\n"
            outstr += "(~(wi%s ^ i%s)) & " % (var, var)
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
    f.write(assignstr)
    f.write("endmodule")
    f.close()

    return dg


def call_maxsat(refine_maxsat_content, Yvar, Yvar_map, modelyp, modely, unates, Yvar_order, selfsub, maxsat_wt):

    maxsatstr = ''
    itr = 0
    for i in Yvar:
        if i not in unates:
            yindex = np.where(i == Yvar_order)[0][0]
            if i in selfsub:
                if (modely[itr] == 0):
                    maxsatstr += str(maxsat_wt) + " -" + str(
                        Yvar_map[i]) + " 0\n"
                else:
                    maxsatstr += str(maxsat_wt) + " " + str(
                        Yvar_map[i]) + " 0\n"
            else:
                if (modelyp[itr] == 0):
                    maxsatstr += str(1) + " -" + str(Yvar_map[i]) + " 0\n"
                else:
                    maxsatstr += str(1) + " " + str(Yvar_map[i]) + " 0\n"
        itr = itr + 1
    refine_maxsat_content += maxsatstr
    inputFile = args.input
    inputfile_name = inputFile.split('/')[-1][:-2]
    maxsatformula = tempfile.gettempdir() + \
        '/' + inputfile_name + "_maxsat.cnf"
    
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
                index = Yvar_map.keys()[Yvar_map.values().index(ymap)]
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
    inputFile = args.input
    inputfile_name = inputFile.split('/')[-1][:-2]
    skolemformula = tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v"
    with open(skolemformula, 'r') as f:
        skolemcontent = f.read()
    f.close()
    errorformula = tempfile.gettempdir() + \
        '/' + inputfile_name + "_errorformula.v"
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


def create_error_formula(Xvar, Yvar, verilog_formula):
    refine_var_log = {}
    # inputFile = args.input

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
            inputskolem += "ip%s, " % (var)
            inputerrory += "i%s, " % (var)
            inputerroryp += "ip%s, " % (var)
            declarey += "input i%s ;\n" % (var)
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


def verify(Xvar, Yvar):
    inputFile = args.input
    inputfile_name = inputFile.split('/')[-1][:-2]
    errorformula = tempfile.gettempdir() + \
        '/' + inputfile_name + "_errorformula.v"
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
            modelyp = templist[2]
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
    Yvar = Yvar_map.keys()
    Yvar_mapping = Yvar_map.values()
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

    inputFile = args.input
    inputfile_name = inputFile.split('/')[-1][:-2]

    # cnffile = tempfile.gettempdir()+'/'+inputfile_name+"_unsat.cnf"

    cnffile = "temp_unsat.cnf"
    f = open(cnffile, "w")
    f.write(refine_cnf_content)
    f.close()
    unsatcorefile = tempfile.gettempdir() + \
        '/' + inputfile_name + "_unsatcore.txt"
    satfile = tempfile.gettempdir() + '/' + inputfile_name + "_sat.txt"
    # unsatcorefile = "temp.txt"
    # satfile ="temp1.txt"
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
                clistx.append(Xvar_map.values().index(C))
                continue
            if C in Yvar_map.values():
                if C != yi_map:
                    clisty.append(Yvar_map.values().index(C))
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
        Yvar_mapping = np.subtract(Yvar_mapping, one).astype(np.int)
        with open(satfile, 'r') as f:
            content = f.read()
        f.close()
        os.unlink(satfile)
        os.unlink(cnffile)
        content = content.replace("s SATISFIABLE\n", "").replace(
            "v", "").replace("\n", "").strip(" \n")

        models = content.split(" ")
        models = np.array(models).astype(np.int)
        models = models[Yvar_mapping] > 1
        models = models.astype(np.int)
        if args.verbose == 1:
            print('formula is sat for', yi)
        return ret, models, beta


  
def selfsubstitute(Xvar, Yvar, var, yi, selfsub, verilog_formula):

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
                    yj = np.where(Yvar == i)[0][0]

                inputstr += "i%s ," % (i)
                selfsub_inputstr += "i%s ," % (i)
                selfsub_declarestr += "input i%s;\n" % (i)
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
                        yj = np.where(Yvar == i)[0][0]

                    inputstr += "i%s ," % (i)
                    selfsub_inputstr += "i%s ," % (i)
                    selfsub_declarestr += "input i%s;\n" % (i)

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

    def refine(self, Experiment, refine_cnf_content, ind_var, modelx, modely, modelyp, refine_repeat_var):
        Yvar = sorted(self.Yvar_map.keys())
        refineformula = {}
        itr = 0
        sat_var = []
        while itr < len(ind_var):

            var = ind_var[itr]
            itr += 1
            self.refine_var_log[var] += 1
            yi = np.where(Yvar == var)[0][0]
            yi_model = modelyp[yi]

            yj_model = []
            yj_map = []

            if var in self.selfsub:
                continue

            if self.refine_var_log[var] > args.selfsubthres or refine_repeat_var[yi] == 10:
                if var not in self.selfsub:
                    if len(self.selfsub) == 0:
                        os.system("mkdir "+tempfile.gettempdir()+"/selfsub")
                    self.selfsub.append(var)
                    refineformula[var] = selfsubstitute(
                        self.Xvar_map.keys(), Yvar, var, yi, self.selfsub, self.verilog_formula)
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
                    if Yvar[yk] not in ind_var and Yvar[yk] not in self.unates:
                        temp.append(Yvar[yk])
                index = np.where(self.Yvar_order == Yvar[yi])[0][0]
                l = itr + 1
                for tmp in range(index - 1, -1, -1):
                    var1 = self.Yvar_order[tmp]
                    if var1 in temp:
                        if var1 not in ind_var:
                            flag = 0
                            while (l < len(ind_var)):
                                temp_yvar = ind_var[l]
                                index1 = np.where(
                                    self.Yvar_order == temp_yvar)[0][0]
                                if index1 < tmp:
                                    flag = 1
                                    ind_var = np.insert(ind_var, l, var1)
                                    break
                                l = l + 1
                            if flag == 0:
                                ind_var = np.append(
                                    ind_var, var1).astype(np.int)

                continue
            else:
                # generate Beta formula from unsat core variable list:
                betaformula = ''
                index = np.where(self.Yvar_order == var)[0][0]
                # ancestors=nx.ancestors(self.dg,var)
                ancestors = self.Yvar_order[range(0, index)]
                # ancestors=[]
                if args.verbose == 2:
                    print("in unsat core of %s X var %s and Y var %s",
                          var, beta_varlist.clistx, beta_varlist.clisty)
                for betavar in beta_varlist.clistx:
                    if modelx[betavar] == 0:
                        betaformula += "~i%s & " % (
                            self.Xvar_map.keys()[betavar])
                    else:
                        betaformula += "i%s & " % (
                            self.Xvar_map.keys()[betavar])
                for betavar in beta_varlist.clisty:
                    if Yvar[betavar] in ancestors:
                        continue

                    if Yvar[betavar] in ind_var:
                        if Yvar[betavar] in sat_var:
                            if(modelyp[betavar] == 0):
                                betaformula += "~i%s & " % (
                                    self.Yvar_map.keys()[betavar])
                            else:
                                betaformula += "i%s & " % (
                                    self.Yvar_map.keys()[betavar])
                            continue
               
                        if(modelyp[betavar] == 0):
                            betaformula += "i%s & " % (
                                self.Yvar_map.keys()[betavar])
                        else:
                            betaformula += "~i%s & " % (
                                self.Yvar_map.keys()[betavar])
                        continue
          
                    if(modelyp[betavar] == 0):
                        betaformula += "~i%s & " % (
                            self.Yvar_map.keys()[betavar])
                    else:
                        betaformula += "i%s & " % (
                            self.Yvar_map.keys()[betavar])

                betaformula = betaformula.strip("& ")
                assert(betaformula != "")
                refineformula[var] = betaformula
                del beta_varlist

        if args.verbose == 2:
            print(refineformula)
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


def sub_skolem(skolemformula, Xvar, Yvar, Yvar_order, verilog_formula, selfsub):
    print("error formula unsat..reverse substituing...\n")

    with open(skolemformula, 'r') as f:
        lines = f.readlines()
    f.close()

    declare = ''
    assign = ''
    for var in range(len(Xvar) + len(Yvar)):
        if var in Xvar:
            declare += "input i%s;\n" % (var)
        if var in Yvar:
            declare += "output i%s;\n" % (var)
            assign += "assign i%s = wi%s;\n" % (var, var)
    skolemcontent = ""
    flag = 0
    for line in lines:
        if line.startswith("input"):
            if flag == 0:
                skolemcontent += declare
                flag = 1
            continue
        if line.startswith("output"):
            continue
        if line.startswith('assign out'):
            skolemcontent += assign
        else:
            skolemcontent += line

    skolemcontent_lines = skolemcontent.split("\n")
    for var in Yvar:
        if var in selfsub:
            continue
        yi_index = np.where(Yvar_order == var)[0]
        for i in range(len(skolemcontent_lines)):
            if skolemcontent_lines[i].startswith("assign beta%s_" % (var)) or skolemcontent_lines[i].startswith("assign wi%s" % (var)):

                tmp_state = skolemcontent_lines[i].split('=')[1]

                if "i" not in tmp_state:
                    continue

                for dep_var in selfsub:
                    yj_index = np.where(Yvar_order == dep_var)[0]

                    if (yj_index < yi_index):
                        continue

                    if " ~i%s &" % (dep_var) in skolemcontent_lines[i]:
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace(" ~i%s &" % (dep_var), "")

                    if " ~i%s;" % (dep_var) in skolemcontent_lines[i]:
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace(" & ~i%s;" % (dep_var), ";")
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace("~i%s;" % (dep_var), ";")

                    if " i%s &" % (dep_var) in skolemcontent_lines[i]:
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace(" i%s &" % (dep_var), "")

                    if " i%s;" % (dep_var) in skolemcontent_lines[i]:
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace(" & i%s;" % (dep_var), ";")
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace(" i%s;" % (dep_var), ";")

                    skolemcontent_lines[i] = skolemcontent_lines[
                        i].strip(";").strip(" ").strip("&")
                    skolemcontent_lines[i] += ";"
                    if "=" in skolemcontent_lines[i]:
                        sanity_check = skolemcontent_lines[i].split("=")
                        sanity_check[1] = sanity_check[1].strip(" ")

                        if sanity_check[1] == ";":
                            skolemcontent_lines[i] = ''

                    else:
                        skolemcontent_lines[i] = ""

                    if skolemcontent_lines[i].startswith("assign wi%s" % (var)):
                        temp_str = sanity_check[
                            0].split("assign")[1].strip(" ")
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace("& ~(%s)" % (temp_str), "")
                        skolemcontent_lines[i] = skolemcontent_lines[
                            i].replace("| (%s)" % (temp_str), "")

    skolemcontent = "\n".join(skolemcontent_lines)
    skolemcontent_write = ''
    if len(selfsub) != 0:
        for all_selfsub_var in selfsub:
            file_open = open(
                tempfile.gettempdir()+"/selfsub/formula%s_true.v" % (all_selfsub_var), "r")
            content = file_open.read()
            file_open.close()
            skolemcontent_write += "\n" + content
    f = open(skolemformula, "w")
    f.write(skolemcontent + "\n")
    f.write(verilog_formula)
    f.write(skolemcontent_write)
    f.close()
    cmd = "./dependencies/file_write_verilog %s %s > /dev/null 2>&1 " % (
        skolemformula, skolemformula)
    os.system(cmd)



def unate_skolemfunction(Xvar, Yvar, pos_unate, neg_unate):
    inputfile = args.input
    inputfile_name = inputfile.split('/')[-1][:-2]
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


def gen_weighted_cnf(cnf_content, Xvar_map, Yvar_map, allvar_map):

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
            sample_cnf_content += "w %d 0.9\n" % (Yvar_map[var])
    return sample_cnf_content


def manthan(samples, maxSamples, seed, verb, varlistfile, weighted):
    inputfile_name = args.input.split('/')[-1][:-2]
    Xvar = []
    Yvar = []
    varlist = [line.rstrip('\n')
               for line in open(varlistfile)]  # Y variable list
    dg = nx.DiGraph()  # dag to handle dependencies
    flag = 0
    verilog_formula = ''
    with open(args.input, 'r') as f:
        for x, line in enumerate(f):
            if line.startswith("module"):
                line_split = line.split("(")
                total_var = line_split[1].split(",")
                for var in range(len(total_var) - 1):
                    variable_check = total_var[var]
                    variable_check = variable_check.strip(" ").strip("\n")
                    if str(variable_check) in varlist:
                        Yvar.append(var)
                        dg.add_node(var)
                    else:
                        Xvar.append(var)
                modulename = line.split("(")[0].split(" ")[1]
                line = line.replace(modulename, "FORMULA")
            verilog_formula += line

    f.close()
    pos_unate = []
    neg_unate = []
    Xvar = np.array(Xvar)
    Yvar = np.array(Yvar)
    if args.logtime:
    	write_to_logfile("file : " + str(args.input))
    start = time.time()
    pos_unate_tmp, neg_unate_tmp, Xvar_tmp, Yvar_tmp, Xvar_map, Yvar_map = preprocess(varlistfile)

    # only if could not do preprocessing : proceed without preprocessing
    if len(Xvar_tmp) == 0 or len(Yvar_tmp) == 0:
        cmd = "./dependencies/file_generation_cnf %s %s.cnf %s_mapping.txt  > /dev/null 2>&1" % (
            inputFile, inputfile_name, inputfile_name)
        os.system(cmd)
        with open(inputfile_name + "_mapping.txt", 'r') as f:
            lines = f.readlines()
        f.close()
        for line in lines:
            allvar_map = line.strip(" \n").split(" ")
        os.unlink(inputfile_name + "_mapping.txt")
        allvar_map = np.array(allvar_map).astype(np.int)
        Xvar_map = dict(zip(Xvar, allvar_map[Xvar]))
        Yvar_map = dict(zip(Yvar, allvar_map[Yvar]))
        flag = 1
    else:
        Xvar = Xvar_tmp
        Yvar = Yvar_tmp
        Xvar_map = dict(zip(Xvar, Xvar_map))
        Yvar_map = dict(zip(Yvar, Yvar_map))
        Xvar = np.sort(Xvar)
        Yvar = np.sort(Yvar)
    for unate in pos_unate_tmp:
        pos_unate.append(Yvar_map.keys()[Yvar_map.values().index(unate)])
    for unate in neg_unate_tmp:
        neg_unate.append(Yvar_map.keys()[Yvar_map.values().index(unate)])
    
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
            os.system("rm *.txt")
        write_to_logfile("sampling time : " + str(0))
        write_to_logfile("Candidate time : " + str(0))
        write_to_logfile("refinement time : " + str(0))
        write_to_logfile("rev sub time : " + str(0))
        write_to_logfile("total time : " + str(time.time() - start))
        return

    # to sample, we need a cnf file and variable mapping coressponding to
    # varilog variables
    cnffile = args.input.split(".v")[0] + ".cnf"

    # to add c ind and positive and negative unate in cnf
    unates = []
    indIter = 1
    indStr = 'c ind '
    allvar_map = []
    for i in range(len(Xvar) + len(Yvar)):
        if i in Xvar:
            i_map = Xvar_map[i]
        if i in Yvar:
            i_map = Yvar_map[i]
        allvar_map.append(i_map)
        if indIter % 10 == 0:
            indStr += ' 0\nc ind '
        indStr += "%d " % i_map
        indIter += 1
    indStr += " 0\n"
    allvar_map = np.array(allvar_map)
    fixedvar = ''
    for i in pos_unate:
        fixedvar += "%s 0\n" % (Yvar_map[i])
        unates.append(i)
    for i in neg_unate:
        fixedvar += "-%s 0\n" % (Yvar_map[i])
        unates.append(i)
    with open(cnffile, 'r') as f:
        lines = f.readlines()
    f.close()
    if flag != 1:
        fixedvar += "%s 0\n" % (1)  # output variable always true.

    unates = np.sort(unates)
    cnf_content = ''
    for line in lines:
        line = line.strip(" \n")
        if line.startswith("c"):
            continue
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            line = line.replace("p cnf " + str(numVar) + " " + str(
                numCls), "p cnf " + str(numVar) + " " + str(numCls + len(unates) + 1))
        cnf_content += line + "\n"
    cnf_content = cnf_content.strip("\n")
    cnf_content = indStr + cnf_content + "\n" + fixedvar.rstrip(' \n')

    os.unlink(cnffile)

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
                cnf_content, Xvar_map, Yvar_map, allvar_map)
        samples = get_sample_cms(allvar_map, sample_cnf_content, no_samples)

    if args.logtime:
    	write_to_logfile("sampling time : " + str(time.time() - start_t))

    # phase two : learn candidate skolem functions using decision tree based
    # algo
    print("leaning candidate skolem functions..")
    start_t = time.time()
    dg = learn_skf(samples, Xvar, Yvar, pos_unate, neg_unate, dg)
    
    if args.logtime:
    	write_to_logfile("Candidate time : " + str(time.time() - start_t))

    # find order
    Yvar_order = np.array(list(nx.topological_sort(dg)))
    if args.verbose == 2:
        print("total order of Y variables", Yvar_order)

    # create error formula : E(X,Y,Y') = F(X,Y) \land \lnot F(X,Y')
    error_content, refine_var_log = create_error_formula(
        Xvar, Yvar, verilog_formula)

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
    while True:
        add_skolem_to_errorformula(error_content, ref.selfsub)

        # sat call to errorformula:
        check, sigma, ret = verify(Xvar, Yvar)
        # phase three : Refinement

        if check == 0:
            print("error...ABC network read fail")
            print("Skolem functions not generated")
            print("not solved !!")
            break

        if ret == 0:
            print("Total number of refinement needed", refine_itr)
            print('error formula unsat.. skolem functions generated')

            if args.logtime:
            	write_to_logfile("refinement time : " + str(time.time() - start_t))

            start_t = time.time()
            skolemformula = tempfile.gettempdir(
            ) + '/' + inputfile_name + "_skolem.v"
            sub_skolem(skolemformula, Xvar, Yvar, Yvar_order, verilog_formula, ref.selfsub)
            exists = os.path.isfile(skolemformula)
            print("Skolem functions: %s_skolem.v" %(inputfile_name))
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
                print(
                    "calling MaxSAT to find candidate error skolem functions..")

            refine_itr = refine_itr + 1

            assert len(sigma.modelx) == len(Xvar)
            assert len(sigma.modely) == len(Yvar)
            assert len(sigma.modelyp) == len(Yvar)

            refine_cnf_content, refine_maxsat_content = add_x_models(
                cnf_content, maxsat_cnf_content, maxsat_wt, Xvar_map, sigma.modelx)

            ind_var = call_maxsat(refine_maxsat_content, Yvar, Yvar_map,
                                  sigma.modelyp, sigma.modely, unates, Yvar_order, ref.selfsub, maxsat_wt)

            for y in range(len(Yvar)):
                if Yvar[y] in ind_var:
                    refine_repeat_var[y] = refine_repeat_var[y] + 1
                else:
                    refine_repeat_var[y] = 0

            assert len(ind_var) > 0

            print("refinement number", refine_itr)
            print("no of variables undergoing refinement:", len(ind_var))
            if args.verbose:
                print("variables undergoing refinement", ind_var)

            refineformula, ref.refine_var_log, ref.selfsub = ref.refine(
                Experiment, refine_cnf_content, ind_var, sigma.modelx, sigma.modely, sigma.modelyp, refine_repeat_var)

            skolemformula = tempfile.gettempdir(
            ) + '/' + inputfile_name + "_skolem.v"

            with open(skolemformula, 'r') as f:
                lines = f.readlines()
            f.close()
            skolemcontent = "".join(lines)

            # refine the candidates with refineformula(beta)
            for refine_var in refineformula.keys():

                if refine_var in ref.selfsub:
                    psi_refine_var_old = [
                        line for line in lines if "assign wi" + str(refine_var) in line][0]
                    psi_refine_var = refineformula[
                        refine_var] + "assign wi%s = outsub%s;\n" % (refine_var, refine_var)
                    skolemcontent = skolemcontent.replace(
                        psi_refine_var_old, psi_refine_var)
                    continue

                psi_refine_var_old = [
                    line for line in lines if "assign wi" + str(refine_var) in line][0]
                psi_refine_var = psi_refine_var_old.rstrip(
                    ';\n').lstrip("assign wi%s = " % (refine_var))

                psi_refine_var = "wire beta%s_%s;\nassign beta%s_%s = %s;\nassign wi%s = (%s " \
                    % (refine_var, refine_itr, refine_var, refine_itr, refineformula[refine_var], refine_var, psi_refine_var)

                if sigma.modelyp[np.where(Yvar == refine_var)[0][0]] == 0:
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

            if refine_itr == args.maxrefineitr:
                print("problem !! refinemenet itr > %d" % (args.maxrefineitr))
                print("not solved")
                break
    if args.logtime:
    	write_to_logfile("total time : " + str(time.time() - start))
    os.unlink("strash.txt")
    os.unlink("variable_mapping.txt")
    return


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    
    parser.add_argument('--seed', type=int, required=True, dest='seed')
    parser.add_argument('--verb', type=int, help="0 ,1 ,2", dest='verbose')
    parser.add_argument(
        '--gini', type=float, help="minimum impurity drop, default = 0.005", default=0.005, dest='gini')
    parser.add_argument(
        '--varlist', type=str, help="list of existensially quantified variables, Y", dest='varlist')
    parser.add_argument('--weighted', type=int, default=1,
                        help="weighted sampling: 1; uniform sampling: 0; default 1", dest='weighted')
    parser.add_argument('--maxrefineitr', type=int, default=1000,
                        help="maximum allowed refinement iterations; default 1000", dest='maxrefineitr')
    parser.add_argument('--selfsubthres', type=int, default=10,
                        help="self substitution threshold", dest='selfsubthres')
    parser.add_argument('--adaptivesample', type=int, default=0,
                        help="required --weighted to 1: to enable/disable adaptive weighted sampling ", dest='adaptivesample')
    parser.add_argument('--showtrees', type=int, default=0,
                        help="To see the decision trees: 1; default 0", dest='showtrees')
    parser.add_argument(
        '--samples', type=int, help=" set 1 to use given samples to learn, default 0;\n if 0 : manthan will decide number of samples as per |Y| ", default=0, dest='samples')
    parser.add_argument('--maxsamp', type=int, default=1000,
                        help="samples used to learn: manthan will use this only if --samples is set to 1", dest='maxSamples')
    parser.add_argument('--logtime', type=int, default=1,
                        help="to log the time taken by individual module", dest='logtime')
    parser.add_argument("input", help="input file")
    args = parser.parse_args()

    manthan(
        samples=args.samples,
        maxSamples=args.maxSamples,
        seed=args.seed,
        verb=args.verbose,
        varlistfile=args.varlist,
        weighted=args.weighted
        )
