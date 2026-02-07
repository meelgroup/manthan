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
import os
import tempfile
import subprocess
from src import runtime_env  # noqa: F401
from src.logging_utils import cprint
from src.tempfiles import temp_path
from dependencies.rc2 import RC2Stratified
from pysat.formula import WCNF


def maxsatContent(cnfcontent,n, u):
    lines = cnfcontent.split("\n")
    maxsatCnf = ''
    for line in lines:
        line = line.strip("\n")
        if line == '':
            continue
        if line.startswith("c"):
            maxsatCnf += line + "\n"
            continue
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            maxsatWt = numVar + 100
            line = line.replace("p cnf " + str(numVar) + " " + str(
                numCls), "p wcnf " + str(numVar) + " " + str(numCls + n+u) + " " + str(maxsatWt))
            cnfcontent = cnfcontent.replace("p cnf " + str(numVar) + " " + str(
                numCls), "p cnf " + str(numVar) + " " + str(numCls + u))
            maxsatCnf += line + "\n"
            continue
        maxsatCnf += str(maxsatWt) + " " + line + "\n"
    return maxsatWt, maxsatCnf, cnfcontent


def static_bin_path(bin_name):
    preferred = os.path.join("./dependencies/static_bin", bin_name)
    if os.path.isfile(preferred) and os.access(preferred, os.X_OK):
        return os.path.abspath(preferred)
    return os.path.abspath(os.path.join("./dependencies", bin_name))




def addXvaluation(cnfcontent, maxsatWt, maxsatcnf, modelx, Xvar):
    maxsatstr = ''
    cnfstr = ''
    itr = 0
    for var in Xvar:
        if (modelx[itr] == 0):
            maxsatstr += str(maxsatWt) + " -" + str(var) + " 0\n"
            cnfstr += "-" + str(var) + " 0\n"
        else:
            maxsatstr += str(maxsatWt) + " " + str(var) + " 0\n"
            cnfstr += str(var) + " 0\n"
        itr += 1
    cnfcontent = cnfcontent.strip("\n") + "\n" + cnfstr
    maxsatcnf += "\n" + maxsatstr
    return cnfcontent, maxsatcnf

def callRC2(maxsatcnf, modelyp, UniqueVars, Unates, Yvar, YvarOrder, args):
    wcnf = WCNF(from_string = maxsatcnf)
    wt_softclause = 0
    for i in range(len(Yvar)):
        yvar = Yvar[i]

        if (yvar in UniqueVars) or (yvar in Unates):
            continue
        yindex = np.where(yvar == YvarOrder)[0][0]
        weight = len(Yvar) - yindex

        if modelyp[i] == 0:
            wcnf.append([-1*yvar], weight = weight)
        else:
            wcnf.append([yvar], weight = weight)
        
        wt_softclause += 1
    
    rc2 = RC2Stratified(wcnf)
    model = rc2.compute()
    if args.verbose >= 2 and len(model) == 0:
        cprint("c [callRC2] rc2: empty model")
    indlist = []
    diff_count = 0
    for var in model:
        abs_var = abs(var)
        if (abs_var in Yvar) and (abs_var not in UniqueVars) and (abs_var not in Unates):
            index = Yvar.index(abs_var)
            if (var < 0) and (modelyp[index] == 1):
                indlist.append(abs_var)
                diff_count += 1
            if (var > 0) and (modelyp[index] == 0):
                indlist.append(abs_var)
                diff_count += 1
    if args.verbose >= 2:
        cprint("c [callRC2] rc2: soft clauses", wt_softclause, "diffs", diff_count, "ind", len(indlist))
    
    indlist = np.array(indlist)
    indlist = np.unique(indlist)

    # to add variables in indlist according to Y order.
    YvarOrder_ind = []
    for i in indlist:
        yindex = np.where(i == YvarOrder)[0][0]
        YvarOrder_ind.append(yindex)
    indlist = []
    YvarOrder_ind.sort(reverse=True)
    for i in YvarOrder_ind:
        indlist.append(YvarOrder[i])
    indlist = np.array(indlist)
    return indlist









