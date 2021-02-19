## Manthan: A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in a F(X,Y) formula as input and returns Boolean function \Psi such that \exists Y F(X, Y) = F(X,\Psi(X)). Manthan works at the intersection of machine learning, constrained sampling, and automated reasoning. 

To read more about Manthan, please refer to [our paper](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf)


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
5. [UNIQUE](https://github.com/perebor/unique) to extract interpolant based definiations.

Manthan employ the algorithmic routine proposed by [BFSS](https://github.com/Sumith1896/bfss) to do preprocessing.

In the `dependencies` directory, you will find 64-bit x86 Linux compiled binaries for all the required dependencies.

## How to Use

```bash
python manthan.py  <inputfile qdimacs> 
```
### Examples of use:

```
python manthan.py --seed 10 --verb 1 --preprocess  <inputfile qdimacs>

```



 You can use `showtrees 1 ` to dump the learned trees, futhermore to see detailed list of available option:

```
python manthan.py --help
```

To synthesise function using interpolant based technique:


```
python manthan.py --seed 10 --verb 1 --preprocess --unique  <inputfile qdimacs>

```

The output F(X,\Psi(X)) would be stored as `inputfile-name_skolem.v`

## Benchmarks
We used matrix multiplication encoding discussed in polymath project to generate different benchmarks.

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
* Friedrich Slivovsky (fslivovsky@gmail.com)
* Subhajit Roy (subhajit@cse.iitk.ac.in)
* Kuldeep Meel (meel@comp.nus.edu.sg)


