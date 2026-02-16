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
try:
    import pydotplus  # optional, only needed for --showtrees
except ImportError:
    pydotplus = None
import networkx as nx
from collections import OrderedDict
from numpy import count_nonzero
from src import runtime_env  # noqa: F401
from src.logging_utils import cprint
import collections
import sys
import re
import os


def candidateYDeps(expr):
    """Return Y-variable dependencies (w<var> references) used in a candidate expression."""
    return sorted(set(int(v) for v in re.findall(r"\bw(\d+)\b", expr)))


def _normalize_candidate_expr(expr):
    expr = expr.replace("\r", " ").replace("\n", " ")
    expr = re.sub(r"\b1'b1\b", "1", expr)
    expr = re.sub(r"\b1'b0\b", "0", expr)
    expr = re.sub(r"\bone\b", "1", expr)
    expr = re.sub(r"\bzero\b", "0", expr)
    expr = " ".join(expr.split())
    return " %s " % expr.strip()


def _candidate_expr_supported(expr):
    # Keep this strict: imported expressions must be self-contained boolean formulas
    # over i<var>/w<var> plus constants and operators.
    ids = re.findall(r"[A-Za-z_][A-Za-z0-9_]*", expr)
    for tok in ids:
        if re.fullmatch(r"[iw]\d+", tok):
            continue
        return False
    if re.search(r"[^0-9A-Za-z_~&|() \t]", expr):
        return False
    return True


