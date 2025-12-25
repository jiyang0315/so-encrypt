from distutils.core import setup
from Cython.Build import cythonize
#[]内是要打包的文件名，也可多个文件
setup(ext_modules = cythonize(["mytest.py"]))