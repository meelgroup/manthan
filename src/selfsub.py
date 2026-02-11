#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Self-substitution helpers adapted from the original manthan flow.
"""

import os
import subprocess


def _static_bin_path(bin_name):
    preferred = os.path.join("./dependencies/static_bin", bin_name)
    if os.path.isfile(preferred) and os.access(preferred, os.X_OK):
        return os.path.abspath(preferred)
    fallback = os.path.join("./dependencies", bin_name)
    return os.path.abspath(fallback)


def _ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def _formula_vars(Xvar, Yvar):
    return list(Xvar) + list(Yvar)


def selfsubstitute(Xvar, Yvar, var, selfsub, verilog_formula, selfsub_dir):
    _ensure_dir(selfsub_dir)
    formula_vars = _formula_vars(Xvar, Yvar)
    index_selfsub = selfsub.index(var)

    def build_io(exclude_selfsub):
        inputstr = "FORMULA F%s_ ( " % (var)
        selfsub_inputstr = ""
        selfsub_declarestr = ""
        for v in formula_vars:
            if v == var:
                inputstr += "# ,"
                continue
            if exclude_selfsub and v in selfsub:
                continue
            sig = "i%s" % (v)
            inputstr += "%s ," % (sig)
            selfsub_inputstr += "%s ," % (sig)
            selfsub_declarestr += "input %s;\n" % (sig)
        inputstr += "out );\nendmodule"
        return inputstr, selfsub_inputstr, selfsub_declarestr

    file_write_verilog = _static_bin_path("file_write_verilog")

    if index_selfsub == 0:
        inputstr, selfsub_inputstr, selfsub_declarestr = build_io(False)
        write_str_true = "module FORMULA%s_true ( %s out);\n" % (var, selfsub_inputstr)
        write_str_false = "module FORMULA%s_false ( %s out);\n" % (var, selfsub_inputstr)
        write_str = selfsub_declarestr + "output out;\n"
        write_str += "wire one;\n"
        write_str += "wire zero;\n"
        write_str += "assign one = 1;\n"
        write_str += "assign zero = 0;\n"
        formula_true = inputstr.replace("#", "one")
        formula_false = inputstr.replace("#", "zero")

        true_path = os.path.join(selfsub_dir, "formula%s_true.v" % (var))
        false_path = os.path.join(selfsub_dir, "formula%s_false.v" % (var))
        with open(true_path, "w") as f:
            f.write(write_str_true + write_str + formula_true + "\n")
            f.write(verilog_formula)
        with open(false_path, "w") as f:
            f.write(write_str_false + write_str + formula_false + "\n")
            f.write(verilog_formula)

        subprocess.run([file_write_verilog, true_path, true_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([file_write_verilog, false_path, false_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        return_string = "wire outsub%s ;\nFORMULA%s_true F%s_ ( %s outsub%s);\n" % (
            var, var, var, selfsub_inputstr, var)
        return return_string

    last_update = selfsub[index_selfsub - 1]
    true_prev = os.path.join(selfsub_dir, "formula%s_true.v" % (last_update))
    false_prev = os.path.join(selfsub_dir, "formula%s_false.v" % (last_update))
    with open(true_prev, "r") as f:
        file_content_true = f.read()
    with open(false_prev, "r") as f:
        file_content_false = f.read()
    if os.path.isfile(false_prev):
        os.remove(false_prev)

    inputstr, selfsub_inputstr, selfsub_declarestr = build_io(True)
    write_str_true = "module FORMULA%s_true ( %s out);\n" % (var, selfsub_inputstr)
    write_str_false = "module FORMULA%s_false ( %s out);\n" % (var, selfsub_inputstr)
    write_str = selfsub_declarestr + "output out;\n"
    write_str += "wire one;\n"
    write_str += "wire zero;\n"
    write_str += "wire out1;\n"
    write_str += "wire out2;\n"
    write_str += "assign one = 1;\n"
    write_str += "assign zero = 0;\n"

    formula_true = inputstr.replace("#", "one")
    formula_true1 = "FORMULA%s_true F%s ( %sout1 );\n" % (
        last_update, last_update, formula_true)
    formula_true2 = "FORMULA%s_false F%s ( %sout2 );\n" % (
        last_update, last_update, formula_true)

    formula_false = inputstr.replace("#", "zero")
    formula_false1 = "FORMULA%s_false F%s( %sout2 );\n" % (
        last_update, last_update, formula_false)
    formula_false2 = "FORMULA%s_true F%s( %sout1 );\n" % (
        last_update, last_update, formula_false)

    true_path = os.path.join(selfsub_dir, "formula%s_true.v" % (var))
    false_path = os.path.join(selfsub_dir, "formula%s_false.v" % (var))
    with open(true_path, "w") as f:
        f.write(write_str_true + write_str + formula_true1 + formula_true2)
        f.write("assign out = out1 | out2 ;\nendmodule\n")
        f.write(file_content_true + "\n")
        f.write(file_content_false + "\n")
    with open(false_path, "w") as f:
        f.write(write_str_false + write_str + formula_false1 + formula_false2)
        f.write("assign out = out1 | out2 ;\nendmodule\n")
        f.write(file_content_true + "\n")
        f.write(file_content_false + "\n")

    subprocess.run([file_write_verilog, true_path, true_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    subprocess.run([file_write_verilog, false_path, false_path],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    return_string = "wire outsub%s ;\nFORMULA%s_true F%s_ ( %s outsub%s);\n" % (
        var, var, var, selfsub_inputstr, var)
    return return_string


def load_selfsub_modules(selfsub, selfsub_dir):
    if not selfsub or not selfsub_dir:
        return ""
    content = ""
    for var in selfsub:
        path = os.path.join(selfsub_dir, "formula%s_true.v" % (var))
        if not os.path.isfile(path):
            continue
        with open(path, "r") as f:
            content += "\n" + f.read()
    return content
