import os

# Force single-threaded numerical backends (scikit-learn/numpy).
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")
os.environ.setdefault("NUMEXPR_NUM_THREADS", "1")
os.environ.setdefault("VECLIB_MAXIMUM_THREADS", "1")
os.environ.setdefault("BLIS_NUM_THREADS", "1")

# Allow cluster users to provide BOOST_ROOT and have child processes inherit it.
if "BOOST_ROOT" in os.environ:
    os.environ["LD_LIBRARY_PATH"] = f"{os.environ['BOOST_ROOT']}/lib:" + os.environ.get("LD_LIBRARY_PATH", "")
