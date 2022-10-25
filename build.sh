#!/usr/bin/env sh

set -eu

export VERSION="${1:-}"
python setup.py sdist
python setup.py bdist_wheel


