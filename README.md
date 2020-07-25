## Manthan- A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in a F(X,Y) formula as input and returns Boolean function \Psi such that \exists Y F(X, Y) = F(X,\Psi(X)). Manthan works at the intersection of machine learning, constrained sampling, and automated reasoning. 

This work is by Priyanka Golia, Subhajit Roy and Kuldeep S. Meel, as published in CAV-20. To read more about Manthan, please refer to [our paper](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf)


## Requirements to run

* Python 2.7+

To install the required libraries, run:

```
python -m pip install -r requirements.txt
```
Manthan depends on: 
1. [Open-WBO](https://github.com/sbjoshi/Open-WBO-Inc)  for MaxSAT queries
2. [PicoSAT](http://fmv.jku.at/picosat/) to compute unsat core. 
3. [Scikit-Learn](https://scikit-learn.org/stable/modules/tree.html) to create decision trees to learn candidates.  
4. [ABC](https://github.com/berkeley-abc/abc) to represent and manipulate Boolean functions. 

Manthan employ the algorithmic routine proposed by [BFSS](https://github.com/Sumith1896/bfss) to do preprocessing, and to convert qdimacs files to verilog.

In the `dependencies` directory, you will find 64-bit x86 Linux compiled binaries for all the required dependencies.

## How to Use

A simple invocation with verilog as input:
```bash
python manthan.py --varlist <Y variables> --verilog <inputfile verilog>
```
And, with qdimacs as input:
```bash
python manthan.py --qdimacs <inputfile qdimacs>
```
### Examples of use:

```
python manthan.py --seed 1 --varlist benchmarks/Yvarlist/adder_varstoelim.txt --verilog benchmarks/adder.v

generating samples  10000
weighted samples....
leaning candidate skolem functions..
total number of refinement needed 0
error formula unsat.. skolem functions generated
error formula unsat..reverse substituing...

skolem function: adder_skolem.v

```

you can also provide different option to consider for manthan.

```
python manthan.py [options]  --varlist <Y variables>  --verilog <inputfile verilog> 
                             or 
python manthan.py [options]  --qdimacs <inputfile qdimacs> 
```
To see detailed list of available option:

```
python manthan.py --help
```


## Benchmarks
Few benchmarks are given in `benchmarks` directory and their corresponding Y variable list is in `benchmarks\Yvarlist` directory. 

Full list of benchmarks used for our experiments is available [here](https://zenodo.org/record/3892859#.XuTB2XUzZhE). The dataset includes qdimacs and verilog benchmarks. 

You can use readCnf provided by [BFSS](https://github.com/Sumith1896/bfss) to convert qdimacs files to verilog. 

We have also included complied readCnf in `dependencies` directory.  Running 

```
./dependencies/readCnf benchmark.qdimacs
```
creates 2 new files in the working directory: benchmark.v and benchmark_vars.txt (list of variables to be eliminated).

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


