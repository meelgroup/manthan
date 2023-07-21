#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 21:35:13 2020

@author: fs
"""

import sys, os, fnmatch


def find(pattern, path):
    result = []
    for root, dirs, files in os.walk(path):
        
        for name in files:
            if fnmatch.fnmatch(name, pattern):
                result.append(os.path.join(root))
    return result

result = find("itp*.so", os.getcwd()+"/unique") # Assuming Unique dir is inside Manthan dir, else update the path to unique dir here.


sys.path.append(result[0])

import itp
import src.Utils as Utils


TRIBOOL_FALSE = 0
TRIBOOL_TRUE = 1
TRIBOOL_INDETERMINATE = 2

class InterpolatingSolver:
  def __init__(self, first_part, second_part):
    self.max_var_index = Utils.maxVarIndex(first_part + second_part)
    self.solver = itp.InterpolatingMiniSAT(self.max_var_index)
    self.solver.addFormula(Utils.miniSAT_clauses(first_part),
                           Utils.miniSAT_clauses(second_part))
    
  def resetFormula(self, first_part, second_part):
    self.max_var_index = Utils.maxVarIndex(first_part + second_part)
    self.solver.resetSolver(self.max_var_index)
    self.solver.addFormula(Utils.miniSAT_clauses(first_part),
                           Utils.miniSAT_clauses(second_part))
    
  def addClause(self, literals, first_part=True):
    max_var = max([abs(l) for l in literals])
    if max_var > self.max_var_index:
      self.max_var_index = max_var
      self.solver.reserve(self.max_var_index)
    part = 1 if first_part else 2
    return self.solver.addClause(Utils.miniSAT_literals(literals), part)
  
  def solve(self, assumptions=[]):
    return self.solver.solve(Utils.miniSAT_literals(assumptions))
  
  def interpolate(self, variable, shared_variables, assumptions=[], budget=0):
    return self.solver.getInterpolant(variable,
                                      Utils.miniSAT_literals(assumptions),
                                      shared_variables, 
                                      budget)

  def getDefinition(self, input_variable_ids, output_variable_id, offset,
                    compress= False):
    return self.solver.getDefinition(input_variable_ids, output_variable_id,
                                     compress, max(self.max_var_index,
                                                   offset))
  
  def getAssignment(self, variables):
    return {v: self.solver.getVarVal(v) for v in variables}