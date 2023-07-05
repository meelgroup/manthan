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

import numpy as np
from sklearn import tree
import pydotplus
import networkx as nx
from collections import OrderedDict
from numpy import count_nonzero
import collections


def treepaths(root, is_leaves, children_left, children_right, data_feature_names, feature, values, dependson, leave_label, Xvar, Yvar, index, size,args):
    if (is_leaves[root]):
        if not args.multiclass:
            temp = values[root]
            temp = temp.ravel()
            if len(temp) == 1:
                return(['1'], dependson)
            if temp[1] < temp[0]:
                return(['val=0'], dependson)
            else:
                return(['1'], dependson)
        else:
            node_label = leave_label[root]
            bool_res = format(node_label,"0"+str(size)+"b")
            if int(bool_res[index]):
                return (["1"],dependson)
            else:
                return(["val=0"],dependson)
    	


    left_subtree, dependson = treepaths(
        children_left[root], is_leaves, children_left,
        children_right, data_feature_names, feature, values, dependson,leave_label, Xvar, Yvar, index, size,args)
    right_subtree, dependson = treepaths(
        children_right[root], is_leaves, children_left,
        children_right, data_feature_names, feature, values, dependson,leave_label, Xvar, Yvar, index, size,args)

    # conjunction of all the literal in a path where leaf node has label 1
    # Dependson is list of Y variables on which candidate SKF of y_i depends
    list_left = []
    for leaf in left_subtree:
        if leaf != "val=0":
            if data_feature_names[feature[root]] in Yvar:
                dependson.append(data_feature_names[feature[root]])
            # the left part
                list_left.append("~w" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
            else:
                list_left.append("~i" + str(data_feature_names[feature[root]]) + ' & ' + leaf)
           
    list_right = []
    for leaf in right_subtree:
        if leaf != "val=0":
            if data_feature_names[feature[root]] in Yvar:
                dependson.append(data_feature_names[feature[root]])
                list_left.append("w"+str(data_feature_names[feature[root]]) + ' & ' + leaf)
            else:
                list_left.append("i"+str(data_feature_names[feature[root]]) + ' & ' + leaf)
    dependson = list(set(dependson))
    return(list_left + list_right, dependson)

def createDecisionTree(featname, featuredata, labeldata, yvar, args, Xvar, Yvar):
    clf = tree.DecisionTreeClassifier(
        criterion='gini',
        min_impurity_decrease=args.gini, random_state=args.seed)
    clf = clf.fit(featuredata, labeldata)
    if args.showtrees:
        dot_data = tree.export_graphviz(clf,
                                        feature_names=featname,
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
        graph.write_png(str(yvar) + ".png")
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
    
    D_dict = {}
    psi_dict = {}

    for i in range(len(yvar)):
        D = []
        paths, D = treepaths( 0, is_leaves, children_left, children_right, featname, feature, values, D, leave_label, Xvar, Yvar, i, len(yvar),args)
        psi_i = ''

        if is_leaves[0]:
            if len(yvar) == 1:
                len_one = count_nonzero(labeldata)
                if len_one >= int(len(labeldata)/2):
                    paths = ["1"]
                else:
                    paths = ["0"]
            else:
                if "val=0" in paths:
                    paths = ["0"]
                else:
                    paths = ["1"]  
        if len(paths) == 0:
            paths.append("0")
            D = []

        for path in paths:
            psi_i += "( "+ path + " ) | " 
        D_dict[yvar[i]] = D
        psi_dict[yvar[i]] = psi_i.strip("| ")
    
    return psi_dict, D_dict
         

def binary_to_int(lst):
	lst = np.array(lst)
	# filling the begining with zeros to form bytes
	diff = 8 - lst.shape[1] % 8
	if diff > 0 and diff != 8:
		lst = np.c_[np.zeros((lst.shape[0],diff),int),lst]
	label = np.packbits(lst,axis=1)
	return label

def learnCandidate(Xvar, Yvar, UniqueVars, PosUnate, NegUnate, samples, dg, ng, args):
    
    candidateSkf = {}
    samples_X = samples[:, (np.array(Xvar)-1)]
    disjointSet = []
    clusterY = []

    for var in PosUnate:
        candidateSkf[var] = " 1 "
        if (args.multiclass) and (var in list(ng.nodes)):
            ng.remove_node(var)
    
    for var in NegUnate:
        candidateSkf[var] = " 0 "
        if (args.multiclass) and (var in list(ng.nodes)):
            ng.remove_node(var)
        
    for var in UniqueVars:
        if (args.multiclass) and (var in list(ng.nodes)):
            ng.remove_node(var)
    
    for var in Yvar:
        if (var in UniqueVars) or (var in PosUnate) or (var in NegUnate):
            continue
        if args. multiclass:
            if var in list(ng.nodes):
                Yset = []
                hoppingDistance = args.hop
                while (hoppingDistance > 0):
                    hop_neighbour = list(nx.single_source_shortest_path_length(ng,var,cutoff = hoppingDistance))
                    if len(hop_neighbour) < args.clustersize:
                        break
                    else:
                        hop_neighbour = []
                    hoppingDistance -= 1
                
                if len(hop_neighbour) == 0:
                    hop_neighbour = [var]
                
                for var2 in hop_neighbour:
                    ng.remove_node(var2)
                    Yset.append(var2)
                    clusterY.append(var2)
                disjointSet.append(Yset)
            else:
                if var not in clusterY:
                    disjointSet.append([var])
        else:
            disjointSet.append([var])
    
    for Yset in disjointSet:
        dependent = []
        for yvar in Yset:
            depends_on_yvar = list(nx.ancestors(dg,yvar))
            depends_on_yvar.append(yvar)
            dependent = dependent + depends_on_yvar
        Yfeatname = list(set(Yvar)-set(dependent))
        if len(Yfeatname) > 0:
            featname= Xvar + Yfeatname
            Samples_Y = samples[:,(np.array(Yfeatname)-1)]
            featuredata = np.concatenate((samples_X,Samples_Y),axis=1)
        else:
            featname = Xvar
            featuredata = samples_X
        label = samples[:,(np.array(Yset)-1)]
        labeldata = binary_to_int(label)
        functions, D_set = createDecisionTree(featname, featuredata, labeldata, Yset, args, Xvar, Yvar)

        for var in functions.keys():
            assert(var not in UniqueVars)
            assert(var not in PosUnate)
            assert(var not in NegUnate)
            candidateSkf[var] = functions[var]
            D = list(set(D_set[var])-set(Xvar))
            for jvar in D:
                dg.add_edge(var, jvar)

    if args.verbose:
        print("generated candidate functions for all variables.")

    if args.verbose == 2:
        print("candidate functions are", candidateSkf)

    return candidateSkf, dg    