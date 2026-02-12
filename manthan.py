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
import configparser
import math
import random
import argparse
import copy
import tempfile
import shutil
from src import runtime_env  # noqa: F401
from src.tempfiles import temp_path
import numpy as np
from numpy import count_nonzero
from sklearn import tree
import collections
import subprocess as subprocess
import time
import networkx as nx
from src.logging_utils import cprint
from pathlib import Path
import re
config = configparser.ConfigParser()
config.read("manthan_dependencies.cfg")
if config.has_option("ITP-Path", "itp_path"):
    sys.path.append(config["ITP-Path"]["itp_path"])

from src.DefinabilityChecker import DefinabilityChecker
from dependencies.rc2 import RC2Stratified
from pysat.formula import WCNF
import pydotplus

from collections import OrderedDict


from src.convert_verilog import convert_verilog
from src.preprocess import *
from src.callUnique import unique_function
from src.createSkolem import *
from src.selfsub import selfsubstitute
from src.generateSamples import *
from src.candidateSkolem import *
from src.repair import *


def manthan():
    cprint("c [manthan] parsing")
    start_time = time.time()
    status = "finished"
    def finish(status):
        cprint("c [manthan] %s" % (status))
    Xvar, Yvar, qdimacs_list = parse(args.input)

    cprint("c [manthan] count X variables", len(Xvar))
    cprint("c [manthan] count Y variables", len(Yvar))

    input_name = Path(args.input).name
    if input_name.endswith(".qdimacs"):
        output_stem = input_name[:-8]
    else:
        output_stem = Path(input_name).stem
    output_path = args.output or f"{output_stem}_skolem.v"
    temp_stem = re.sub(r"[^A-Za-z0-9_-]+", "_", output_stem).strip("_") or "manthan"
    last_errorformula_path = os.path.abspath(temp_stem + "_errorformula_last.v")

    cnffile_name = temp_path(temp_stem + ".cnf")

    cnfcontent = convertcnf(args.input, cnffile_name)
    cnfcontent = cnfcontent.strip("\n")+"\n"

    if args.preprocess == 1:
        cprint("c [manthan] preprocessing: finding unates (constant functions)")
        start_t = time.time()
        if getattr(args, "debug_keep", False):
            preprocess_cnf_path = os.path.abspath(temp_stem + "_preprocess.cnf")
            shutil.copyfile(cnffile_name, preprocess_cnf_path)
            if getattr(args, "verbose", 0) >= 1:
                cprint("c [manthan] saved preprocess cnf:", preprocess_cnf_path)
        if len(Yvar) < 20000:
            PosUnate, NegUnate = preprocess(cnffile_name)
        else:
            cprint("c [manthan] too many Y variables, let us proceed with Unique extraction")
            PosUnate = []
            NegUnate = []
        end_t = time.time()
        if args.verbose:
            cprint("c [manthan] count of positive unates", len(PosUnate))
            cprint("c [manthan] count of negative unates", len(NegUnate))
            if args.verbose >= 2:
                cprint("c [manthan] positive unates", PosUnate)
                cprint("c [manthan] negative unates", NegUnate)

        Unates = PosUnate + NegUnate

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
        cprint("c [manthan] preprocessing is disabled. To do preprocessing, please use --preprocess=1")

    if len(Unates) == len(Yvar):
        cprint("c [manthan] positive unates", PosUnate)
        cprint("c [manthan] negative unates", NegUnate)
        cprint("c [manthan] all Y variables are unates and have constant functions")
        skolemfunction_preprocess(
            Xvar, Yvar, PosUnate, NegUnate, [], '', temp_stem, output_path)
        finish("finished")
        return

    dg = nx.DiGraph()  # dag to handle dependencies

    if args.unique == 1:
        cprint("c [manthan] finding uniquely defined functions")
        start_t = time.time()
        try:
            UniqueVars, UniqueDef = unique_function(
                qdimacs_list, Xvar, Yvar, dg, Unates)
        except MemoryError:
            cprint("c [manthan] unique extraction skipped due to MemoryError")
            UniqueVars, UniqueDef = [], ""
        cprint("c [manthan] count of uniquely defined variables", len(UniqueVars))
        if args.verbose >= 2:
            cprint("c [manthan] uniquely defined variables", UniqueVars)
    else:
        UniqueVars = []
        UniqueDef = ''
        cprint("c [manthan] finding unique function is disabled. To find unique functions please use --unique")

    if len(Unates) + len(UniqueVars) == len(Yvar):
        cprint("c [manthan] all Y variables are either unate or unique")
        cprint("c [manthan] found functions for all Y variables")
        if args.preprocess == 1:
            skolemfunction_preprocess(
                Xvar, Yvar, PosUnate, NegUnate, UniqueVars, UniqueDef, temp_stem, output_path)
        else:
            skolemfunction_preprocess(
                Xvar, Yvar, [], [], UniqueVars, UniqueDef, temp_stem, output_path)
        finish("finished")
        return

    # we need verilog file for repairing the candidates, hence first let us convert the qdimacs to verilog
    cprint("c [manthan] parsing and converting to verilog")
    verilogformula, dg, ng = convert_verilog(args.input, args.multiclass == 1, dg)
    use_bus_ports = "v_bus0" in verilogformula

    start_t = time.time()

    sampling_cnf = cnfcontent
    if not args.maxsamples:
        remaining_y = len(Yvar) - len(UniqueVars) - len(PosUnate) - len(NegUnate)
        if remaining_y < 0:
            remaining_y = 0
        if remaining_y > 4000:
            num_samples = 1000
        if (remaining_y > 1200) and (remaining_y <= 4000):
            num_samples = 5000
        if remaining_y <= 1200:
            num_samples = 10000
    else:
        num_samples = args.maxsamples

    if args.weighted:
        sampling_weights_y_1 = ''
        sampling_weights_y_0 = ''
        for xvar in Xvar:
            sampling_cnf += "w %s 0.5\n" % (xvar)
        for yvar in Yvar:
            if yvar in UniqueVars:
                sampling_cnf += "w %s 0.5\n" % (yvar)
                continue
            if (yvar in PosUnate) or (yvar in NegUnate):
                continue

            sampling_weights_y_1 += "w %s 0.9\n" % (yvar)
            sampling_weights_y_0 += "w %s 0.1\n" % (yvar)

        if args.adaptivesample:
            weighted_sampling_cnf = computeBias(
                Xvar, Yvar, sampling_cnf, sampling_weights_y_1, sampling_weights_y_0, temp_stem, Unates + UniqueVars, args)
        else:
            weighted_sampling_cnf = sampling_cnf + sampling_weights_y_1

        cprint("c [manthan] generating weighted samples")
        samples = generatesample(
            args, num_samples, weighted_sampling_cnf, temp_stem, 1)
    else:
        cprint("c [manthan] generating uniform samples")
        samples = generatesample(
            args, num_samples, sampling_cnf, temp_stem, 0)

    cprint("c [manthan] generated samples.. learning candidate functions")
    start_t = time.time()

    candidateSkf, dg = learnCandidate(
        Xvar, Yvar, UniqueVars, PosUnate, NegUnate, samples, dg, ng, args)

    missing = [y for y in Yvar if (y not in UniqueVars and y not in PosUnate and y not in NegUnate and y not in candidateSkf)]
    if missing:
        cprint("c [manthan] missing candidate functions for Y variables:", missing)
        raise RuntimeError("Missing candidate functions for some Y variables; see log for details.")

    if args.testflip and args.testflip > 0:
        flip_candidates = [y for y in Yvar if (y in candidateSkf and y not in UniqueVars and y not in PosUnate and y not in NegUnate)]
        rng = random.Random(args.seed)
        rng.shuffle(flip_candidates)
        flip_count = min(args.testflip, len(flip_candidates))
        flipped = flip_candidates[:flip_count]
        for y in flipped:
            expr = candidateSkf.get(y, "").strip()
            if not expr:
                expr = " 1 "
            candidateSkf[y] = " ~ ( %s ) " % expr
        if args.verbose:
            cprint("c [manthan] testflip enabled; flipped %s functions" % flip_count)

    YvarOrder = np.array(list(nx.topological_sort(dg)))

    assert(len(Yvar) == len(YvarOrder))

    createSkolem(candidateSkf, Xvar, Yvar, UniqueVars,
                 UniqueDef, temp_stem)

    error_content = createErrorFormula(Xvar, Yvar, UniqueVars, verilogformula)
    refine_var_log = {y: 0 for y in Yvar}
    selfsub = []
    selfsub_wires = {}
    selfsub_dir = temp_path("selfsub")

    maxsatWt, maxsatcnf, cnfcontent = maxsatContent(
        cnfcontent, (len(Xvar)+len(Yvar)), (len(PosUnate)+len(NegUnate)))

    countRefine = 0

    start_t = time.time()

    while True:
        addSkolem(error_content, temp_stem, debug_keep=args.debug_keep, selfsub=selfsub, selfsub_dir=selfsub_dir)
        check, sigma, ret = verify(Xvar, Yvar, temp_stem, args.verbose or 0, args.debug_keep)
        if check != 0 and getattr(args, "debug_keep", False):
            errorformula = temp_path(temp_stem + "_errorformula.v")
            if args.debug_keep and not os.path.isfile(errorformula):
                errorformula = os.path.abspath(temp_stem + "_errorformula.v")
            if os.path.isfile(errorformula):
                shutil.copyfile(errorformula, last_errorformula_path)
                cprint("c [manthan] last successful error formula:", last_errorformula_path)
        if check == 0:
            cprint("c [manthan] error --- ABC network read fail")
            status = "failed"
            break
        if ret == 0:
            cprint("c [manthan] verification check UNSAT")
            cprint("c [manthan] no more repair needed")
            cprint("c [manthan] number of repairs needed to converge", countRefine)
            createSkolemfunction(temp_stem, Xvar, Yvar, output_path, selfsub=selfsub, selfsub_dir=selfsub_dir)
            break
        if ret == 1:
            countRefine += 1
            cprint("c [manthan] verification check is SAT, we have counterexample to fix")
            if args.verbose:
                cprint("c [manthan] number of repair", countRefine)
                cprint("c [manthan] finding candidates to repair using maxsat")

            repaircnf, maxsatcnfRepair = addXvaluation(
                cnfcontent, maxsatWt, maxsatcnf, sigma[0], Xvar)

            ind = callMaxsat(
                maxsatcnfRepair, sigma[2], UniqueVars, Unates, Yvar, YvarOrder, temp_stem, args.weightedmaxsat, args=args, selfsub=selfsub)

            assert(len(ind) > 0)

            if args.verbose == 1:
                cprint("c [manthan] number of candidates undergoing repair iterations", len(ind))
            if args.verbose == 2:
                cprint("c [manthan] number of candidates undergoing repair iterations", len(ind))
                cprint("c [manthan] variables undergoing refinement", ind)

            lexflag, repairfunctions = repair(
                repaircnf, ind, Xvar, Yvar, YvarOrder, UniqueVars, Unates, sigma, temp_stem, args, args.lexmaxsat == 1)

            if lexflag:
                cprint("c [manthan] calling rc2 to find another set of candidates to repair")
                ind = callRC2(maxsatcnfRepair,
                              sigma[2], UniqueVars, Unates, Yvar, YvarOrder, args, selfsub=selfsub)
                if len(ind) == 0:
                    cprint("c [manthan] no candidates returned by rc2; stopping repair")
                    status = "failed"
                    break
                if args.verbose == 1:
                    cprint("c [manthan] number of candidates undergoing repair iterations", len(ind))
                lexflag, repairfunctions = repair(
                    repaircnf, ind, Xvar, Yvar, YvarOrder, UniqueVars, Unates, sigma, temp_stem, args, 0)
            if not repairfunctions:
                cprint("c [manthan] error --- no repairs produced; aborting")
                status = "failed"
                break
            for yvar in list(repairfunctions.keys()):
                refine_var_log[yvar] = refine_var_log.get(yvar, 0) + 1
                if use_bus_ports:
                    continue
                if refine_var_log[yvar] > args.selfsubthres and yvar not in selfsub:
                    if len(selfsub) == 0:
                        os.makedirs(selfsub_dir, exist_ok=True)
                    selfsub.append(yvar)
                    if len(selfsub) > 2 and args.verbose:
                        cprint("c [manthan] selfsub size > 2:", len(selfsub))
                    selfsub_wires[yvar] = selfsubstitute(
                        Xvar, Yvar, yvar, selfsub, verilogformula, selfsub_dir)

            updateSkolem(repairfunctions, countRefine,
                         sigma[2], temp_stem, Yvar, args, selfsub_wires=selfsub_wires)
        if countRefine > args.maxrepairitr:
            cprint("c [manthan] number of maximum allowed repair iteration reached")
            cprint("c [manthan] could not synthesize functions")
            status = "failed"
            break
    finish(status)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()

    parser.add_argument('--seed', type=int, default=10, dest='seed')
    parser.add_argument('--verb', type=int, default=0, help="0 ,1 ,2", dest='verbose')
    parser.add_argument(
        '--gini', type=float, help="minimum impurity drop, default = 0.005", default=0.005, dest='gini')
    parser.add_argument('--weightedsampling', type=int, default=1,
                        help="weighted sampling: 1; uniform sampling: 0; default 1", dest='weighted')
    parser.add_argument('--maxrepairitr', type=int, default=5000,
                        help="maximum allowed repair iterations; default 1000", dest='maxrepairitr')
    parser.add_argument('--testflip', type=int, default=0,
                        help="test mode: flip N learned Skolem functions to measure recovery", dest='testflip')
    parser.add_argument('--selfsubthres', type=int, default=30,
                        help="self substitution threshold", dest='selfsubthres')
    parser.add_argument('--adaptivesample', type=int, default=1,
                        help="required --weighted to 1: to enable/disable adaptive weighted sampling ", dest='adaptivesample')
    parser.add_argument('--showtrees', type=int, default=0,
                        help="To see the decision trees: 1; default 0", dest='showtrees')
    parser.add_argument('--maxsamples', type=int,
                        help="samples used to learn", dest='maxsamples')
    parser.add_argument(
        "--preprocess",
        nargs="?",
        const=1,
        default=1,
        type=int,
        choices=[0, 1],
        help="enable preprocess: 1; disable: 0; default 1",
    )
    parser.add_argument(
        "--multiclass",
        nargs="?",
        const=1,
        default=1,
        type=int,
        choices=[0, 1],
        help="enable multiclass: 1; disable: 0; default 1",
    )
    parser.add_argument("--weightedmaxsat", action='store_true')
    parser.add_argument(
        "--lexmaxsat",
        nargs="?",
        const=1,
        default=1,
        type=int,
        choices=[0, 1],
        help="enable lexmaxsat: 1; disable: 0; default 1",
    )
    parser.add_argument("--hop", type=int, default=3, dest='hop')
    parser.add_argument("--clustersize", type=int,
                        default=8, dest='clustersize')
    parser.add_argument(
        "--unique",
        nargs="?",
        const=1,
        default=1,
        type=int,
        choices=[0, 1],
        help="enable unique: 1; disable: 0; default 1",
    )
    parser.add_argument("--itp-limit", type=int, default=100000,
                        help="interpolating solver conflict limit; -1 for no limit", dest='itp_limit')
    parser.add_argument("-o", "--output", help="output skolem verilog path")
    parser.add_argument("--sample-mem-frac", type=float, default=0.7,
                        help="fraction of available memory to use for sample parsing (0 disables cap)")
    parser.add_argument("--debug-keep", action="store_true",
                        help="keep generated temp files for debugging")
    parser.add_argument("input", help="input file")
    args = parser.parse_args()
    try:
        import src.InterpolatingSolver as InterpolatingSolver
        InterpolatingSolver.set_global_limit(args.itp_limit)
    except Exception:
        pass
    cprint("c [__main__] starting Manthan")
    manthan()
