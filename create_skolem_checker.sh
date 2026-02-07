#!/bin/bash

ulimit -t unlimited
shopt -s nullglob

filespos="synth"
# Directory containing QDIMACS specs (override via env SPEC_DIR)
SPEC_DIR="${SPEC_DIR:-${SLURM_SUBMIT_DIR}/inputfiles/${filespos}}"
# Directory containing corresponding skolem outputs (override via env SKOLEM_DIR)
SKOLEM_DIR="${SKOLEM_DIR:-${SLURM_SUBMIT_DIR}/outfiles}"


opts_arr=(
"python checkSkolem.py "
)

output="out-manthan"
tlimit="3600"
#tlimit="600"
#4.5GB mem limit
#memlimit="4500000"
# memlimit="20000000"
#9GB mem limit
memlimit="9000000"
numthreads=$((OMPI_COMM_WORLD_SIZE))

# May comment out the below echo commands later
echo "Job is running on node ${SLURM_JOB_NODELIST}"
echo "Rank is: ${OMPI_COMM_WORLD_RANK}"
echo "SLURM: sbatch is running on ${SLURM_SUBMIT_HOST}"
echo "SLURM: working directory is ${SLURM_SUBMIT_DIR}"
echo "SLURM: job identifier is ${SLURM_JOB_ID}"
echo "SLURM: job name is ${SLURM_JOB_NAME}"
echo "SLURM: current home directory is $HOME"
echo "SCRATCH     is ${SCRATCH}"
echo "workdir     is ${WORKDIR}"
echo "servpermdir is ${SERVPERMDIR}"
echo "Output dir  is ${output}"

WORKDIR="$SCRATCH/scratch/${SLURM_JOB_ID}_${OMPI_COMM_WORLD_RANK}"
output="${output}-${SLURM_JOB_ID}"

# echo "Transferring files from server to compute node"
mkdir -p "${WORKDIR}"
cd "${WORKDIR}" || exit

