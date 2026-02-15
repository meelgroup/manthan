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

def _build_bus_wrapper(formula_vars, wrapper_name):
    if not formula_vars:
        return ""
    max_var = max(formula_vars)
    bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
    vars_set = set(formula_vars)

    ports = ["i%s" % v for v in formula_vars] + ["out"]
    lines = []
    lines.append(_wrap_commas("module %s " % wrapper_name, ports))
    for v in formula_vars:
        lines.append("input i%s;\n" % v)
    lines.append("output out;\n")
    for i in range(bus_cnt):
        lines.append("wire [127:0] v_bus%d;\n" % i)
    for i in range(bus_cnt):
        base = i * 128
        for bit in range(128):
            var = base + bit + 1
            if var in vars_set:
                lines.append("assign v_bus%d[%d] = i%d;\n" % (i, bit, var))
            else:
                lines.append("assign v_bus%d[%d] = 1'b0;\n" % (i, bit))
    bus_args = ["v_bus%d" % i for i in range(bus_cnt)] + ["out"]
    lines.append("FORMULA F ( %s );\n" % (", ".join(bus_args)))
    lines.append("endmodule\n")
    return "".join(lines)


def _build_bus_inst_wrapper(wrapper_name, args, Xvar, Yvar, target_module):
    if not args:
        return ""
    max_var = max([0] + list(Xvar) + list(Yvar))
    max_y = max([0] + list(Yvar))
    i_bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
    o_bus_cnt = (max_y + 127) // 128 if max_y > 0 else 0
    xset = set(Xvar)
    yset = set(Yvar)
    ports = ["i_bus%d" % i for i in range(i_bus_cnt)] + ["o_bus%d" % i for i in range(o_bus_cnt)] + ["out"]
    lines = []
    lines.append("module %s ( %s );\n" % (wrapper_name, ", ".join(ports)))
    for i in range(i_bus_cnt):
        lines.append("input [127:0] i_bus%d;\n" % i)
    for i in range(o_bus_cnt):
        lines.append("input [127:0] o_bus%d;\n" % i)
    lines.append("output out;\n")
    for arg in args:
        lines.append("wire %s;\n" % arg)
    for arg in args:
        v = int(arg[1:])
        seg = (v - 1) // 128
        off = (v - 1) % 128
        if v in xset:
            lines.append("assign %s = i_bus%d[%d];\n" % (arg, seg, off))
        elif v in yset:
            lines.append("assign %s = o_bus%d[%d];\n" % (arg, seg, off))
    conns = [".%s(%s)" % (a, a) for a in args] + [".out(out)"]
    lines.append(_wrap_commas("%s F_ " % target_module, conns))
    lines.append("endmodule\n")
    return "".join(lines)


