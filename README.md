## Manthan: A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in a F(X,Y) formula as input and returns Boolean function \Psi such that \exists Y F(X, Y) = F(X,\Psi(X)). Manthan works at the intersection of machine learning, constrained sampling, and automated reasoning. 

To read more about Manthan, have a look at [CAV-20 paper](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf) and [ICCAD-21 paper](https://arxiv.org/pdf/2108.05717.pdf)


## Requirements

* Python 3+

Install the required libraries:

```
python -m pip install -r requirements.txt
```
Manthan depends on:
1. [Open-WBO](https://github.com/sbjoshi/Open-WBO-Inc)  for MaxSAT queries
2. [PicoSAT](http://fmv.jku.at/picosat/) to compute unsat core. 
3. [Scikit-Learn](https://scikit-learn.org/stable/modules/tree.html) to create decision trees to learn candidates.  
4. [ABC](https://github.com/berkeley-abc/abc) to represent and manipulate Boolean functions.
5. [UNIQUE](https://github.com/perebor/unique) to extract the unique functions.

Manthan uses the algorithmic routine proposed by [BFSS](https://github.com/Sumith1896/bfss) to do preprocessing. We used a [CryptoMiniSAT](https://github.com/msoos/cryptominisat) based framework to do the preprocessing.

CryptoMiniSat is used via a prebuilt binary placed at `dependencies/cryptominisat5` (do not add it as a submodule). Download it from https://github.com/msoos/cryptominisat and verify the version:
```
./dependencies/cryptominisat5
c CMS SHA1: 7a62ccb6d63ab835b091b51e8d155629db3e78d2
c CryptoMiniSat version 5.13.0
```

## Dependency sources

You can initialize all dependency submodules at their pinned commits:

```
git submodule update --init --recursive
./scripts/clone_dependencies.sh
```

## Build dependencies

To build dependencies (including the `itp` Python module for Unique), use the scripts below. Make sure `pybind11` is installed in the same Python environment you plan to run Manthan with.

```
./scripts/clone_dependencies.sh
./scripts/build_dependencies_macos.sh
```

For Linux, use `./scripts/build_dependencies_linux.sh`. The scripts configure Unique with C++14 and bind to the active `python3` interpreter; the resulting module lives at `dependencies/unique/build/interpolatingsolver/src`.

Binaries are expected under `dependencies/static_bin/<os>/` (e.g., `dependencies/static_bin/macos/`). Copy the binaries for your OS into that directory if you build them elsewhere.
## How to Use

```bash
python manthan.py --preprocess --unique --multiclass --lexmaxsat <qdimacs input> 
```

## Skolem checker

Use the independent Skolem checker to validate a generated `*_skolem.v` against the original QDIMACS:

```
python src/checkSkolem.py --qdimacs <input.qdimacs> --skolem <input>_skolem.v --multiclass
```

To see a detailed list of available options:

```bash
python manthan.py [options]  <inputfile qdimacs> 
```
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
