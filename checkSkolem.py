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
    in_module = False
    port_blob = ""
    seen_ports = False
    with open(skolem_path, "r") as f:
        for line in f:
            match = re.match(r"\s*module\s+([A-Za-z_][A-Za-z0-9_]*)\s*\(", line)
            if match:
                if module_name is None:
                    module_name = match.group(1)
                    in_module = True
                    seen_ports = True
                    port_blob += line.split("(", 1)[1]
                else:
                    # Stop scanning outputs after the first module.
                    in_module = False
            elif in_module and seen_ports:
                port_blob += line
            if in_module and re.search(r"\boutput\s+out\b", line):
                has_out = True
            if in_module and seen_ports and ");" in line:
                in_module = False
                seen_ports = False
    if module_name is None:
        raise RuntimeError("Could not find module declaration in %s" % skolem_path)
    port_blob = port_blob.split(");", 1)[0]
    ports = [p.strip() for p in port_blob.replace("\n", " ").split(",") if p.strip()]
    is_bused = any(p.startswith("i_bus") or p.startswith("o_bus") for p in ports)
    return module_name, has_out, is_bused


def _wrap_concat(prefix, args, suffix=";\n", indent="  ", max_len=200):
    if not args:
        return prefix + "{}" + suffix
    current = prefix + "{" + args[0]
    lines = []
    for arg in args[1:]:
        if len(current) + 2 + len(arg) > max_len:
            lines.append(current + ",")
            current = indent + arg
        else:
            current += ", " + arg
    lines.append(current + "}" + suffix)
    return "\n".join(lines)


def _wrap_commas(prefix, args, suffix=";\n", indent="  ", max_len=200):
    if not args:
        return prefix + "()" + suffix
    current = prefix + "(" + args[0]
    lines = []
    for arg in args[1:]:
        if len(current) + 2 + len(arg) > max_len:
            lines.append(current + ",")
            current = indent + arg
        else:
            current += ", " + arg
    lines.append(current + ")" + suffix)
    return "\n".join(lines)

def _var_name(var_id):
    return "v%s" % var_id


def _ip_name(var_id):
    return "ip%s" % var_id


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
                name = _var_name(avar)
                declare += "%s," % name
                declare_input += "input %s;\n" % name
            continue

        if line.startswith("e"):
            e_variables = line.strip("e").strip("\n").strip(" ").split(" ")[:-1]
            for evar in e_variables:
                tmp_array.append(int(evar))
                name = _var_name(evar)
                declare += "%s," % name
                declare_input += "input %s;\n" % name
            continue

        declare_wire += "wire t_%s;\n" % (itr)

        clause_variable = line.strip(" \n").split(" ")[:-1]
        assign_expr = ""
        for var in clause_variable:
            if int(var) < 0:
                assign_expr += "~%s | " % (_var_name(abs(int(var))))
            else:
                assign_expr += "%s | " % (_var_name(abs(int(var))))

        assign_expr = assign_expr.strip("| ")
        assign_expr = _wrap_assign(assign_expr, indent="  ", max_terms=50, max_len=200)
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
            tcount_expr = _wrap_assign(tcount_expr, indent="  ", max_terms=50, max_len=200)
            assign_lines.append("assign tcount_%s = %s;\n" % (itr, tcount_expr))
            outstr += "tcount_%s & " % (itr)
            temp_assign = ""
        itr += 1

    if temp_assign != "":
        declare_wire += "wire tcount_%s;\n" % (itr)
        tcount_expr = temp_assign.strip("& ")
        tcount_expr = _wrap_assign(tcount_expr, indent="  ", max_terms=50, max_len=200)
        assign_lines.append("assign tcount_%s = %s;\n" % (itr, tcount_expr))
        outstr += "tcount_%s & " % (itr)
    out_expr = outstr.strip("& \n")
    out_expr = _wrap_assign(out_expr, indent="  ", max_terms=50, max_len=200)
    outstr = "assign out = %s;\n" % (out_expr)

    verilogformula = declare + declare_input + declare_wire + "".join(assign_lines) + outstr + "endmodule\n"

    return verilogformula


def _build_error_formula(Xvar, Yvar, verilog_formula, skolem_module):
    inputformula = []
    inputskolem = []
    inputerrorx = []
    inputerrory = []
    inputerroryp = []
    declarex = []
    declarey = []
    declareyp = []

    for var in Xvar:
        name = _var_name(var)
        inputformula.append(name)
        inputskolem.append(name)
        inputerrorx.append(name)
        declarex.append("input %s ;\n" % name)

    for var in Yvar:
        name = _var_name(var)
        ip_name = _ip_name(var)
        inputformula.append(name)
        inputerrory.append(name)
        declarey.append("input %s ;\n" % name)
        inputerroryp.append(ip_name)
        declareyp.append("input %s ;\n" % ip_name)
        inputskolem.append(ip_name)

    inputformula_call = _wrap_commas("FORMULA F_formula ", inputformula + ["out1"])
    inputformula_sk = _wrap_commas("FORMULA F_formulask ", inputskolem + ["out3"])
    inputskolem_call = _wrap_commas("%s F_skolem " % skolem_module, inputskolem + ["out2"])
    inputerrorx_line = _wrap_commas("module MAIN ", inputerrorx + inputerrory + inputerroryp + ["out"])
    declare = "".join(declarex) + "".join(declarey) + "".join(declareyp) + 'output out;\n' + \
        "wire out1;\n" + "wire out2;\n" + "wire out3;\n"
    # Use distinct instance names to avoid duplicate identifiers in the module.
    error_content = inputerrorx_line + declare + \
        inputformula_call + inputskolem_call + inputformula_sk
    error_content += "assign out = ( out1 & out2 & ~(out3) );\nendmodule\n"
    error_content += verilog_formula
    return error_content


