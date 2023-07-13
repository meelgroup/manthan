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

from enum import unique
import numpy as np
import os
import tempfile
from dependencies.rc2 import RC2Stratified
from pysat.formula import WCNF
import networkx as nx


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

def callRC2(maxsatcnf, modelyp, UniqueVars, Unates, Yvar, YvarOrder):
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
    
    wcnf.topw = wt_softclause

    rc2 = RC2Stratified(wcnf)
    model = rc2.compute()
    indlist = []
    for var in model:
        if (var in Yvar) and (var not in UniqueVars) and (var not in Unates):
            index = Yvar.index(var)
            if (int(var) < 0) and (modelyp[index] == 1):
                indlist.append(abs(var))
            if (int(var) > 0) and (modelyp[index] == 0):
                indlist.append(abs(var))
    
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









def callMaxsat(maxsatcnf, modelyp, SkolemKnown, Yvar, YvarOrder, inputfile_name):

    itr = 0
    for var in Yvar:
        

        if var not in SkolemKnown:
        
            weight = 1
            
            if modelyp[itr] == 0:
                maxsatcnf += "%s -%s 0\n" %(weight, var )
            else:
                maxsatcnf += "%s %s 0\n" %(weight,var)
        itr += 1

    maxsatformula =  inputfile_name + "_maxsat.cnf"

    outputfile =  "o.txt"

    with open(maxsatformula, "w") as f:
        f.write(maxsatcnf)
    f.close()

    cmd = "./dependencies/open-wbo %s -print-unsat-soft=%s  > /dev/null 2>&1 " % (maxsatformula, outputfile)
    
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

    cmd = "./dependencies/picosat -s %s -V %s %s > %s " %(args.seed, unsatcorefile, cnffile, satfile)
    os.system(cmd)
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

def findUnsatCore(repair_Yvar_constraint, repaircnf, Xvar, Yvar, Count_Yvar, inputfile_name, args):

    lines = repaircnf.split("\n")

    for line in lines:
        if line.startswith('p cnf'):
            numVar = int(line.split()[2])
            numCls = int(line.split()[3])
            str_tmp = "p cnf " + str(numVar) + " " + str(numCls)
            break

    repaircnf = repaircnf.replace(str_tmp, "p cnf " + str(numVar) + " " + str(numCls + Count_Yvar  + len(Xvar)))
    repaircnf += repair_Yvar_constraint

    cnffile = tempfile.gettempdir() + '/' + inputfile_name+"_unsat.cnf"

    with open(cnffile,"w") as f:
        f.write(repaircnf)
    f.close()

    unsatcorefile = tempfile.gettempdir() + '/' + inputfile_name + "_unsatcore.txt"
    satfile = tempfile.gettempdir() + '/' + inputfile_name + "_sat.txt"
    exists = os.path.isfile(unsatcorefile)

    if exists:
        os.remove(unsatcorefile)
        
    ret, clistx, clisty = findUNSATCorePicosat(cnffile, unsatcorefile, satfile, Xvar,Yvar, args)

    

    if ret:
        return (ret, [], clistx, clisty)
    else:
        os.system("./dependencies/cryptominisat5 --random %s --maxsol %s %s --dumpresult %s > /dev/null 2>&1" % (args.seed, 1, cnffile,satfile))
        with open(satfile,"r") as f:
            lines = f.readlines()
        f.close()
        model = []
        ret = 0
        modelseq = []
        for line in lines:
            if line.startswith("SAT"):
                continue

            assignment = line.split(" ")
            for assign in assignment:
                if int(assign) == 0:
                    break
                else:
                    if (abs(int(assign))) in Yvar:
                        modelseq.append(int(assign))
        for yvar in Yvar:
            if yvar in modelseq:
                model.append(1)
            else:
                model.append(0)
        os.unlink(cnffile)
        os.unlink(satfile)
        return ret, model, [], []   