files=$(ls ${SPEC_DIR}/*.qdimacs.gz ${SPEC_DIR}/*.qdimacs 2>/dev/null | shuf --random-source="${SCRATCH}/rndfile")
files=$(ls ${SPEC_DIR}/*.qdimacs.gz ${SPEC_DIR}/*.qdimacs 2>/dev/null | shuf --random-source="${SCRATCH}/rndfile")
outputdir="${SCRATCH}/outfiles/"
orig=$(pwd)
mkdir -p manthan
cd "manthan" || exit
ln -s ${SLURM_SUBMIT_DIR}/manthan/* .
cd "$orig" || exit

# create todo
rm -f todo
at_opt=0
numlines=0
mylinesper=0

add_todo() {
    echo "$1" >> todo
    lines_this=$((lines_this+1))
}
for opts in "${opts_arr[@]}"
do
    fin_out_dir="${output}-${at_opt}"
    mkdir -p "manthan/${fin_out_dir}" || exit
    for file in $files
    do
        lines_this=0
        filename=$(basename "$file")
        filenameunzipped=${filename%.gz}

        # create dir
        add_todo "mkdir -p ${outputdir}/${fin_out_dir}"
        add_todo "cp ${SPEC_DIR}/${filename} ."
        if [[ "${filename}" == *.gz ]]; then
            add_todo "gunzip ${filename}"
        fi
        baseout="${fin_out_dir}/${filename}"

        # run
        add_todo "./clean.sh"
        add_todo "skolem_path=\"${SKOLEM_DIR}/${filename}_skolem.v.xz\""
        add_todo "skolem_fallback=\"${SKOLEM_DIR}/${fin_out_dir}/${filenameunzipped%.qdimacs}_skolem.v\""
        add_todo "if [[ -f \"${skolem_path}\" ]]; then xz -d -c \"${skolem_path}\" > \"${filenameunzipped%.qdimacs}_skolem.v\"; skolem_use=\"${filenameunzipped%.qdimacs}_skolem.v\"; elif [[ -f \"${skolem_fallback}\" ]]; then skolem_use=\"${skolem_fallback}\"; else echo \"Missing skolem for ${filename}\"; exit 1; fi"
        add_todo "/usr/bin/time --verbose -o ${baseout}.timeout_manthan ./doalarm -t real ${tlimit} ${opts} --qdimacs ${filenameunzipped} --skolem \"${skolem_use}\" > ${baseout}.out_manthan 2>&1"

        #copy back result
	add_todo "xz ${baseout}.out* 2>/dev/null || true"
	add_todo "xz ${baseout}.timeout* 2>/dev/null || true"
	add_todo "rm -f core.*"

	add_todo "mv ${baseout}.out*.xz ${outputdir}/${fin_out_dir}/ 2>/dev/null || true"
	add_todo "mv ${baseout}.timeout*.xz ${outputdir}/${fin_out_dir}/ 2>/dev/null || true"

	
        add_todo "rm -f ${baseout}*"
        add_todo "rm -f ${filenameunzipped%.qdimacs}_skolem.v"
        add_todo "rm -f ${filenameunzipped}"
        add_todo "rm -f ${filename}"

        if [[ $mylinesper -eq 0 ]]; then
            mylinesper=$lines_this
        fi

        numlines=$((numlines+1))
    done
    (( at_opt++ ))
done

# create per-core todos
numper=$((numlines/numthreads))
remain=$((numlines-numper*numthreads))
if [[ $remain -ge 1 ]]; then
    numper=$((numper+1))
fi
remain=$((numlines-numper*(numthreads-1)))

moretime=$((tlimit+30))
mystart=0
for ((myi=0; myi < numthreads ; myi++))
do
    rm -f todo_$myi.sh
    if [[ $myi -eq $OMPI_COMM_WORLD_RANK ]]; then
        touch todo_$myi.sh
        echo "#!/bin/bash" > todo_$myi.sh
        echo "ulimit -t $moretime" >> todo_$myi.sh
        echo "ulimit -v $memlimit" >> todo_$myi.sh
        echo "ulimit -c 0" >> todo_$myi.sh
        echo "set -x" >> todo_$myi.sh
        echo "cd manthan" >> todo_$myi.sh
        echo "source ./todo.sh" >> todo_$myi.sh
        echo "source manthan-venv/bin/activate" >> todo_$myi.sh
    fi
    typeset -i myi
    typeset -i numper
    typeset -i mystart
    mystart=$((mystart + numper))
    if [[ $myi -lt $((numthreads-1)) ]]; then
        if [[ $mystart -gt $((numlines+numper)) ]]; then
            sleep 0
        else
            if [[ $mystart -lt $numlines ]]; then
                myp=$((numper*mylinesper))
                mys=$((mystart*mylinesper))
                if [[ $myi -eq $OMPI_COMM_WORLD_RANK ]]; then
                    head -n $mys todo | tail -n $myp >> todo_$myi.sh
                fi
            else
                #we are at boundary, e.g. numlines is 100, numper is 3, mystart is 102
                #we must only print the last numper-(mystart-numlines) = 3-2 = 1
                mys=$((mystart*mylinesper))
                p=$(( numper-mystart+numlines ))
                if [[ $p -gt 0 ]]; then
                    myp=$((p*mylinesper))
                    if [[ $myi -eq $OMPI_COMM_WORLD_RANK ]]; then
                        head -n $mys todo | tail -n $myp >> todo_$myi.sh
                    fi
                fi
            fi
        fi
    else
        if [[ $remain -gt 0 ]]; then
            mys=$((mystart*mylinesper))
            mr=$((remain*mylinesper))
            if [[ $myi -eq $OMPI_COMM_WORLD_RANK ]]; then
                head -n $mys todo | tail -n $mr >> todo_$myi.sh
            fi
        fi
    fi
    if [[ $myi -eq $OMPI_COMM_WORLD_RANK ]]; then
        echo "exit 0" >> todo_$myi.sh
        chmod +x todo_$myi.sh
    fi
done
# echo "Done."

# Execute todos
# echo "This is MPI exec number $OMPI_COMM_WORLD_RANK"
./todo_${OMPI_COMM_WORLD_RANK}.sh > "out_${OMPI_COMM_WORLD_RANK}"
echo "Finished waiting rank $OMPI_COMM_WORLD_RANK"

rm -f doalarm*
rm -rf manthan/manthan-venv
rm -rf manthan/dependencies
rm -rf manthan/*.cnf
rm -rf manthan/*.qdimacs
rm -rf manthan*
rm -rf tmp_*
rm -rf flow_*
rm -rf tmp
rm -f todo
rm -f todo_*
rm -rf out*
exit 0
