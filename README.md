## Manthan: A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in a F(X,Y) formula as input and returns Boolean function \Psi such that \exists Y F(X, Y) = F(X,\Psi(X)). Manthan works at the intersection of machine learning, constrained sampling, and automated reasoning. 

To read more about Manthan, have a look at [CAV-20 paper](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf) and [ICCAD-21 paper](https://arxiv.org/pdf/2108.05717.pdf)


## Requirements to run

* Python 2.7+

To install the required libraries, run:

```
python -m pip install -r requirements.txt
```
Manthan depends on: 
1. [Open-WBO](https://github.com/sbjoshi/Open-WBO-Inc) and [RC2](https://pysathq.github.io/docs/html/api/examples/rc2.html)  for MaxSAT queries
2. [PicoSAT](http://fmv.jku.at/picosat/) to compute unsat core. 
3. [Scikit-Learn](https://scikit-learn.org/stable/modules/tree.html) to create decision trees to learn candidates.  
4. [ABC](https://github.com/berkeley-abc/abc) to represent and manipulate Boolean functions.
5. [UNIQUE](https://github.com/perebor/unique) to extract the unique functions.

Manthan employ the algorithmic routine proposed by [BFSS](https://github.com/Sumith1896/bfss) to do preprocessing. We used a [CryptoMiniSAT](https://github.com/msoos/cryptominisat) based framework to do the preprocessing.

In the `dependencies` directory, you will find 64-bit x86 Linux compiled binaries for the required dependencies.

## Install

To install Unique: Make sure you have python-sat installed.

```
git clone https://github.com/perebor/unique.git
cd unique
git checkout 1902a5aa9573722cf473c7e8b5f49dedf9a4646d
git submodule init
git submodule update
mkdir build
cd build
cmake .. && make

```

Now, clone Manthan

```
git clone https://github.com/meelgroup/manthan
cd manthan
cp ../unique/build/interpolatingsolver/src/itp.cpython-38-x86_64-linux-gnu.so itp.so
```
## How to Use

```bash
python manthan.py --preprocess --unique --multiclass --lexmaxsat <qdimacs input> 
```

## To test:

A simple invocation with benchmarks/max64.qdimacs

```
python manthan.py --multiclass --preprocess --unique --lexmaxsat --verb 1 benchmarks/max64.qdimacs

```

```

starting Manthan
parsing
count X variables 128
count Y variables 290
preprocessing: finding unates (constant functions)
count of positive unates 7
count of negative unates 5
finding uniquely defined functions
count of uniquely defined variables 277
parsing and converting to verilog
generating weighted samples
generated samples.. learning candidate functions
generated candidate functions for all variables.
verification check UNSAT
no more repair needed
number of repairs needed to converge 0
```

you can also provide different option to consider for manthan:

```
python manthan.py [options]  <inputfile qdimacs> 
```
To see detailed list of available option:

```
python manthan.py --help
```


## Benchmarks
Few benchmarks are given in `benchmarks` directory. 

Full list of benchmarks used for our experiments is available [here](https://zenodo.org/record/3892859#.XuTB2XUzZhE). The dataset includes qdimacs and verilog benchmarks. 

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

@inproceedings{GSRM21,
author={Golia, Priyanka and  Slivovsky, Friedrich and Roy, Subhajit and  Meel, Kuldeep S.},
title={Engineering an Efficient Boolean Functional Synthesis Engine},
booktitle={Proceedings of International Conference On Computer Aided Design (ICCAD)},
month={7},
year={2021}
}

```

## Contributors
* Priyanka Golia (pgoila@cse.iitk.ac.in)
* Subhajit Roy (subhajit@cse.iitk.ac.in)
* Kuldeep Meel (meel@comp.nus.edu.sg)


