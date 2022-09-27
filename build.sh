#!/bin/bash

version="${1:-"0.1.0"}"
# shellcheck disable=SC2016
VERSION="$version" envsubst '$VERSION' < setup.py.in > "setup.py"

python setup.py sdist
python setup.py bdist_wheel


