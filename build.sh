#!/bin/bash

export VERSION="${1:-"0.1.0"}"
python setup.py sdist
python setup.py bdist_wheel


