from setuptools import setup, find_packages
import setuptools
from setuptools.extension import Extension
from Cython.Build import cythonize
import numpy
from distutils import ccompiler
import os
import pysam
import glob
from sys import argv
import sysconfig


cfg_vars = sysconfig.get_config_vars()
for key, value in cfg_vars.items():
    if type(value) == str:
        cfg_vars[key] = value.replace("-Wstrict-prototypes", "")


def has_flag(compiler, flagname):
    """Return a boolean indicating whether a flag name is supported on
    the specified compiler.
    """
    import tempfile
    with tempfile.NamedTemporaryFile('w', suffix='.cpp') as f:
        f.write('int main (int argc, char **argv) { return 0; }')
        try:
            compiler.compile([f.name], extra_postargs=[flagname])
        except setuptools.distutils.errors.CompileError:
            return False
    return True


def cpp_flag(compiler, flags):
    """Return the -std=c++[11/14/17,20] compiler flag.
    The newer version is prefered over c++11 (when it is available).
    """
    for flag in flags:
        if has_flag(compiler, flag):
            return flag


def get_extra_args():
    compiler = ccompiler.new_compiler()
    extra_compile_args = []
    flags = ['-std=c++17', '-std=c++14', '-std=c++11']
    f = cpp_flag(compiler, flags)
    if not f:
        return ['-std=c++11']
    extra_compile_args.append(f)
    flags = ['-stdlib=libc++']
    f = cpp_flag(compiler, flags)
    if f:
        extra_compile_args.append(f)

    return extra_compile_args


extras = get_extra_args() + ["-Wno-sign-compare", "-Wno-unused-function",
                             "-Wno-unused-result", '-Wno-ignored-qualifiers',
                             "-Wno-deprecated-declarations", "-fpermissive",
                             "-Wno-unreachable-code-fallthrough", "-Wdeprecated-builtins"
                             ]

ext_modules = list()

root = os.path.abspath(os.path.dirname(__file__))

if "--conda-prefix" in argv or os.getenv('PREFIX'):
    prefix = None
    if "--conda-prefix" in argv:
        idx = argv.index("--conda-prefix")
        h = argv[idx + 1]
        argv.remove("--conda-prefix")
        argv.remove(h)
    else:
        h = os.getenv('PREFIX')

    if h and os.path.exists(h):
        if any("libhts" in i for i in glob.glob(h + "/lib/*")):
            print("Using htslib at {}".format(h))
            prefix = h
            if prefix[-1] == "/":
                htslib = prefix[:-1]
        else:
            raise ValueError("libhts not found at ", h + "/lib/*")
    else:
        raise ValueError("prefix path does not exists")

    libraries = ["hts"]
    library_dirs = [f"{prefix}/lib", numpy.get_include()] + pysam.get_include()
    include_dirs = [numpy.get_include(), root,
                    f"{prefix}/include/htslib", f"{prefix}/include"] + pysam.get_include()
    runtime_dirs = [f"{prefix}/lib"]

else:
    # Try and link dynamically to htslib
    htslib = None
    if "--htslib" in argv:
        idx = argv.index("--htslib")
        h = argv[idx + 1]
        if h and os.path.exists(h):
            if any("libhts" in i for i in glob.glob(h + "/*")):
                print("Using --htslib at {}".format(h))
                htslib = h
                if htslib[-1] == "/":
                    htslib = htslib[:-1]
                argv.remove("--htslib")
                argv.remove(h)
        else:
            raise ValueError("--htslib path does not exists")

    if htslib is None:
        print("Using packaged htslib")
        htslib = os.path.join(root, "dysgu/htslib")

    libraries = [f"{htslib}/hts"]
    library_dirs = [htslib, numpy.get_include(), f"{htslib}/htslib"] + pysam.get_include()
    include_dirs = [numpy.get_include(), root,
                    f"{htslib}/htslib", f"{htslib}/cram"] + pysam.get_include()
    runtime_dirs = [htslib]


print("Libs", libraries)
print("Library dirs", library_dirs)
print("Include dirs", include_dirs)
print("Runtime dirs", runtime_dirs)
print("Extras compiler args", extras)

# Scikit-bio module
ssw_extra_compile_args = ["-Wno-deprecated-declarations", '-std=c99', '-I.']


ext_modules.append(Extension(f"dysgu.scikitbio._ssw_wrapper",
                             [f"dysgu/scikitbio/_ssw_wrapper.pyx", f"dysgu/scikitbio/ssw.c"],
                             include_dirs=[f"{root}/dysgu/scikitbio", numpy.get_include()],
                             extra_compile_args=ssw_extra_compile_args,
                             language="c"))

ext_modules.append(Extension(f"dysgu.edlib.edlib",
                             [f"dysgu/edlib/edlib.pyx", f"dysgu/edlib/src/edlib.cpp"],
                             include_dirs=[f"{root}/dysgu/edlib", numpy.get_include()],
                             extra_compile_args=["-O3", "-std=c++11"],
                             language="c++"))

# Dysgu modules
for item in ["sv2bam", "io_funcs", "graph", "coverage", "assembler", "call_component",
             "map_set_utils", "cluster", "sv_category", "extra_metrics"]:

    ext_modules.append(Extension(f"dysgu.{item}",
                                 [f"dysgu/{item}.pyx"],
                                 libraries=libraries,
                                 library_dirs=library_dirs,
                                 include_dirs=include_dirs,
                                 runtime_library_dirs=runtime_dirs,
                                 extra_compile_args=extras,
                                 define_macros=[("NPY_NO_DEPRECATED_API", "NPY_1_7_API_VERSION")],
                                 language="c++"))


print("Found packages", find_packages(where="."))
setup(
    name="dysgu",
    author="Kez Cleal",
    author_email="clealk@cardiff.ac.uk",
    url="https://github.com/kcleal/dysgu",
    description="Structural variant calling",
    license="MIT",
    version='1.6.3',
    python_requires='>=3.10',
    install_requires=[  # runtime requires
            'setuptools>=63.0',
            'cython',
            'click>=8.0',
            'numpy>=1.18',
            'scipy',
            'pandas',
            'pysam==0.22.0',
            'networkx>=2.4',
            'scikit-learn>=0.22',
            'sortedcontainers',
            'lightgbm',
        ],
    setup_requires=[
            'setuptools>=63.0',
            'cython',
            'click>=8.0',
            'numpy>=1.18',
            'scipy',
            'pandas',
            'pysam==0.22.0',
            'networkx>=2.4',
            'scikit-learn>=0.22',
            'sortedcontainers',
            'lightgbm',
        ],
    packages=["dysgu", "dysgu.tests", "dysgu.scikitbio", "dysgu.edlib"],
    ext_modules=cythonize(ext_modules),
    include_package_data=True,
    zip_safe=False,
    entry_points='''
        [console_scripts]
        dysgu=dysgu.main:cli
    ''',
)