def repair(flagRC2, repaircnf, ind, Xvar, Yvar, YvarOrder, dg, SkolemKnown, sigma, inputfile_name, args, HenkinDep = {}):

    modelyp = sigma[2]
    modelx = sigma[0]

    itr = 0

    repaired = []
    repairfunctions = {}
    ind_org = ind.copy()

    satvar = []  # if G_k formal is SAT, need to find another set of variables.

    while itr < len(ind):

        repairvar = ind[itr]
        itr += 1
        
        if (repairvar in SkolemKnown) or (repairvar in satvar):
            continue


        repair_Yvar_constraint = ''
        count_Yvar = 0  # it counts the number of times (Y <-> \sigma[Y']) is added part wrong unique variables
        allowed_Y = []  # list of all y_j variables on which y_i (repairvar) could be depended.

        if not args.henkin: 

            '''
            YvarOrder: Y_{i+1} to |Y| on which y_i could be depended.
            '''
            
            repairvar_index = np.where(YvarOrder == repairvar)[0][0]
            
            for yj_index in range(repairvar_index,len(Yvar)):
                yj_var = YvarOrder[yj_index]
                allowed_Y.append(yj_var)
        
        if args.henkin:

            allowed_Y = list(nx.descendants(dg,repairvar))
        
        
        for yj_var in allowed_Y:

            yj_index = np.where(np.array(Yvar) == yj_var)[0][0]
            
            if yj_var in SkolemKnown:
                continue

            if yj_var in repaired:
                if modelyp[yj_index] == 0:
                    repair_Yvar_constraint += "%s 0\n" %(yj_var)
                else:
                    repair_Yvar_constraint += "-%s 0\n" %(yj_var)
            else:
                if modelyp[yj_index] == 0:
                    repair_Yvar_constraint += "-%s 0\n" %(yj_var)
                else:
                    repair_Yvar_constraint += "%s 0\n" %(yj_var)
            count_Yvar += 1  
        
        if args.verbose > 1:
            print("repairing %s" %(repairvar))
        
        if not args.henkin:
            ret, model, clistx, clisty = findUnsatCore(repair_Yvar_constraint, repaircnf, 
                                                            Xvar, Yvar, count_Yvar, inputfile_name, args)
        else:
            ret, model, clistx, clisty = findUnsatCore(repair_Yvar_constraint, repaircnf, HenkinDep[repairvar], 
                                                            Yvar, count_Yvar, inputfile_name, args)

        if ret == 0:
            '''
            G_k is SAT, find another set of candidates to repair
            '''
            
            satvar.append(repairvar)

            if (repairvar not in ind_org) and (len(repaired) > 0):
                continue
            
            if len(ind) > (len(ind_org) * 50) and flagRC2:
                print("too many new repair candidate added.. calling rc2")
                return 1, repairfunctions
            
            
            
            model = np.array(model)
            diff = np.bitwise_xor(modelyp, model)
            index = np.where(diff == 1)[0]
            
            
            for yk in index:

                l = itr

                if (Yvar[yk] not in ind) and (Yvar[yk] not in SkolemKnown):

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
                        ind = np.append(ind, Yvar[yk]).astype(np.int_)   
        else:

            '''
             G_k is UNSAT, construct Beta formula from unsat core.
            '''

            repaired.append(repairvar)

            if args.verbose > 1:
                print("gk formula is UNSAT\ncreating beta formula")
            
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

                if y == repairvar:
                    continue
        
                if modelyp[y_index] == 0:
                    betaformula += "~o%s & " %(y)
                else:
                    betaformula += "o%s & " %(y)
            
            repairfunctions[repairvar] = betaformula.strip("& ")
            assert(repairfunctions[repairvar] != "")
        
    if args.verbose == 2:
        print("repaired functions", repairfunctions)
    return 0, repairfunctions

def updateSkolem(repairfunctions, countRefine, modelyp, inputfile_name, Yvar):
    
    with open(tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v","r") as f:
        lines = f.readlines()
    f.close()
    
    skolemcontent = "".join(lines)
    
    for yvar in list(repairfunctions.keys()):
        oldfunction = [line for line in lines if "assign w" + str(yvar)+" " in line][0]
        oldfunctionR = oldfunction.rstrip(";\n").lstrip("assign w%s = " %(yvar))
        repairformula = "wire beta%s_%s;\nassign beta%s_%s = ( %s );\n" %(yvar,countRefine,yvar,countRefine,repairfunctions[yvar])
        
        yindex = np.where(np.array(Yvar) == yvar)[0][0]

        '''
        if repair is to move from 0 to 1
            F(X) = F(X) \lor repair
        
        if repair is to move from 1 to 0
            F(X) = F(X) \land \lnot repair
        
        '''

        if modelyp[yindex] == 0:
            newfunction = "assign w%s = (( %s ) | ( beta%s_%s) );\n" %(yvar, oldfunctionR, yvar, countRefine)
        else:
            newfunction = "assign w%s = (( %s ) & ~(beta%s_%s) );\n" %(yvar, oldfunctionR, yvar, countRefine)
        skolemcontent = skolemcontent.replace(oldfunction, repairformula + newfunction)
    
    with open(tempfile.gettempdir() + '/' + inputfile_name + "_skolem.v","w") as f:
        f.write(skolemcontent)
    f.close()