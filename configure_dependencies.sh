pararser() {
    CurrDir=$(realpath dependencies)
    # Define default values
    cmsgen=${cmsgen:-"$CurrDir/cmsgen"}
    abc=${abc:-"$CurrDir/abc"}
    preprocess=${preprocess:-"$CurrDir/manthan-preprocess"}
    openwbo=${openwbo:-"$CurrDir/open-wbo"}
    picosat=${picosat:-"$CurrDir/picosat"}
    all=${all:-"no"}
    # Assign the values given by the user
    while [ $# -gt 0 ]; do
        if [[ $1 == *"--"* ]]; then
            param="${1/--/}"
            if [ "$param" = "all" ]; then
                declare -g $param="yes"
                if [ -z "$2" ]; then
                    echo "c setting building all dependencies on"
                else
                    if [[ $2 != *"--"* ]]; then
                        echo "WARNING! \"all\" does not take any parameter. Considering it on."
                        echo "c setting building all dependencies on"
                    fi
                fi
            else   
                declare -g $param="$2"
            fi
        fi
        shift
    done

}
pararser $@
export LOG_FILE="manthan_dependencies.cfg"
CFG_FILE=$(realpath $LOG_FILE)
echo "-n" > $CFG_FILE
Diritp=$(realpath itp.so)
unique="$CurrDir/unique"
cd $unique
if test -d "build"; then
    echo "c unique/build dir exists."
    echo "c clearing it"
    rm -r build
fi
mkdir build
cd build
export PATH=$HOME/.local/bin:$PATH
cmake .. && echo "c cmake to unique succeeded" || exit
make -j8 && echo "c make to unique succeeded" || exit
if test -f "interpolatingsolver/src/itp."*; then
    echo "c found itp module"
    Diritp=$(realpath interpolatingsolver/src/)
    export PYTHONPATH="${PYTHONPATH}:${Diritp}"
    echo "[ITP-Path]" >> $CFG_FILE
    echo "itp_path = "${Diritp} >> $CFG_FILE

else
    echo "c could not found itp module"
    echo "c check if pyblind[global] is installed properly"
    echo "c check cmake log to see if pyblind is found or not"
    echo "c you might need to export pyblind[global] path and re run ./configure_dependencies.sh"
    exit
fi


if [ "$all" = "yes" ]; then
    echo "Going to install all dependencies from the source code"
        echo "[Dependencies-Path]" >> $CFG_FILE
        source $CFG_FILE

        echo "c installing ABC"

        cd $abc
        make -j8 libabc.a && echo "c make to ABC succeeded" || exit

        gcc -Wall -g -c file_generation_cex.c -o file_generation_cex.o  && echo "c file_generation_cex complied" || exit
        g++ -g -o file_generation_cex file_generation_cex.o libabc.a -lm -ldl -lreadline -lpthread && echo "c file_generation_cex linked" || exit
        file_generation_cex=file_generation_cex
        if test -f "$file_generation_cex"; then
            echo "c $file_generation_cex exists."
            file_generation_cex_path=$(realpath $file_generation_cex)
            echo "file_generation_cex_path = "$file_generation_cex_path >> $CFG_FILE
        else 
            echo "ERROR! could not found $file_generation_cex"
            echo "ERROR! check ABC install and follow readme in build_dependencies/abc"
            exit
        fi

        echo "c ABC and its dependencies are sucessfully installed"


        echo "c installing CMSGen"
        cd $cmsgen
        if test -d "build"; then
            echo "c CMSGen/build dir exists."
            echo "c clearing it"
            rm -r build
        fi
        mkdir build
        cd build
        cmake .. && echo "c cmake to cmsgen succeeded" || exit
        make -j8 && echo "c make to cmsgen succeeded" || exit
        cmsgen_exe=cmsgen
        if test -f "$cmsgen_exe"; then
            echo "c $cmsgen_exe exists."
            cmsgen_path=$(realpath $cmsgen_exe)
            echo "cmsgen_path = " $cmsgen_path >> $CFG_FILE

        else 
            echo "Error! could not found $cmsgen_exe"
            echo "Error! check cmsgen install and follow readme in build_dependencies/cmsgen"
            exit
        fi
        echo "c cmsgen and its dependencies are sucessfully installed"


        echo "c installing Open-WBO"
        cd $openwbo
        make rs && echo "c make to open wbo succeeded" || exit
        wbo=open-wbo
        if test -f "$wbo"; then
            echo "c $wbo exists."
            openwbo_path=$(realpath $wbo)
            echo "openwbo_path = " $openwbo_path >> $CFG_FILE
        else
            if  test -f "$wbo"*; then
                echo "c $wbo exists."
                echo "c coping it to dependencies folder"
                openwbo_path=$(realpath $wbo*)
                echo "openwbo_path = " $openwbo_path >> $CFG_FILE
            else
                echo "Error! could not found $wbo"
                echo "Error! check open-wbo install and follow INSTALL in build_dependencies/open-wbo"
                exit
            fi
        fi
        echo "c open-wbo is sucessfully installed"


        echo "c installing picosat"
        cd $picosat
        ./configure.sh && echo "c configuration to picosat succeeded" || exit
        make -j4  && echo "c make to picosat succeeded" || exit
        picosat_exe=picosat
        if test -f "$picosat_exe"; then
            echo "c $picosat_exe exists."
            picosat_path=$(realpath $picosat_exe)
            echo "picosat_path = " $picosat_path >> $CFG_FILE
        else 
            echo "Error! could not found $picosat_exe"
            echo "Error! check picosat install and follow readme in build_dependencies/picosat"
            exit
        fi
        echo "c picosat is sucessfully installed"


        echo "c install preprocess"
        cd $preprocess
        cd louvain-community
        if test -d "build"; then
            echo "c manthan-preproces/louvain-community/build dir exists."
            echo "c clearing it"
            rm -r build
        fi
        mkdir build
        cd build
        cmake .. && echo "c cmake to louvain-community succeeded" || exit
        make -j8 && echo "c make to louvain-community succeeded" || exit
        echo "c louvain-community path set done"
        echo "c install cryptominisat"
        cd ../..
        cd cryptominisat
        if test -d "build"; then
            echo "c manthan-preproces/cryptominisat/build dir exists."
            echo "c clearing it"
            rm -r build
        fi
        mkdir build
        cd build
        cmake .. && echo "c cmake to cryptominisat succeeded" || exit
        make -j8 && echo "c make to cryptominisat succeeded" || exit
        cd ../..
        echo "c installing preprocess"
        if test -d "build"; then
            echo "c manthan-preproces/build dir exists."
            echo "c clearing it"
            rm -r build
        fi
        mkdir build
        cd build
        cmake .. && echo "c cmake to preprocess succeeded" || exit
        make -j8 && echo "c make to preprocess succeeded" || exit
        preprocess_exe=preprocess
        if test -f "$preprocess_exe"; then
            echo "c $preprocess_exe exists."
            preprocess_path=$(realpath $preprocess_exe)
            echo "preprocess_path = " $preprocess_path >> $CFG_FILE
        else 
            echo "Error! could not found $preprocess_exe"
            echo "Error! check preprocess install and follow readme in build_dependencies/preprocess"
            exit
        fi
else
    echo "Going to use precomplied static binaries from the dependencies/static_bin folder"
fi
exit

