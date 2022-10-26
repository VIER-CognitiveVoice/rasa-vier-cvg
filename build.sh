#!/usr/bin/env sh

set -eu

if [ -e build ]
then
  rm -R build
fi

if [ -e dist ]
then
  rm -R dist
fi

version="${1:-}"
if [ -n "$version" ]
then
  sed -i 's/version="9.9.9"/version="'"$version"'"/' setup.py
fi

python setup.py sdist
python setup.py bdist_wheel


