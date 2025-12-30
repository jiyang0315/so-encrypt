#!/bin/sh
# Absolute path to this script, e.g. /home/user/bin/foo.sh
SCRIPT=$(readlink -f "$0")
# Absolute path this script is in, thus /home/user/bin
SCRIPT_PATH=$(dirname "$SCRIPT")

PYTHONHOME=/home/jiyang/miniconda3/envs/mytest
export PYTHONHOME
NUITKA_PYTHONPATH="/data1/jiyang/jiyang/Projects/so_test:/home/jiyang/miniconda3/envs/mytest/lib/python3.12:/home/jiyang/miniconda3/envs/mytest/lib/python3.12/lib-dynload:/home/jiyang/miniconda3/envs/mytest/lib/python3.12/site-packages:/home/jiyang/miniconda3/envs/mytest/lib/python3.12/site-packages/setuptools/_vendor"
export NUITKA_PYTHONPATH
PYTHONPATH="/data1/jiyang/jiyang/Projects/so_test:/home/jiyang/miniconda3/envs/mytest/lib/python3.12:/home/jiyang/miniconda3/envs/mytest/lib/python3.12/lib-dynload:/home/jiyang/miniconda3/envs/mytest/lib/python3.12/site-packages:/home/jiyang/miniconda3/envs/mytest/lib/python3.12/site-packages/setuptools/_vendor"
export PYTHONPATH

"$SCRIPT_PATH/hello.bin" $@

