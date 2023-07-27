file_write_verilog=build_dependencies/abc/file_write_verilog
if test -f "$file_write_verilog"; then
    echo "c $file_write_verilog exists."
    echo "c coping it to dependencies folder"
    cp  $file_write_verilog .
else 
    echo "WARNING! could not found $file_write_verilog"
    echo "WARNING! check ABC install and follow readme in build_dependencies/abc"
fi

file_generation_cnf=build_dependencies/abc/file_generation_cnf
if test -f "$file_generation_cnf"; then
    echo "c $file_generation_cnf exists."
    echo "c coping it to dependencies folder"
    cp  $file_generation_cnf .
else 
    echo "WARNING! could not found $file_generation_cnf"
    echo "WARNING! check ABC install and follow readme in build_dependencies/abc"
fi

file_generation_cex=build_dependencies/abc/file_generation_cex
if test -f "$file_generation_cex"; then
    echo "c $file_generation_cex exists."
    echo "c coping it to dependencies folder"
    cp  $file_generation_cex .
else 
    echo "WARNING! could not found $file_generation_cex"
    echo "WARNING! check ABC install and follow readme in build_dependencies/abc"
fi

preprocess=build_dependencies/manthan-preprocess/build/preprocess
if test -f "$preprocess"; then
    echo "c $preprocess exists."
    echo "c coping it to dependencies folder"
    cp  $preprocess .
else 
    echo "WARNING! could not found $preprocess"
    echo "WARNING! check preprocess install and follow readme in build_dependencies/manthan-preprocess"
fi

wbo=build_dependencies/open-wbo/open-wbo
if test -f "$wbo"; then
    echo "c $wbo exists."
    echo "c coping it to dependencies folder"
    cp  $wbo .
else
    if  test -f "$wbo"*; then
    	echo "c $wbo exists."
    	echo "c coping it to dependencies folder"
    	cp  $wbo* open-wbo
    else
    	echo "WARNING! could not found $wbo"
    	echo "WARNING! check open-wbo install and follow INSTALL in build_dependencies/open-wbo"
    fi
fi

cmsgen=build_dependencies/cmsgen/build/cmsgen
if test -f "$cmsgen"; then
    echo "c $cmsgen exists."
    echo "c coping it to dependencies folder"
    cp  $cmsgen .
else 
    echo "WARNING! could not found $cmsgen"
    echo "WARNING! check cmsgen install and follow readme in build_dependencies/cmsgen"
fi

picosat=build_dependencies/picosat/picosat
if test -f "$picosat"; then
    echo "c $picosat exists."
    echo "c coping it to dependencies folder"
    cp  $picosat .
else 
    echo "WARNING! could not found $picosat"
    echo "WARNING! check picosat install and follow readme in build_dependencies/picosat"
fi
