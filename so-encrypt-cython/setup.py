from distutils.core import setup
from Cython.Build import cythonize
from pathlib import Path


def get_py_list(folder: str, recursive: bool = False):
    p = Path(folder).expanduser().resolve()

    if recursive:
        files = p.rglob("*.py")
    else:
        files = p.glob("*.py")

    py_list = [
        str(f)
        for f in sorted(files)
        if f.name != "__init__.py" and "__pycache__" not in str(f)
    ]

    return py_list


py_list = get_py_list("/home/jiyang/jiyang/Projects/so_test/service")
    
setup(ext_modules = cythonize(py_list))