def callMaxsat(maxsatcnf, modelyp, UniqueVars, Unates, Yvar, YvarOrder, inputfile_name, flag):
    def pick_executable(preferred_path, fallback_path):
        if os.path.isfile(preferred_path) and os.access(preferred_path, os.X_OK):
            return preferred_path
        return fallback_path

    itr = 0
    for var in Yvar:
        if (var not in Unates) and (var not in UniqueVars):
            if flag:
                yindex = np.where(var == YvarOrder)[0][0]
                weight = len(Yvar) - yindex
            else:
                weight = 1
            
            if modelyp[itr] == 0:
                maxsatcnf += "%s -%s 0\n" %(weight, var )
            else:
                maxsatcnf += "%s %s 0\n" %(weight,var)
        itr += 1

    openwbo = pick_executable(static_bin_path("open-wbo"),
                              "./dependencies/open-wbo/open-wbo_release")
    openwbo = os.path.abspath(openwbo)

    with tempfile.TemporaryDirectory(prefix="manthan_openwbo_") as tmpdir:
        maxsatformula = os.path.join(tmpdir, "maxsat.wcnf")
        outputfile = os.path.join(tmpdir, "o.txt")

        with open(maxsatformula, "w") as f:
            f.write(maxsatcnf)
        f.close()

        cmd = [openwbo, "maxsat.wcnf", "-print-unsat-soft=o.txt"]
        subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if not os.path.isfile(outputfile):
            raise FileNotFoundError("open-wbo did not produce %s (cmd: %s)" % (outputfile, " ".join(cmd)))

        with open(outputfile, 'r') as f:
            lines = f.readlines()
        f.close()

    indlist = []
    for line in lines:
        if line.split(' ')[0].startswith("p"):
            continue
        else:
            ymap = abs(int(line.split(" ")[1]))
            indlist.append(ymap)
    indlist = np.array(indlist)
    indlist = np.unique(indlist)

    # to add variables in indlist according to Y order.
    YvarOrder_ind = []
    for i in indlist:
        yindex = np.where(i == YvarOrder)[0][0]
        YvarOrder_ind.append(yindex)
    indlist = []
    YvarOrder_ind.sort(reverse=True)
    for i in YvarOrder_ind:
        indlist.append(YvarOrder[i])
    indlist = np.array(indlist)
    return indlist


def findUNSATCorePicosat(cnffile,unsatcorefile, satfile, Xvar,Yvar, args):
    picosat = static_bin_path("picosat")
    cmd = [picosat, "-s", str(args.seed), "-V", unsatcorefile, cnffile]
    with open(satfile, "w") as out:
        subprocess.run(cmd, stdout=out, stderr=subprocess.DEVNULL)
    exists = os.path.isfile(unsatcorefile)
    if exists:
        with open(unsatcorefile,"r") as f:
            lines = f.readlines()
        f.close()
        clistx = []
        clisty = []
        for line in lines:
            v = int(line.strip(" \n"))
            if v in Xvar:
                clistx.append(v)
            if v in Yvar:
                clisty.append(v)
        os.unlink(unsatcorefile)
        os.unlink(cnffile)
        return 1, clistx, clisty
    else:
        os.unlink(satfile)
        return 0, [], []

