## Manthan: A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in an F(X, Y) formula and returns a Boolean function \Psi such that
\exists Y F(X, Y) = F(X, \Psi(X)). It combines machine learning, constrained
sampling, and automated reasoning.

Learn more in the [CAV-20 paper](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf)
and [ICCAD-21 paper](https://arxiv.org/pdf/2108.05717.pdf).

## Quick start

System prerequisites:

- macOS: `brew install cmake gmp boost`
- Ubuntu: `sudo apt-get install -y build-essential cmake git pkg-config libgmp-dev zlib1g-dev libreadline-dev libboost-dev libboost-program-options-dev`

Create a virtual environment, install Python requirements, and build dependencies:

```bash
python3.13 -m venv manthan-venv
source manthan-venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
./scripts/setup.sh --build
```

If you want to clean and rebuild dependencies:

```bash
./scripts/setup.sh --clean
./scripts/setup.sh --build
```

To pull fresh changes in dependencies before rebuilding:

```bash
./scripts/setup.sh --update
```

## Usage

```bash
python manthan.py <qdimacs input>
```

To disable any of these flags, pass `0`:

```bash
python manthan.py --preprocess=0 --unique=0 --multiclass=0 --lexmaxsat=0 <qdimacs input>
```

Each of these options defaults to `1`, and specifying the flag without a value
still enables it (e.g., `--preprocess` is the same as `--preprocess=1`).


To see a detailed list of available options:

```bash
python manthan.py [options]  <inputfile qdimacs> 
```
```
python manthan.py --help
```
## Skolem checker

Use the independent Skolem checker to validate a generated `*_skolem.v` against the original QDIMACS:

```
python checkSkolem.py --qdimacs <input.qdimacs> --skolem <input>_skolem.v
```

## Smoke test

After setup, run:

```bash
python manthan.py benchmarks/max64.qdimacs --maxsamples=10 --maxrepairitr=10 --adaptivesample=0 --weightedsampling=0
```

## Benchmarks
Some benchmarks are available in the `benchmarks` directory. 

Full list of benchmarks used for our experiments is available [here](https://zenodo.org/record/3892859#.XuTB2XUzZhE). The dataset includes qdimacs and verilog benchmarks. 

## Issues and questions
Please [create a new issue](https://github.com/meelgroup/manthan/issues).

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
