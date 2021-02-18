#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Wed Jun  3 21:39:16 2020

@author: fs
"""

def miniSAT_literals(literals):
  return [2*abs(lit) + (lit < 0) for lit in literals]

def miniSAT_clauses(clauses):
  return [miniSAT_literals(c) for c in clauses]

def maxVarIndex(clause_list):
  return max([abs(l) for c in clause_list for l in c], default=0)

def clausalEncodingAND(definition):
  defining_literals, defined_literal = definition
  negative_clauses = [[l, -defined_literal] for l in defining_literals]
  positive_clause = [-l for l in defining_literals] + [defined_literal]
  return negative_clauses + [positive_clause]

def renameLiteral(l, renaming):
  return renaming.get(l, l) if l > 0 else -renaming.get(abs(l), abs(l))

def renameClause(clause, renaming):
  return [renameLiteral(l, renaming) for l in clause]

def renameFormula(clauses, renaming):
  return [renameClause(clause, renaming) for clause in clauses]

def createRenaming(clauses, shared_variables, auxiliary_start=None):
  variables = {abs(l) for clause in clauses for l in clause}
  non_shared = variables.difference(shared_variables)
  if auxiliary_start is None:
    auxiliary_start = max(variables, default=0) + 1
  renaming_range = range(auxiliary_start, auxiliary_start+len(non_shared))
  renaming = dict(zip(non_shared, renaming_range))
  renamed_clauses = renameFormula(clauses, renaming)
  return renamed_clauses, renaming, auxiliary_start+len(non_shared)-1

def negate(clauses, auxiliary_start=None):
  if auxiliary_start is None:
    auxiliary_start = maxVarIndex(clauses) + 1
  auxiliary_range = range(auxiliary_start, auxiliary_start + len(clauses) + 1)
  small_clauses = [[-l, auxiliary_range[i]] for i in range(len(clauses))
                   for l in clauses[i]]
  big_clause = [-v for v in auxiliary_range]
  return small_clauses + [big_clause]

def equality(lit1, lit2, switch):
  return [[-switch, lit1, -lit2], 
          [-switch, -lit1, lit2]]