def selfsubstitute(Xvar, Yvar, var, selfsub, verilog_formula, selfsub_dir):
    _ensure_dir(selfsub_dir)
    formula_vars = _formula_vars(Xvar, Yvar)
    bused_formula = "v_bus0" in verilog_formula
    wrapper_name = "FORMULA"
    wrapper_content = ""
    bus_wrapper_content = ""
    bus_wrapper_name = ""
    if bused_formula:
        wrapper_name = "FORMULA_SCALAR_%s" % (var)
        wrapper_content = _build_bus_wrapper(formula_vars, wrapper_name)
    index_selfsub = selfsub.index(var)

    def build_io(exclude_selfsub):
        arglist = []
        selfsub_ports = []
        selfsub_declarestr = ""
        for v in formula_vars:
            if v == var:
                arglist.append("#")
                continue
            if exclude_selfsub and v in selfsub:
                continue
            sig = "i%s" % (v)
            arglist.append(sig)
            selfsub_ports.append(sig)
            selfsub_declarestr += "input %s;\n" % (sig)
        return arglist, selfsub_ports, selfsub_declarestr

    file_write_verilog = _static_bin_path("file_write_verilog")

    if index_selfsub == 0:
        arglist, selfsub_ports, selfsub_declarestr = build_io(False)
        write_str_true = _wrap_commas("module FORMULA%s_true " % var, selfsub_ports + ["out"])
        write_str_false = _wrap_commas("module FORMULA%s_false " % var, selfsub_ports + ["out"])
        write_str = selfsub_declarestr + "output out;\n"
        write_str += "wire one;\n"
        write_str += "wire zero;\n"
        write_str += "assign one = 1;\n"
        write_str += "assign zero = 0;\n"
        args_one = [("one" if a == "#" else a) for a in arglist]
        args_zero = [("zero" if a == "#" else a) for a in arglist]
        formula_true = _wrap_commas("%s F%s_ " % (wrapper_name, var), args_one + ["out"])
        formula_false = _wrap_commas("%s F%s_ " % (wrapper_name, var), args_zero + ["out"])

        true_path = os.path.join(selfsub_dir, "formula%s_true.v" % (var))
        false_path = os.path.join(selfsub_dir, "formula%s_false.v" % (var))
        args = list(selfsub_ports)
        if bused_formula:
            bus_wrapper_name = "FORMULA%s_true_BUS" % (var)
            bus_wrapper_content = _build_bus_inst_wrapper(
                bus_wrapper_name, args, Xvar, Yvar, "FORMULA%s_true" % var)
        with open(true_path, "w") as f:
            f.write(write_str_true + write_str + formula_true + "\nendmodule\n")
            if wrapper_content:
                f.write(wrapper_content)
            if bus_wrapper_content:
                f.write(bus_wrapper_content)
        with open(false_path, "w") as f:
            f.write(write_str_false + write_str + formula_false + "\nendmodule\n")
            # Only include shared modules in the true file to avoid duplicates.

        # For bused formulas, ABC's write_verilog produces escaped identifiers that
        # file_generation_cex cannot parse reliably. Keep our generated verilog.
        if not bused_formula:
            subprocess.run([file_write_verilog, true_path, true_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            subprocess.run([file_write_verilog, false_path, false_path],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if bused_formula:
            max_var = max([0] + list(Xvar) + list(Yvar))
            max_y = max([0] + list(Yvar))
            i_bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
            o_bus_cnt = (max_y + 127) // 128 if max_y > 0 else 0
            bus_args = ["i_bus%d" % i for i in range(i_bus_cnt)] + ["o_bus%d" % i for i in range(o_bus_cnt)] + ["outsub%s" % var]
            inst = _wrap_commas("%s F%s_ " % (bus_wrapper_name, var), bus_args)
        else:
            args = [s.strip() for s in selfsub_inputstr.split(",") if s.strip()]
            conns = [".%s(%s)" % (a, a) for a in args] + [".out(outsub%s)" % var]
            inst = _wrap_commas("FORMULA%s_true F%s_ " % (var, var), conns)
        return_string = "wire outsub%s ;\n%s" % (var, inst)
        return return_string

    last_update = selfsub[index_selfsub - 1]
    true_prev = os.path.join(selfsub_dir, "formula%s_true.v" % (last_update))
    false_prev = os.path.join(selfsub_dir, "formula%s_false.v" % (last_update))

    arglist, selfsub_ports, selfsub_declarestr = build_io(True)
    write_str_true = _wrap_commas("module FORMULA%s_true " % var, selfsub_ports + ["out"])
    write_str_false = _wrap_commas("module FORMULA%s_false " % var, selfsub_ports + ["out"])
    write_str = selfsub_declarestr + "output out;\n"
    write_str += "wire one;\n"
    write_str += "wire zero;\n"
    write_str += "wire out1;\n"
    write_str += "wire out2;\n"
    write_str += "assign one = 1;\n"
    write_str += "assign zero = 0;\n"

    args_one = [("one" if a == "#" else a) for a in arglist]
    args_zero = [("zero" if a == "#" else a) for a in arglist]
    formula_true1 = _wrap_commas("FORMULA%s_true F%s_t1 " % (last_update, last_update), args_one + ["out1"])
    formula_true2 = _wrap_commas("FORMULA%s_false F%s_t2 " % (last_update, last_update), args_one + ["out2"])

    formula_false1 = _wrap_commas("FORMULA%s_false F%s_f1 " % (last_update, last_update), args_zero + ["out2"])
    formula_false2 = _wrap_commas("FORMULA%s_true F%s_f2 " % (last_update, last_update), args_zero + ["out1"])

    true_path = os.path.join(selfsub_dir, "formula%s_true.v" % (var))
    false_path = os.path.join(selfsub_dir, "formula%s_false.v" % (var))
    args = list(selfsub_ports)
    if bused_formula:
        bus_wrapper_name = "FORMULA%s_true_BUS" % (var)
        bus_wrapper_content = _build_bus_inst_wrapper(
            bus_wrapper_name, args, Xvar, Yvar, "FORMULA%s_true" % var)
    with open(true_path, "w") as f:
        f.write(write_str_true + write_str + formula_true1 + formula_true2)
        f.write("assign out = out1 | out2 ;\nendmodule\n")
        if wrapper_content:
            f.write(wrapper_content)
        if bus_wrapper_content:
            f.write(bus_wrapper_content)
    with open(false_path, "w") as f:
        f.write(write_str_false + write_str + formula_false1 + formula_false2)
        f.write("assign out = out1 | out2 ;\nendmodule\n")
        # Only include shared modules in the true file to avoid duplicates.

    # For bused formulas, ABC's write_verilog produces escaped identifiers that
    # file_generation_cex cannot parse reliably. Keep our generated verilog.
    if not bused_formula:
        subprocess.run([file_write_verilog, true_path, true_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        subprocess.run([file_write_verilog, false_path, false_path],
                       stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    if bused_formula:
        max_var = max([0] + list(Xvar) + list(Yvar))
        max_y = max([0] + list(Yvar))
        i_bus_cnt = (max_var + 127) // 128 if max_var > 0 else 0
        o_bus_cnt = (max_y + 127) // 128 if max_y > 0 else 0
        bus_args = ["i_bus%d" % i for i in range(i_bus_cnt)] + ["o_bus%d" % i for i in range(o_bus_cnt)] + ["outsub%s" % var]
        inst = _wrap_commas("%s F%s_ " % (bus_wrapper_name, var), bus_args)
    else:
        args = [s.strip() for s in selfsub_inputstr.split(",") if s.strip()]
        conns = [".%s(%s)" % (a, a) for a in args] + [".out(outsub%s)" % var]
        inst = _wrap_commas("FORMULA%s_true F%s_ " % (var, var), conns)
    return_string = "wire outsub%s ;\n%s" % (var, inst)
    return return_string


def load_selfsub_modules(selfsub, selfsub_dir):
    if not selfsub or not selfsub_dir:
        return ""
    content = ""
    for var in selfsub:
        true_path = os.path.join(selfsub_dir, "formula%s_true.v" % (var))
        false_path = os.path.join(selfsub_dir, "formula%s_false.v" % (var))
        if os.path.isfile(true_path):
            with open(true_path, "r") as f:
                content += "\n" + f.read()
        if os.path.isfile(false_path):
            with open(false_path, "r") as f:
                content += "\n" + f.read()
    return content
