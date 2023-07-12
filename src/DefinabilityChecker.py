#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Aug 26 22:55:21 2020

@author: fs
"""

from pysat.solvers import Cadical103 as Cadical
import logging
import src.InterpolatingSolver as InterpolatingSolver
import src.Utils as Utils

class DefinabilityChecker:
  
  def __init__(self, formula, existentials):
    self.max_variable = Utils.maxVarIndex(formula)
    variables = {abs(l) for clause in formula for l in clause}
    self.renaming = {v: v + self.max_variable for v in variables}
    # Create copy of 'formula' for second part.
    formula_copy = Utils.renameFormula(formula, self.renaming)
    
    # Create on/off constraints/selectors for existential variables.
    self.on_selector_dict = {v: v + (2 * self.max_variable)
                             for v in existentials}
    on = [[v, -self.on_selector_dict[v]] for v in existentials]
    self.off_selector_dict = {v: v + (3 * self.max_variable)
                              for v in existentials}
    off = []
    for v in existentials:
      if v in self.renaming.keys():
        off.append([-self.renaming[v], -self.off_selector_dict[v]])
    '''off = [[-self.renaming[v], -self.off_selector_dict[v]]
           for v in existentials]'''
    # Create equality constraints/selectors for all variables.
    self.eq_selector_dict = {v: v + (4 * self.max_variable) for v in variables}
    eq = [c for v in variables
            for c in Utils.equality(v, 
                                    self.renaming[v], 
                                    self.eq_selector_dict[v])]
    self.max_variable = 5 * self.max_variable
    
    self.solver = InterpolatingSolver.InterpolatingSolver(formula+on,
                                                          formula_copy+off+eq)
    self.backbone_solver = Cadical(bootstrap_with=formula)  
    
  def addClause(self, clause):
    self.solver.addClause(clause, True)
    logging.debug("Adding clause to part 1: {}".format(clause))
    renamed_clause = Utils.renameClause(clause,
                                        self.renaming)
    self.solver.addClause(renamed_clause, False)
    logging.debug("Adding clause to part 2: {}".format(renamed_clause))
    self.backbone_solver.add_clause(clause) #TODO: Check if needed.

  def checkDefinability(self, 
                        defining_variables, 
                        defined_variable,
                        offset=None,
                        assumptions=[]):
    
    if offset is None:
      offset = self.max_variable + 1
    
    # First check whether the assignment of 'defined_variable' is forced.
    # If that is the case, the interpolating solver throws a fit.
    logging.debug("Checking definability of {} in terms of {}.".format(
      defined_variable, defining_variables))
    is_forced, forced_definition = self.checkForced(defined_variable)
    if is_forced:
      return True, forced_definition
    
    # Add assumptions that ensure 'defining_variables' are shared.
    eq_enabled = []
    for v in defining_variables:
      if v in self.eq_selector_dict.keys():
        eq_enabled.append(self.eq_selector_dict[v])
    
    #eq_enabled = [self.eq_selector_dict[v] for v in defining_variables]
    defining_variables_set = set(defining_variables)
    eq_disabled = [-self.eq_selector_dict[v] for v in self.eq_selector_dict
                   if v not in defining_variables_set]

    # Add assumptions ensuring that 'defined_variable' and its copy have
    # distinct values.
    on = self.on_selector_dict[defined_variable]
    off = self.off_selector_dict[defined_variable]
    
    assumptions_complete = eq_disabled + eq_enabled + assumptions + [on, off]
    logging.debug("Assumptions: {}".format(assumptions_complete))
    # Check whether 'defined_variable' is defined.
    satisfiable = self.solver.solve(assumptions_complete)
    assert satisfiable != InterpolatingSolver.TRIBOOL_INDETERMINATE, \
          "SAT call indeterminate."
    
    if satisfiable == InterpolatingSolver.TRIBOOL_FALSE:
      return True, self.solver.getDefinition(defining_variables, 
                                             defined_variable, offset)
    else:
      return False, self.getAssignment(defining_variables)
    
  def checkForced(self, variable):
    if not self.backbone_solver.solve([variable]):
      logging.debug("Variable {} forced to False.".format(variable))
      return True, [[-variable]]
    elif not self.backbone_solver.solve([-variable]):
      logging.debug("Variable {} forced to True.".format(variable))
      return True, [[variable]]
    else:
      return False, None
    
  def getAssignment(self, defining_variables):
      assignment = self.solver.getAssignment(defining_variables)
      positive = [v for v in assignment.keys()
                 if assignment[v] == InterpolatingSolver.TRIBOOL_TRUE]
      negative = [-v for v in assignment.keys()
                  if assignment[v] == InterpolatingSolver.TRIBOOL_FALSE]
      literals = positive + negative
      assert len(assignment) == len(literals), assignment
      return literals
