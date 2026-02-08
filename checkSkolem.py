#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Independent checker for Skolem functions against the original QDIMACS formula.
Builds an error formula and uses ABC's file_generation_cex to find a counterexample.
"""

import argparse
import os
import re
import subprocess
import sys
import tempfile
import shutil

REPO_ROOT = os.path.abspath(os.path.dirname(__file__))
if REPO_ROOT not in sys.path:
    sys.path.insert(0, REPO_ROOT)

from src import runtime_env  # noqa: F401
import numpy as np

from src.logging_utils import cprint
from src.preprocess import parse
from src.convert_verilog import _wrap_assign


def _static_bin_path(bin_name):
    preferred = os.path.join("./dependencies/static_bin", bin_name)
    if os.path.isfile(preferred) and os.access(preferred, os.X_OK):
        return os.path.abspath(preferred)
    return os.path.abspath(os.path.join("./dependencies", bin_name))


def _skolem_module_info(skolem_path):
    module_name = None
    has_out = False
    with open(skolem_path, "r") as f:
        for line in f:
            if module_name is None:
                match = re.match(r"\s*module\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
                if match:
                    module_name = match.group(1)
            if re.search(r"\boutput\s+out\b", line):
                has_out = True
    if module_name is None:
        raise RuntimeError("Could not find module declaration in %s" % skolem_path)
    return module_name, has_out


def _convert_verilog(qdimacs_path):

    with open(qdimacs_path, "r") as f:
        lines = f.readlines()

    itr = 1
    declare = "module FORMULA( "
    declare_input = ""
    declare_wire = ""
    assign_lines = []
    tmp_array = []

    for line in lines:
        line = line.strip(" ")
        if (line == "") or (line == "\n"):
            continue
        if line.startswith("c "):
            continue
        if line.startswith("p "):
            continue

        if line.startswith("a"):
            a_variables = line.strip("a").strip("\n").strip(" ").split(" ")[:-1]
            for avar in a_variables:
                declare += "%s," % (avar)
                declare_input += "input %s;\n" % (avar)
            continue

        if line.startswith("e"):
            e_variables = line.strip("e").strip("\n").strip(" ").split(" ")[:-1]
            for evar in e_variables:
                tmp_array.append(int(evar))
                declare += "%s," % (evar)
                declare_input += "input %s;\n" % (evar)
            continue

        declare_wire += "wire t_%s;\n" % (itr)

        clause_variable = line.strip(" \n").split(" ")[:-1]
        assign_expr = ""
        for var in clause_variable:
            if int(var) < 0:
                assign_expr += "~%s | " % (abs(int(var)))
            else:
                assign_expr += "%s | " % (abs(int(var)))

        assign_expr = assign_expr.strip("| ")
        assign_expr = _wrap_assign(assign_expr, indent="  ", max_terms=200)
        assign_lines.append("assign t_%s = %s;\n" % (itr, assign_expr))
        itr += 1


    count_tempvariable = itr

    declare += "out);\n"
    declare_input += "output out;\n"

    temp_assign = ""
    outstr = ""

    itr = 1
    while itr < count_tempvariable:
        temp_assign += "t_%s & " % (itr)
        if itr % 100 == 0:
            declare_wire += "wire tcount_%s;\n" % (itr)
            tcount_expr = temp_assign.strip("& ")
            tcount_expr = _wrap_assign(tcount_expr, indent="  ", max_terms=200)
            assign_lines.append("assign tcount_%s = %s;\n" % (itr, tcount_expr))
            outstr += "tcount_%s & " % (itr)
            temp_assign = ""
        itr += 1

    if temp_assign != "":
        declare_wire += "wire tcount_%s;\n" % (itr)
        tcount_expr = temp_assign.strip("& ")
        tcount_expr = _wrap_assign(tcount_expr, indent="  ", max_terms=200)
        assign_lines.append("assign tcount_%s = %s;\n" % (itr, tcount_expr))
        outstr += "tcount_%s & " % (itr)
    out_expr = outstr.strip("& \n")
    out_expr = _wrap_assign(out_expr, indent="  ", max_terms=200)
    outstr = "assign out = %s;\n" % (out_expr)

    verilogformula = declare + declare_input + declare_wire + "".join(assign_lines) + outstr + "endmodule\n"

    return verilogformula


def _build_error_formula(Xvar, Yvar, verilog_formula, skolem_module):
    inputformula = '('
    inputskolem = '('
    inputerrorx = 'module MAIN ('
    inputerrory = ''
    inputerroryp = ''
    declarex = ''
    declarey = ''
    declareyp = ''

    for var in Xvar:
        inputformula += "%s, " % (var)
        inputskolem += "%s, " % (var)
        inputerrorx += "%s, " % (var)
        declarex += "input %s ;\n" % (var)

    for var in Yvar:
        inputformula += "%s, " % (var)
        inputerrory += "%s, " % (var)
        declarey += "input %s ;\n" % (var)
        inputerroryp += "ip%s, " % (var)
        declareyp += "input ip%s ;\n" % (var)
        inputskolem += "ip%s, " % (var)

    inputformula += "out1 );\n"
    inputformula_sk = inputskolem + "out3 );\n"
    inputskolem += "out2 );\n"
    inputerrorx = inputerrorx + inputerrory + inputerroryp + "out );\n"
    declare = declarex + declarey + declareyp + 'output out;\n' + \
        "wire out1;\n" + "wire out2;\n" + "wire out3;\n"
    formula_call = "FORMULA F1 " + inputformula
    skolem_call = "%s F2 " % skolem_module + inputskolem
    formulask_call = "FORMULA F2 " + inputformula_sk
    error_content = inputerrorx + declare + \
        formula_call + skolem_call + formulask_call
    error_content += "assign out = ( out1 & out2 & ~(out3) );\nendmodule\n"
    error_content += verilog_formula
    return error_content


def _build_wrapper(Xvar, Yvar, skolem_module, wrapper_name):
    decl = "module %s (" % wrapper_name
    decl_inputs = ""
    for var in Xvar:
        decl += "%s, " % var
        decl_inputs += "input %s;\n" % var
    for var in Yvar:
        decl += "ip%s, " % var
        decl_inputs += "input ip%s;\n" % var
    decl += "out);\n"
    decl_inputs += "output out;\n"

    wires = ""
    inst_args = ""
    for var in Xvar:
        inst_args += "%s, " % var
    for var in Yvar:
        wires += "wire o%s;\n" % var
        inst_args += "o%s, " % var
    inst_args = inst_args.strip(", ")
    inst = "%s U (%s);\n" % (skolem_module, inst_args)

    out_expr = ""
    for var in Yvar:
        out_expr += "(~(o%s ^ ip%s)) & " % (var, var)
    out_expr = out_expr.strip("& ")
    assign = "assign out = %s;\n" % out_expr
    return decl + decl_inputs + wires + inst + assign + "endmodule\n"


def _parse_cex(model, x_count, y_count):
    if (" " not in model) and ("\n" not in model) and all(ch in "01" for ch in model):
        cex = [int(ch) for ch in model]
    else:
        cex = []
        for tok in model.split():
            try:
                val = int(tok)
            except ValueError:
                continue
            if val == 0:
                continue
            cex.append(val)

    expected = x_count + 2 * y_count
    if len(cex) < expected:
        return None
    return cex[:expected]


def check_skolem(qdimacs_path, skolem_path, debug_keep=False):
    Xvar, Yvar, _ = parse(qdimacs_path)
    verilog_formula = _convert_verilog(qdimacs_path)

    skolem_module, has_out = _skolem_module_info(skolem_path)
    if has_out:
        wrapper_name = skolem_module
        wrapper_content = ""
    else:
        wrapper_name = "SKOLEM_CHECK_WRAPPER"
        wrapper_content = _build_wrapper(Xvar, Yvar, skolem_module, wrapper_name)

    error_content = _build_error_formula(Xvar, Yvar, verilog_formula, wrapper_name)

    with open(skolem_path, "r") as f:
        skolem_content = f.read()

    abc_cex = _static_bin_path("file_generation_cex")
    with tempfile.TemporaryDirectory(prefix="manthan_skolem_check_") as tmpdir:
        errorformula = os.path.join(tmpdir, "errorformula.v")
        cexfile = os.path.join(tmpdir, "cex.txt")

        with open(errorformula, "w") as f:
            f.write(error_content)
            f.write(skolem_content)
            if wrapper_content:
                f.write("\n" + wrapper_content)
        if debug_keep:
            debug_name = os.path.splitext(os.path.basename(skolem_path))[0] + "_errorformula.v"
            shutil.copyfile(errorformula, os.path.abspath(debug_name))

        cmd = [abc_cex, errorformula, cexfile]
        result = subprocess.run(cmd, cwd=tmpdir, capture_output=True, text=True)
        if result.returncode != 0:
            err = "ABC failed: %s\nstdout: %s\nstderr: %s" % (
                " ".join(cmd), result.stdout.strip(), result.stderr.strip())
            return "error", None, err

        if not os.path.isfile(cexfile):
            return "unsat", None, None

        with open(cexfile, "r") as f:
            model = f.read().strip(" \n")
        if not model:
            return "unsat", None, None

        cex = _parse_cex(model, len(Xvar), len(Yvar))
        if cex is None:
            return "unsat", None, None
        return "sat", cex, None


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--qdimacs", required=True, help="Input QDIMACS file")
    parser.add_argument("--skolem", required=True, help="Skolem Verilog file")
    parser.add_argument("--debug-keep", action="store_true",
                        help="keep generated errorformula.v in the working directory")
    args = parser.parse_args()

    status, cex, err = check_skolem(args.qdimacs, args.skolem, args.debug_keep)
    if status == "sat":
        cprint("c [main] skolem check SAT (counterexample exists)")
        cprint("c [main] cex length:", len(cex))
    elif status == "unsat":
        cprint("c [main] skolem check UNSAT (no counterexample)")
    else:
        cprint("c [main] skolem check ERROR")
        cprint("c checkSkolem main", err)
        raise SystemExit(1)


if __name__ == "__main__":
    main()