def _build_wrapper(Xvar, Yvar, skolem_module, wrapper_name):
    decl_args = []
    decl_inputs = []
    for var in Xvar:
        name = _var_name(var)
        decl_args.append(name)
        decl_inputs.append("input %s;\n" % name)
    for var in Yvar:
        ip_name = _ip_name(var)
        decl_args.append(ip_name)
        decl_inputs.append("input %s;\n" % ip_name)
    decl_args.append("out")
    decl = _wrap_commas("module %s " % wrapper_name, decl_args)
    decl_inputs.append("output out;\n")

    wires = []
    inst_args = []
    for var in Xvar:
        inst_args.append(_var_name(var))
    for var in Yvar:
        wires.append("wire o%s;\n" % var)
        inst_args.append("o%s" % var)
    inst = _wrap_commas("%s U " % skolem_module, inst_args)

    tcount_wires = []
    tcount_assigns = []
    chunk = []
    chunk_size = 50
    tcount_names = []
    for var in Yvar:
        chunk.append("(~(o%s ^ %s))" % (var, _ip_name(var)))
        if len(chunk) >= chunk_size:
            name = "tcheck_%d" % (len(tcount_names) + 1)
            tcount_names.append(name)
            tcount_wires.append("wire %s;\n" % name)
            expr = " & ".join(chunk)
            expr = _wrap_assign(expr, indent="  ", max_terms=50, max_len=200)
            tcount_assigns.append("assign %s = %s;\n" % (name, expr))
            chunk = []
    if chunk:
        name = "tcheck_%d" % (len(tcount_names) + 1)
        tcount_names.append(name)
        tcount_wires.append("wire %s;\n" % name)
        expr = " & ".join(chunk)
        expr = _wrap_assign(expr, indent="  ", max_terms=50, max_len=200)
        tcount_assigns.append("assign %s = %s;\n" % (name, expr))

    if tcount_names:
        out_expr = " & ".join(tcount_names)
        out_expr = _wrap_assign(out_expr, indent="  ", max_terms=50, max_len=200)
    else:
        out_expr = "1'b1"
    assign = "assign out = %s;\n" % out_expr
    return (
        decl
        + "".join(decl_inputs)
        + "".join(wires)
        + "".join(tcount_wires)
        + inst
        + "".join(tcount_assigns)
        + assign
        + "endmodule\n"
    )


def _build_bus_wrapper(Xvar, Yvar, skolem_module, wrapper_name):
    max_var = max([0] + list(Xvar) + list(Yvar))
    max_y = max([0] + list(Yvar))
    i_bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
    o_bus_cnt = (max_y + 127) // 128 if max_y > 0 else 0

    decl_args = []
    decl_inputs = []
    for var in Xvar:
        name = _var_name(var)
        decl_args.append(name)
        decl_inputs.append("input %s;\n" % name)
    for var in Yvar:
        ip_name = _ip_name(var)
        decl_args.append(ip_name)
        decl_inputs.append("input %s;\n" % ip_name)
    decl_args.append("out")
    decl = _wrap_commas("module %s " % wrapper_name, decl_args)
    decl_inputs.append("output out;\n")

    wires = []
    assigns = []
    inst_args = []
    for i in range(i_bus_cnt):
        name = "i_bus%d" % i
        wires.append("wire [127:0] %s;\n" % name)
        base = i * 128
        for bit in range(127, -1, -1):
            var = base + bit + 1
            if var in Xvar:
                expr = _var_name(var)
            else:
                expr = "1'b0"
            assigns.append("assign %s[%d] = %s;\n" % (name, bit, expr))
        inst_args.append(name)
    for i in range(o_bus_cnt):
        name = "o_bus%d" % i
        wires.append("wire [127:0] %s;\n" % name)
        base = i * 128
        for bit in range(127, -1, -1):
            var = base + bit + 1
            if var in Yvar:
                expr = _ip_name(var)
            else:
                expr = "1'b0"
            assigns.append("assign %s[%d] = %s;\n" % (name, bit, expr))
        inst_args.append(name)
    inst_args.append("out")
    inst = _wrap_commas("%s U " % skolem_module, inst_args)

    return (
        decl
        + "".join(decl_inputs)
        + "".join(wires)
        + "".join(assigns)
        + inst
        + "endmodule\n"
    )


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

    skolem_module, has_out, is_bused = _skolem_module_info(skolem_path)
    if is_bused:
        wrapper_name = "SKOLEM_BUS_WRAPPER"
        wrapper_content = _build_bus_wrapper(Xvar, Yvar, skolem_module, wrapper_name)
    elif has_out:
        wrapper_name = skolem_module
        wrapper_content = ""
    else:
        wrapper_name = "SKOLEM_CHECK_WRAPPER"
        wrapper_content = _build_wrapper(Xvar, Yvar, skolem_module, wrapper_name)

    error_content = _build_error_formula(Xvar, Yvar, verilog_formula, wrapper_name)

    with open(skolem_path, "r") as f:
        skolem_lines = f.readlines()
    skolem_content = []
    for line in skolem_lines:
        stripped = line.lstrip()
        if stripped.startswith("module ") and "(" in line and ");" in line:
            prefix = line[:line.find("(")].rstrip() + " "
            args_blob = line[line.find("(") + 1:line.rfind(");")]
            args = [a.strip() for a in args_blob.split(",") if a.strip()]
            skolem_content.append(_wrap_commas(prefix, args, suffix=";\n"))
        else:
            skolem_content.append(line)
    skolem_content = "".join(skolem_content)

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
