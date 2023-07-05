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
from src.DefinabilityChecker import DefinabilityChecker
from dependencies.rc2 import RC2Stratified
from pysat.formula import WCNF
import pydotplus

from collections import OrderedDict


from src.convert_verilog import convert_verilog
from src.preprocess import *
from src.callUnique import find_unique_function
from src.createSkolem import *
from src.generateSamples import *
from src.candidateSkolem import *
from src.repair import *


def logtime(inputfile, text):
    with open(inputfile+"time_details", "a+") as f:
        f.write(text + "\n")
    f.close()


def manthan():
    print("parsing")
    start_time = time.time()

    if args.henkin:
        Xvar, Yvar, HenkinDep, qdimacs_list, dg = parse(args)
    
    else:
        Xvar, Yvar, qdimacs_list, dg = parse(args)

    '''
        We create a DAG to handle dependencies among existentially quantified variables
        if y_i depends on y_j, there is a edge from y_i to y_j
    '''
    
    

    if args.verbose:
        print("count X (universally qunatified variables) variables", len(Xvar))
        print("count Y (existentially qunatified variables) variables", len(Yvar))

    
    
    inputfile_name = args.input.split('/')[-1][:-8]  
    cnffile_name = tempfile.gettempdir()+"/"+inputfile_name+".cnf"

    cnfcontent = convertcnf(args.input, cnffile_name)
    cnfcontent = cnfcontent.strip("\n")+"\n"

    if (args.preprocess) and (not (args.henkin)):
        print("preprocessing: finding unates (constant functions)")
        start_time_preprocess = time.time()
        
        '''
        We find constants functions only if the existentially quantified variables are less then 20000
        else it takes way much time to find the constant functions.
        '''
        
        if len(Yvar) < 20000:
            PosUnate, NegUnate = preprocess(cnffile_name)
        else:
            print("too many Y variables, let us proceed with Unique extraction\n")
            PosUnate = []
            NegUnate = []
            
        end_time_preprocess = time.time()
        logtime(inputfile_name, "preprocessing time:"+str(end_time_preprocess-start_time_preprocess))

        if args.verbose:
            print("count of positive unates", len(PosUnate))
            print("count of negative unates", len(NegUnate))
            if args.verbose >= 2:
                print("positive unates", PosUnate)
                print("negative unates", NegUnate)

        Unates = PosUnate + NegUnate

        '''
        Adding unates in the specification as constants.
        This might help samplers to produce good data

        '''
        
        for yvar in PosUnate:
            qdimacs_list.append([yvar])
            cnfcontent += "%s 0\n" % (yvar)

        for yvar in NegUnate:
            qdimacs_list.append([-1 * int(yvar)])
            cnfcontent += "-%s 0\n" % (yvar)

    else:
        Unates = []
        PosUnate = []
        NegUnate = []
        print("preprocessing is disabled. To do preprocessing, please use --preprocess")

    if len(Unates) == len(Yvar):
        print("all Y variables are unates and have constant functions")
        
        '''
        Generating verilog files to output Skolem functions.
        '''
        
        skolemfunction_preprocess(inputfile_name,
            Xvar, Yvar, PosUnate, NegUnate)
        
        end_time = time.time()
        print("Manthan has synthesized Skolem functions")
        print("Total time taken", str(end_time-start_time))
        logtime(inputfile_name, "totaltime:"+str(end_time-start_time))
        exit()

    
    

    if args.unique:
        print("finding uniquely defined functions")
        start_time_unique = time.time()

        if args.henkin:
            UniqueVars, UniqueDef, dg = find_unique_function(args, 
                qdimacs_list, Xvar, Yvar, dg, Unates, HenkinDep)
        else:
            UniqueVars, UniqueDef, dg = find_unique_function(args, 
                qdimacs_list, Xvar, Yvar, dg, Unates)
        
        end_time_unique = time.time()
        
        logtime(inputfile_name, "unique function finding:"+str(end_time_unique-start_time_unique))

        if args.verbose:
            print("count of uniquely defined variables", len(UniqueVars))
            
            if args.verbose >= 2:
                print("uniquely defined variables", UniqueVars)
    else:
        
        UniqueVars = []
        UniqueDef = ''
        print("finding unique function is disabled. To find unique functions please use -- unique")

    if len(Unates) + len(UniqueVars) == len(Yvar):

        print("all Y variables are either unate or unique")
        print("found functions for all Y variables")

        skolemfunction_preprocess(inputfile_name, Xvar, Yvar, PosUnate, NegUnate, UniqueVars, UniqueDef)
        
        end_time = time.time()
        logtime(inputfile_name, "totaltime:"+str(end_time-start_time))
        exit()

    

    '''
    deciding the number of samples to be generated
    '''
    start_time_datagen = time.time()
    sampling_cnf = cnfcontent

    if not args.maxsamples:
        if len(Xvar) > 4000:
            num_samples = 1000
        if (len(Xvar) > 1200) and (len(Xvar) <= 4000):
            num_samples = 5000
        if len(Xvar) <= 1200:
            num_samples = 10000
    else:
        num_samples = args.maxsamples

    '''
    We can either choose uniform sampler or weighted sampler.
    In case of weighted sampling, we need to find adaptive weights for each positive literals
    including X and Y.
    '''

    if args.adaptivesample:

        '''
        sampling_weights_y_1 is to bias outputs towards 1
        sampling_weights_y_o is to bias outputs towards 0

        '''

        sampling_weights_y_1 = ''
        sampling_weights_y_0 = ''
        for xvar in Xvar:
            sampling_cnf += "w %s 0.5\n" % (xvar)
        for yvar in Yvar:
            
            '''
            uniquely defined variables are now treated as "inputs"
            '''
            if yvar in UniqueVars:
                sampling_cnf += "w %s 0.5\n" % (yvar)
                continue
            
            if (yvar in PosUnate) or (yvar in NegUnate):
                continue

            sampling_weights_y_1 += "w %s 0.9\n" % (yvar)
            sampling_weights_y_0 += "w %s 0.1\n" % (yvar)

        
        weighted_sampling_cnf = computeBias(
            Xvar, Yvar, sampling_cnf, sampling_weights_y_1, sampling_weights_y_0, inputfile_name, Unates + UniqueVars, args)
        

        print("generating weighted samples")
        samples = generatesample(
            args, num_samples, weighted_sampling_cnf, inputfile_name, 1)
    else:
        print("generating uniform samples")
        samples = generatesample(
            args, num_samples, sampling_cnf, inputfile_name, 0)

    end_time_datagen = time.time()
    logtime(inputfile_name, "generating samples:"+str(end_time_datagen-start_time_datagen))

    
    print("generated samples.. learning candidate functions via decision learning")

    '''
    we need verilog file for repairing the candidates, hence first let us convert the qdimacs to verilog
    ng is used only if we are doing multiclassification. It has an edge only if y_i and y_j share a clause
    this is used to cluster the variables for which functions could be learned together.
    '''
    
    verilogformula, dg, ng = convert_verilog(args.input, args.multiclass, dg)


    start_time_learn = time.time()

    candidateSkf, dg = learnCandidate(
        Xvar, Yvar, UniqueVars, PosUnate, NegUnate, samples, dg, ng, args)

    end_time_learn = time.time()
    
    logtime(inputfile_name, "candidate learning:"+str(end_time_learn-start_time_learn))

    '''
    YvarOrder is a total order of Y variables that represents interdependecies among Y. 
    '''

    YvarOrder = np.array(list(nx.topological_sort(dg)))

    assert(len(Yvar) == len(YvarOrder))

    '''
    createSkolem here represents candidate Skolem functions for each Y variables
    in a verilog format.
    '''
    createSkolem(candidateSkf, Xvar, Yvar, UniqueVars,
                 UniqueDef, inputfile_name)

    error_content = createErrorFormula(Xvar, Yvar, UniqueVars, verilogformula)

    
    '''
    We use maxsat to identify the candidates to repair. We are converting specification as a hard constraint for maxsat.
    '''
    maxsatWt, maxsatcnf, cnfcontent = maxsatContent(
        cnfcontent, (len(Xvar)+len(Yvar)), (len(PosUnate)+len(NegUnate)))

    countRefine = 0

    start_time_repair = time.time()

    while True:
        
        '''
        adding Y' <-> f(X) term in the error formula
        '''

        addSkolem(error_content, inputfile_name)

        '''
        sigma [0]: valuation for X
        sigma [1]: valuation for Y
        sigma [2]: valuation for Y' where Y' <-> f(X)

        '''
        
        check, sigma, ret = verify(Xvar, Yvar, inputfile_name)
        
        if check == 0:
            print("error --- ABC network read fail")
            break
        
        if ret == 0:
            print("verification check UNSAT")
            
            if args.verbose:
                print("no more repair needed")
                print("number of repairs needed to converge", countRefine)
            
            createSkolemfunction(inputfile_name, Xvar, Yvar)
            break
        
        if ret == 1:

            countRefine += 1 #update the number of repair itr

            print("verification check is SAT, we have counterexample to fix")
            
            if args.verbose:
                print("number of repair", countRefine)
                print("finding candidates to repair using maxsat")

            repaircnf, maxsatcnfRepair = addXvaluation(
                cnfcontent, maxsatWt, maxsatcnf, sigma[0], Xvar)

            ind = callMaxsat(
                maxsatcnfRepair, sigma[2], UniqueVars, Unates, Yvar, YvarOrder, inputfile_name, args.weightedmaxsat)

            assert(len(ind) > 0)

            
            if args.verbose:
                print("number of candidates undergoing repair iterations", len(ind))
            
            if args.verbose >= 2:
                print("number of candidates undergoing repair iterations", len(ind))
                print("variables undergoing refinement", ind)

            lexflag, repairfunctions = repair(
                repaircnf, ind, Xvar, Yvar, YvarOrder, UniqueVars, Unates, sigma, inputfile_name, args, args.lexmaxsat)
            
            '''

            if we encounter too many repair candidates while repair the previous identifed candidates ind, 
            we call lexmaxsat to identify nicer candidates to repair in accordance with the dependencies.
            
            '''

            if lexflag:
                print("calling rc2 to find another set of candidates to repair")
                
                ind = callRC2(maxsatcnfRepair,
                              sigma[2], UniqueVars, Unates, Yvar, YvarOrder)
                
                assert(len(ind) > 0)
                
                if args.verbose == 1:
                    print("number of candidates undergoing repair iterations", len(ind))
                lexflag, repairfunctions = repair(
                    repaircnf, ind, Xvar, Yvar, YvarOrder, UniqueVars, Unates, sigma, inputfile_name, args, 0)
            
            '''
            update the repair candidates in the candidate Skolem 
            
            '''
            
            updateSkolem(repairfunctions, countRefine,
                         sigma[2], inputfile_name, Yvar)
        
        if countRefine > args.maxrepairitr:
            print("number of maximum allowed repair iteration reached")
            print("could not synthesize functions")
            
            break
    
    end_time = time.time()
    
    logtime(inputfile_name, "repair time:"+str(end_time-start_time_repair))
    logtime(inputfile_name, "totaltime:"+str(end_time-start_time))


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument('--seed', type=int, default=10, dest='seed')
    parser.add_argument('--verb', type=int, help="0 ,1 ,2", default=1, dest='verbose')
    parser.add_argument(
        '--gini', type=float, help="minimum impurity drop, default = 0.005", default=0.005, dest='gini')
    parser.add_argument('--weightedsampling', type=int, default=1,
                        help="weighted sampling: 1; uniform sampling: 0; default 1", dest='weighted')
    parser.add_argument('--maxrepairitr', type=int, default=5000,
                        help="maximum allowed repair iterations; default 1000", dest='maxrepairitr')

    parser.add_argument('--adaptivesample', type=int, default=1,
                        help="required --weighted to 1: to enable/disable adaptive weighted sampling ", dest='adaptivesample')
    parser.add_argument('--showtrees', type=int, default=0,
                        help="To see the decision trees: 1; default 0", dest='showtrees')
    parser.add_argument('--maxsamples', type=int,
                        help="samples used to learn", dest='maxsamples')
    parser.add_argument("--preprocess", type=int, help="0 ,1 ", default=1, dest='preprocess')
    parser.add_argument("--multiclass", action='store_true')
    parser.add_argument("--lexmaxsat", action='store_true')
    parser.add_argument("--henkin", action='store_true')
    parser.add_argument("--hop", type=int, default=3, dest='hop')
    parser.add_argument("--clustersize", type=int,
                        default=8, dest='clustersize')
    parser.add_argument("--unique", type=int, help="0 ,1 ", default=1, dest='unique')
    parser.add_argument("input", help="input file")


    args = parser.parse_args()
    print("starting Manthan")
    
    manthan()
