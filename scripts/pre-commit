#!/bin/bash

command_exists () {
  command -v "$1" >/dev/null 2>&1
}


python_module_exists () {
    /usr/bin/env python -c "import $1" >/dev/null 2>&1 
}

command_exists python || {
    echo
    echo "No python found, skip pre-commit hook."
    echo
    exit 0
}

python_module_exists yaml && python_module_exists jsonschema || {
    echo
    echo "To run pre-commit hook, please install the following modules."
    echo "\$ pip install PyYAML jsonschema"
    echo
    exit 0
}

exec "`dirname -- "$0"`/validate" $@
