from distutils.core import setup
from Cython.Build import cythonize

setup(
    name = 'mkm recursive function',
    ext_modules = cythonize("mkm_recursive.pyx"),
)