#!/bin/bash

# Merge apis/__init__.py
version="${1:-"0.1.0"}"
VERSION="$version" envsubst '$VERSION' < setup.py.in > "setup.py"

cd "$output_folder"
python setup.py sdist
python setup.py bdist_wheel


