[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)


## Manthan: A Data-Driven Approach for Boolean Functional Synthesis
Manthan takes in a \varphi(X,Y) formula as input and returns Boolean function F(X) such that \exists Y \varphi(X, Y) = \varphi(X, F(X)). Manthan works at the intersection of machine learning, constrained sampling, and automated reasoning. 

To read more about Manthan, have a look at [CAV-20 paper](https://priyanka-golia.github.io/publication/cav20-manthan/cav20-manthan.pdf) and [ICCAD-21 paper](https://arxiv.org/pdf/2108.05717.pdf). You can also refer to the related [slides](https://www.comp.nus.edu.sg/~meel/Slides/manthan.pdf) and the talk [video](https://www.youtube.com/watch?v=dXWWiKfY6cI&t=2s).

## Install

Clone Manthan

```
git clone https://github.com/meelgroup/manthan
cd manthan
```

### Requirements to run

* Python 3.7+

To install the required libraries, run the following:

```
python -m pip install -r requirements.txt
```
You might need to give `root` permission. In that case, run:

```
sudo python -m pip install -r requirements.txt
```




#### To install Unique

Manthan usage [UNIQUE](https://github.com/perebor/unique) to extract the unique functions. 

```
apt-get install build-essential cmake
apt-get install libboost-program-options-dev
python -m pip install python-sat==0.1.8.dev8
python -m pip install "pybind11[global]"
git clone https://github.com/perebor/unique.git
cd unique
git checkout 1902a5aa9573722cf473c7e8b5f49dedf9a4646d
git submodule init
git submodule update
mkdir build
cd build
cmake .. && make -j4
cd ../..

```

Manthan need to import `unique` via  a library, do the following:

```
cp unique/build/interpolatingsolver/src/itp.*-linux-gnu.so itp.so
```




#### Additional Dependencies

Manthan depends on: 
1. [Open-WBO](https://github.com/sat-group/open-wbo) and [RC2](https://pysathq.github.io/docs/html/api/examples/rc2.html)  for MaxSAT queries
2. [PicoSAT](http://fmv.jku.at/picosat/) to compute unsat core. 
3. [Scikit-Learn](https://scikit-learn.org/stable/modules/tree.html) to create decision trees to learn candidates.  
4. [ABC](https://github.com/berkeley-abc/abc) to represent and manipulate Boolean functions.
5. [CMSGEN](https://github.com/meelgroup/cmsgen) to sample satisfying assignments.

Manthan employs the algorithmic routine proposed by [BFSS](https://github.com/Sumith1896/bfss) to do preprocessing. We used a [CryptoMiniSAT](https://github.com/msoos/cryptominisat) based framework to do the preprocessing.  

In the `dependencies` directory, you will find 64-bit x86 Linux compiled binaries for the required dependencies.
In addition, if the compiled binaries in `dependencies` do not work on the system, do the following:

```
git submodule update --init --recursive

```
This will retrieve all the dependencies located in the `dependencies/build_dependencies` folder. Please refer to each individual README file (or INSTALL file in case of open-wbo) for instructions on how to compile these dependencies. After compilation, do the following:

```
cd dependencies
chmod +x mv_dependencies.sh
./mv_dependencies.sh
```
This will copy the compiled binaries to the `dependencies` folder.




## How to Use

```bash
python manthan.py  <qdimacs input> 
```

#### A sample invocation 

Let us consider  `benchmarks/test.qdimacs`:


```
p cnf 4 4
a 2 3 0
e 1 4 0
-1 2 0
-1 3 0
1 2 3 0
4 0
```

We need to find Skolem function corresponding to existentially quantified variables 1 and 4.

```
python manthan.py  benchmarks/test.qdimacs

```

```
starting Manthan
parsing
count X (universally qunatified variables) variables 2
count Y (existentially qunatified variables) variables 2
preprocessing: finding unates (constant functions)
count of positive unates 1
count of negative unates 0
finding uniquely defined functions
count of uniquely defined variables 0
generating weighted samples
generated samples.. learning candidate functions via decision learning
generated candidate functions for all variables.
verification check UNSAT
no more repair needed
number of repairs needed to converge 0
```

Manthan will store Skolem functions in a verilog file `test_skolem.v`. 

```
module SkolemFormula (i2, i3, o1, o4);
input i2, i3;
output o1, o4;
wire zero, one;
assign zero = 0;
assign one = 1;
wire w1;
wire w4;
wire wt3;
assign w1 = (( i2 & i3 & one ));
assign w4 = ( one );
assign wt3 = (~(w1 ^ o1)) & (~(w4 ^ o4));
assign o1 = w1;
assign o4 = w4;
endmodule
```
In this, `i2` and `i3` represent universally quantified variables `2` and `3`, and `o1` and `o4` defines existentially quantified variables `1` and `4`. Skolem function corresponding to `1` is `2 & 3` whereas Skolem function corresponding to `4` is constant one.

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