def loadCandidateSkfFromVerilog(path, allowed_vars=None, verbose=0):
    """
    Load candidate definitions from a Verilog skolem file.

    Expected form: assign w<var> = <expr>;
    Returns a dict {var: expr} for vars in allowed_vars (if provided).
    """
    if not os.path.isfile(path):
        raise FileNotFoundError(path)

    with open(path, "r") as f:
        content = f.read()

    # Strip comments first to avoid false positives.
    content = re.sub(r"/\*.*?\*/", " ", content, flags=re.S)
    content = re.sub(r"//.*", " ", content)

    allowed = set(allowed_vars) if allowed_vars is not None else None
    loaded = {}
    skipped_unsupported = []
    skipped_filtered = 0
    w_seen = 0
    w_loaded = 0
    abc_seen = 0
    abc_loaded = 0
    assign_re = re.compile(r"assign\s+w(\d+)\s*=\s*(.*?);", flags=re.S)
    for m in assign_re.finditer(content):
        w_seen += 1
        var = int(m.group(1))
        if (allowed is not None) and (var not in allowed):
            skipped_filtered += 1
            continue
        expr = _normalize_candidate_expr(m.group(2))
        if not _candidate_expr_supported(expr):
            skipped_unsupported.append(var)
            continue
        loaded[var] = expr
        w_loaded += 1

    if not loaded:
        # Fallback for ABC-written SKOLEMFORMULA style:
        #   output i<k>; assign i<k> = <expr>;
        # where indices are often 0-based variable ids.
        output_indices = set()
        for blk in re.finditer(r"\boutput\b(.*?);", content, flags=re.S):
            output_indices.update(int(v) for v in re.findall(r"\bi(\d+)\b", blk.group(1)))
        if output_indices:
            # ABC often emits intermediate nets (`new_n...`) in output assignments.
            # Inline these nets so imported candidates become pure boolean formulas.
            assign_map = {}
            for m in re.finditer(r"assign\s+([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?);", content, flags=re.S):
                assign_map[m.group(1)] = m.group(2).strip()
            abc_seen = len(output_indices)

            id_re = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
            i_tok_re = re.compile(r"i\d+")
            resolved = {}

            def _resolve_expr(expr_text, visiting):
                expr_text = re.sub(r"\b1'b1\b", "1", expr_text)
                expr_text = re.sub(r"\b1'b0\b", "0", expr_text)
                expr_text = re.sub(r"\b1'h1\b", "1", expr_text)
                expr_text = re.sub(r"\b1'h0\b", "0", expr_text)
                out = []
                last = 0
                for m_id in id_re.finditer(expr_text):
                    out.append(expr_text[last:m_id.start()])
                    tok = m_id.group(0)
                    if i_tok_re.fullmatch(tok):
                        out.append(tok)
                    elif tok in assign_map:
                        sub = _resolve_symbol(tok, visiting)
                        if sub is None:
                            return None
                        out.append("( %s )" % sub)
                    else:
                        return None
                    last = m_id.end()
                out.append(expr_text[last:])
                expr_out = " ".join("".join(out).split())
                if re.search(r"[^0-9A-Za-z_~&|() \t]", expr_out):
                    return None
                return expr_out

            def _resolve_symbol(sym, visiting):
                if sym in resolved:
                    return resolved[sym]
                if sym in visiting:
                    return None
                rhs = assign_map.get(sym)
                if rhs is None:
                    return None
                visiting.add(sym)
                expr = _resolve_expr(rhs, visiting)
                visiting.remove(sym)
                resolved[sym] = expr
                return expr

            def _rewrite_i_tokens(expr_text):
                def repl(m_i):
                    idx = int(m_i.group(1))
                    mapped = idx + 1
                    if idx in output_indices:
                        return "w%s" % mapped
                    return "i%s" % mapped
                return re.sub(r"\bi(\d+)\b", repl, expr_text)

            for idx in sorted(output_indices):
                var = idx + 1
                if (allowed is not None) and (var not in allowed):
                    skipped_filtered += 1
                    continue
                expr_resolved = _resolve_symbol("i%s" % idx, set())
                if expr_resolved is None:
                    skipped_unsupported.append(var)
                    continue
                expr = _rewrite_i_tokens(expr_resolved)
                expr = _normalize_candidate_expr(expr)
                if not _candidate_expr_supported(expr):
                    skipped_unsupported.append(var)
                    continue
                loaded[var] = expr
                abc_loaded += 1

    if verbose:
        cprint(
            "c [learnCandidate] import summary: "
            "w-style seen=%s loaded=%s, abc-style seen=%s loaded=%s, "
            "filtered=%s, unsupported=%s, total_loaded=%s"
            % (
                w_seen,
                w_loaded,
                abc_seen,
                abc_loaded,
                skipped_filtered,
                len(set(skipped_unsupported)),
                len(loaded),
            )
        )
        if skipped_unsupported:
            cprint("c [learnCandidate] skipped unsupported imported candidates for vars:", sorted(set(skipped_unsupported)))
    return loaded


