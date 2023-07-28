cd unique
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
    cp "interpolatingsolver/src/itp."* ../../itp.so
else
    echo "c could not found itp module"
    echo "c check if pyblind[global] is installed properly"
    echo "c check cmake log to see if pyblind is found or not"
    echo "c you might need to export pyblind[global] path and re run ./install_unique.sh"
    exit
fi