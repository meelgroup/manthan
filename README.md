## Manthan- A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in a \exists Y F(X,Y) formula as input and returns Boolean function \Psi such that \exists Y F(X, Y) = F(X,\Psi(X)). Manthan works at the intersection of machine learning, constrained sampling, and automated reasoning. This work is by Priyanka Golia, Subhajit Roy and Kuldeep S. Meel, as published in [CAV-20](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf)


## Requirements to run

The required binaries are included in `dependencies` folder.


* Python 2.7

To install the required libraries, run:

```
python2.7 -m pip install -r requirements.txt
```


## How to Use

A simple invocation look like:
```bash
python2.7 manthan.py --seed <int> --varlist <list of Y variables> <inputfile verilog> 
```
### Examples of use:

```
python manthan.py --seed 1 --varlist benchmarks/Yvarlist/adder_varstoelim.txt benchmarks/adder.v
```
```
generating samples  10000
weighted samples....
leaning candidate skolem functions..
Total number of refinement needed 0
error formula unsat.. skolem functions generated
error formula unsat..reverse substituing...

Skolem functions: adder_skolem.v

```
you can also provide different option to consider for manthan.

```
python manthan.py [options] --seed <int>  --varlist <list of Y variables> <inputfile verilog> 
```

### Options

1. Required
    - input in verilog format
    - list of Y variables
    - random seed

    
2. Optional

|        Argument          |       Type        | Default value  | Description | 
| -----------------------  | ----------------- | ---------------| ----------- |
| --verb   |   {0, 1 ,2}   | 0 | verbose  |
| --gini | float | 0.005 | minimum impurity drop  |
| --weighted | {0,1} | 1 | to do weighted sampling set 1; to do uniform sampling set 0 |
| --showtrees  | {0,1} | 0 | to show the decision tree learnt by Manthan |
| --maxrefineitr  | int | 1000 | maximum number of allowed refinement iterations |
| --selfsubthres  | int | 10 | self substitution threshold
| --logtime  | {0,1} | 1 | to log the time taken by individual module; if 1 it give a file `timedetails`  |
| --samples  | int | 0 | set 1 to use given samples to learn; if 0: manthan will decide number of samples as per |Y| |
| --maxsamp  | int | - | required --samples to 1; number of samples to learn candidate functions.

We did experiments with random seed 10.

## Benchmarks
Few benchmarks are given in `benchmarks` directory and their corresponding Y variable list is in `benchmarks\Yvarlist` directory. 

Full list of benchmarks used for our experiments is available [here](https://zenodo.org/record/3892859#.XuTB2XUzZhE).

## Issues, questions, bugs, etc.
Please click on "issues" at the top and [create a new issue](https://github.com/meelgroup/manthan/issues). All issues are responded to promptly.

## How to Cite
```
@inproceedings{GRM20,
author={Golia, Priyanka and  Roy, Subhajit and  Meel, Kuldeep S.},
title={Manthan: A Data-Driven Approach for Boolean Function Synthesis},
booktitle={Proceedings of International Conference on Computer-Aided Verification (CAV)},
month={7},
year={2020}
}
```
## Contributors
* Priyanka Golia (pgoila@cse.iitk.ac.in)
* Subhajit Roy (subhajit@cse.iitk.ac.in)
* Kuldeep Meel (meel@comp.nus.edu.sg)