def treepaths(root, is_leaves, children_left, children_right, data_feature_names, feature, values, dependson, leave_label, Xvar, Yvar, index, size,args):
    if (is_leaves[root]):
        if not args.multiclass:
            temp = values[root]
            temp = temp.ravel()
            if(temp[1] < temp[0]):
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
    def _unique_count(arr):
        arr = np.asarray(arr)
        if arr.ndim <= 1:
            return np.unique(arr).size
        try:
            return np.unique(arr, axis=0).shape[0]
        except TypeError:
            return len(set(tuple(row) for row in arr.tolist()))

    def _fit_with_gini(gini_value):
        model = tree.DecisionTreeClassifier(
            criterion='gini',
            min_impurity_decrease=gini_value,
            random_state=args.seed)
        return model.fit(featuredata, labeldata)

    gini_start = float(args.gini)
    gini_schedule = [gini_start]
    if gini_start > 0:
        gini_schedule.append(gini_start / 10.0)
        gini_schedule.append(gini_start / 100.0)
        gini_schedule.append(0.0)
    # Deduplicate while preserving order.
    seen = set()
    gini_schedule = [g for g in gini_schedule if not (g in seen or seen.add(g))]

    target_unique = _unique_count(labeldata)
    clf = None
    chosen_gini = gini_schedule[0]
    for idx, gini_value in enumerate(gini_schedule):
        clf = _fit_with_gini(gini_value)
        chosen_gini = gini_value
        if not getattr(args, "auto_gini", 1):
            break
        if target_unique <= 1:
            break
        pred_unique = _unique_count(clf.predict(featuredata))
        # If labels vary but model predicts only one value, lower gini and retry.
        if pred_unique > 1:
            break
        if idx < len(gini_schedule) - 1 and getattr(args, "verbose", 0) >= 1:
            cprint(
                "c [learnCandidate] auto-lowering gini for Yset %s: %s -> %s (non-constant labels, constant prediction)"
                % (yvar, gini_value, gini_schedule[idx + 1])
            )
    if getattr(args, "verbose", 0) >= 2 and chosen_gini != gini_start:
        cprint("c [learnCandidate] using lowered gini %s for Yset %s" % (chosen_gini, yvar))

    if args.showtrees:
        if pydotplus is None:
            cprint("c [learnCandidate] error: pydotplus is not installed; --showtrees requires it")
            sys.exit(1)
        else:
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
        node_values = np.asarray(clf.tree_.value[node_id]).reshape(-1)
        classes = clf.classes_[0] if isinstance(clf.classes_, list) else clf.classes_
        leave_label[node_id] = int(classes[int(np.argmax(node_values))])
        if (children_left[node_id] != children_right[node_id]):
            stack.append((children_left[node_id], parent_depth + 1))
            stack.append((children_right[node_id], parent_depth + 1))
        else:
            is_leaves[node_id] = True
    
    D_dict = {}
    psi_dict = {}

    for i in range(len(yvar)):
        D = []
        paths, D = treepaths(0, is_leaves, children_left, children_right, featname, feature, values, D, leave_label, Xvar, Yvar, i, len(yvar), args)
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
        paths = [p.strip() for p in paths if p and p.strip()]
        if len(paths) == 0:
            paths = ["0"]
            D = []

        psi_i = " | ".join("( " + path + " )" for path in paths)
        D_dict[yvar[i]] = D
        psi_dict[yvar[i]] = psi_i.strip()
    if args.verbose >= 2:
        cprint("c [learnCandidate] candidate functions for Y variables are", psi_dict)
    return psi_dict, D_dict
         

def binary_to_int(lst):
	lst = np.array(lst)
	# filling the begining with zeros to form bytes
	diff = 8 - lst.shape[1] % 8
	if diff > 0 and diff != 8:
		lst = np.c_[np.zeros((lst.shape[0],diff),int),lst]
	label = np.packbits(lst,axis=1)
	return label

def learnCandidate(Xvar, Yvar, UniqueVars, PosUnate, NegUnate, samples, dg, ng, args, seed_candidates=None):
    
    candidateSkf = dict(seed_candidates or {})
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
        if (var in UniqueVars) or (var in PosUnate) or (var in NegUnate) or (var in candidateSkf):
            continue
        if args.multiclass:
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
        if args.verbose >= 2:
            cprint("c [learnCandidate] Learning candidate Skolem functions for Y variables:", Yset)
        dependent = []
        for yvar in Yset:
            depends_on_yvar = list(nx.ancestors(dg,yvar))
            depends_on_yvar.append(yvar)
            dependent = dependent + depends_on_yvar
        Yfeatname = list(set(Yvar)-set(dependent))
        featname= Xvar + Yfeatname
        if Yfeatname:
            Samples_Y = samples[:, (np.array(Yfeatname, dtype=int) - 1)]
        else:
            Samples_Y = samples[:, :0]
        featuredata = np.concatenate((samples_X,Samples_Y),axis=1)
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
        cprint("c [learnCandidate] generated candidate functions for all variables.")

    if args.verbose >= 1:
        cprint("c [learnCandidate] candidate functions are", candidateSkf)
    return candidateSkf, dg    