def findUnsatCore(repairYvar, repaircnf, Xvar, Yvar, Count_Yvar, inputfile_name, args):
    lines = repaircnf.split("\n")
    for line in lines:
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            str_tmp = "p cnf " + str(numVar) + " " + str(numCls)
            break
    repaircnf = repaircnf.replace(str_tmp, "p cnf " + str(numVar) + " " + str(numCls + Count_Yvar  + len(Xvar)))
    repaircnf += repairYvar
    cnffile = temp_path(inputfile_name + "_unsat.cnf")

    with open(cnffile,"w") as f:
        f.write(repaircnf)
    f.close()

    unsatcorefile = temp_path(inputfile_name + "_unsatcore.txt")
    satfile = temp_path(inputfile_name + "_sat.txt")
    exists = os.path.isfile(unsatcorefile)
    if exists:
        os.remove(unsatcorefile)
    ret, clistx, clisty = findUNSATCorePicosat(cnffile, unsatcorefile, satfile, Xvar,Yvar, args)
    if getattr(args, "verbose", 0) >= 1:
        cprint("c [findUnsatCore] Picosat UNSAT core result: %s" %(ret))
    if ret:
        return (ret, [], clistx, clisty)
    else:
        cmsgen = static_bin_path("cmsgen")
        tmpdir = os.path.dirname(cnffile)
        cmd = [cmsgen, "--samples", "1", "-s", str(args.seed),
               "--samplefile", os.path.basename(satfile), os.path.basename(cnffile)]
        subprocess.run(cmd, cwd=tmpdir, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if not os.path.isfile(satfile):
            raise FileNotFoundError("cmsgen did not produce %s (cmd: %s)" % (satfile, cmd))
        with open(satfile,"r") as f:
            lines = f.readlines()
        f.close()
        model = []
        ret = 0
        modelseq = []
        for line in lines:
            if line.startswith("SAT") or line.startswith("c") or line.startswith("s") or line.startswith("p"):
                continue
            assignment = line.split()
            for assign in assignment:
                try:
                    lit = int(assign)
                except ValueError:
                    continue
                if lit == 0:
                    break
                if abs(lit) in Yvar:
                    modelseq.append(lit)
        for yvar in Yvar:
            if yvar in modelseq:
                model.append(1)
            else:
                model.append(0)
        os.unlink(cnffile)
        os.unlink(satfile)
        return ret, model, [], []   


def repair(repaircnf, ind, Xvar, Yvar, YvarOrder, UniqueVars, Unates, sigma, inputfile_name, args, flagRC2):
    modelyp = sigma[2]
    modelx = sigma[0]

    itr = 0
    repaired = []
    repairfunctions = {}
    ind_org = ind.copy()
    satvar = []
    while itr < len(ind):
        repairvar = ind[itr]
        itr += 1
        
        if (repairvar in UniqueVars) or (repairvar in Unates) or (repairvar in satvar):
            continue


        repairYvar = ''
        count_Yvar = 0
        allowed_Y = []

        repairvar_index = np.where(YvarOrder == repairvar)[0][0]

        for jindex in range(repairvar_index,len(Yvar)):  
            yjvar = YvarOrder[jindex]
            allowed_Y.append(yjvar)
            yj_index = np.where(np.array(Yvar) == yjvar)[0][0]
            
            if (yjvar in UniqueVars) or (yjvar in Unates):
                continue

            if yjvar in repaired:
                if modelyp[yj_index] == 0:
                    repairYvar += "%s 0\n" %(yjvar)
                else:
                    repairYvar += "-%s 0\n" %(yjvar)
            else:
                if modelyp[yj_index] == 0:
                    repairYvar += "-%s 0\n" %(yjvar)
                else:
                    repairYvar += "%s 0\n" %(yjvar)
            count_Yvar += 1
        
        if args.verbose:
            cprint("c [repair] repairing %s" %(repairvar))
        
        ret, model, clistx, clisty = findUnsatCore(repairYvar, repaircnf, Xvar, Yvar, count_Yvar, inputfile_name, args)

        if ret == 0:
            if args.verbose:
                cprint("c [repair] gk formula is SAT")
            satvar.append(repairvar)
            if (repairvar not in ind_org) and (len(repaired) > 0):
                continue
            if len(ind) > (len(ind_org) * 50) and flagRC2:
                cprint("c [repair] too many new repair candidate added.. calling rc2")
                return 1, repairfunctions
            if args.verbose:
                cprint("c [repair] looking for other candidates to repair")
            model = np.array(model)
            diff = np.bitwise_xor(modelyp, model)
            index = np.where(diff == 1)[0]
            
            for yk in index:
                l = itr
                if (Yvar[yk] not in ind) and (Yvar[yk] not in Unates) and (Yvar[yk] not in UniqueVars):
                    flag = 0
                    yk_index = np.where(YvarOrder == Yvar[yk])[0][0]
                    while (l < len(ind)):
                        tempyvar = ind[l]
                        indextemp = np.where(YvarOrder == tempyvar)[0][0]
                        if indextemp < yk_index:
                            flag = 1
                            ind = np.insert(ind, l, Yvar[yk])
                            break
                        l = l + 1
                    if flag == 0:
                        ind = np.append(ind, Yvar[yk]).astype(int)
        else:
            repaired.append(repairvar)
            if args.verbose:
                cprint("c [repair] gk formula is UNSAT; creating beta formula")
            
            betaformula = ''
            for x in clistx:
                x_index = np.where(np.array(Xvar) == x)[0][0]

                if modelx[x_index] == 0:
                    betaformula += "~i%s & " %(x)
                else:
                    betaformula += "i%s & " %(x)
                
            for y in clisty:
                y_index = np.where(np.array(Yvar) == y)[0][0]

                if y in ind:
                    index = np.where(np.array(ind) == y)[0][0]
                    if itr - 1 < index:
                        satvar.append(y)

                if y not in allowed_Y:
                    continue

                if modelyp[y_index] == 0:
                    betaformula += "~o%s & " %(y)
                else:
                    betaformula += "o%s & " %(y)
            
            if args.verbose >= 2:
                cprint("c [repair] Repair function for w%s: %s" %(repairvar, betaformula.strip("& ")))
            repairfunctions[repairvar] = betaformula.strip("& ")
            assert(repairfunctions[repairvar] != "")
    return 0, repairfunctions

def updateSkolem(repairfunctions, countRefine, modelyp, inputfile_name, Yvar, args):
    with open(temp_path(inputfile_name + "_skolem.v"),"r") as f:
        lines = f.readlines()
    f.close()
    skolemcontent = "".join(lines)
    for yvar in list(repairfunctions.keys()):
        start_idx = None
        for i, line in enumerate(lines):
            if line.strip().startswith("assign w" + str(yvar) + " "):
                start_idx = i
                break
        if start_idx is None:
            continue
        old_lines = [lines[start_idx]]
        i = start_idx
        while ";" not in lines[i]:
            i += 1
            if i >= len(lines):
                break
            old_lines.append(lines[i])
        oldfunction = "".join(old_lines)
        oldfunctionR = oldfunction.replace("\n", " ").strip()
        prefix = "assign w%s = " % (yvar)
        if oldfunctionR.startswith(prefix):
            oldfunctionR = oldfunctionR[len(prefix):]
        oldfunctionR = oldfunctionR.rstrip(";").strip()
        repairformula = "wire beta%s_%s;\nassign beta%s_%s = ( %s );\n" %(yvar,countRefine,yvar,countRefine,repairfunctions[yvar])
        
        yindex = np.where(np.array(Yvar) == yvar)[0][0]

        if modelyp[yindex] == 0:
            newfunction = "assign w%s = (( %s ) | ( beta%s_%s) );\n" %(yvar, oldfunctionR, yvar, countRefine)
        else:
            newfunction = "assign w%s = (( %s ) & ~(beta%s_%s) );\n" %(yvar, oldfunctionR, yvar, countRefine)
        if args.verbose >= 2:
            cprint("c [updateSkolem] Old function for w%s: %s" %(yvar, oldfunction.strip("\n")))
            cprint("c [updateSkolem] New function for w%s: %s" %(yvar, newfunction.strip("\n")))
            cprint("c [updateSkolem] Repair function for w%s: %s" %(yvar, repairformula.strip("\n")))
        skolemcontent = skolemcontent.replace(oldfunction, repairformula + newfunction)
    with open(temp_path(inputfile_name + "_skolem.v"),"w") as f:
        f.write(skolemcontent)
    f.close()
