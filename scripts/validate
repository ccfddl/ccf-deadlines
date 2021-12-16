#!/usr/bin/env python

"""
pre-commit hook to check conference yml files

To use it normally as git pre-commit hook,
make a symlink and install dependencies:
$ ln -s ../../scripts/validate .git/hooks/pre-commit
$ pip install PyYAML jsonschema
"""

import os
import sys

from io import StringIO
from unittest import TestCase, TestLoader, TextTestRunner

import jsonschema
import jsonschema.exceptions

import yaml

ROOT = os.path.dirname(os.path.dirname(os.path.realpath(__file__)))
DATA_ROOT = os.path.join(ROOT, 'conference')
YAML_SCHEMA = None

def load_conference_yaml_schema():
    global YAML_SCHEMA
    with open(os.path.join(ROOT, 'conference-yaml-schema.yml'), 'r') as schema:
        YAML_SCHEMA = yaml.load(schema, Loader=yaml.SafeLoader)


class ConferenceTest(TestCase):
    def test_conference_yaml_schema(self):
        self.assertTrue(os.path.isdir(DATA_ROOT))
        for sub in os.listdir(DATA_ROOT):
            subdir = os.path.join(DATA_ROOT, sub)
            if os.path.isdir(subdir):
                for conf in os.listdir(subdir):
                    if not conf.endswith('.yml'):
                        continue
                    with self.subTest(conf=conf):
                        conference_yml_path = os.path.join(DATA_ROOT, sub, conf)
                        with open(conference_yml_path, 'r') as conference_yml_file:
                            try:
                                conference_yml = yaml.load(conference_yml_file.read(), Loader=yaml.SafeLoader)
                            except Exception:
                                self.fail(msg=f'Conference \033[1;31m{conf}\033[m contains invalid YAML')
                            try:
                                jsonschema.validate(conference_yml, YAML_SCHEMA)
                            except jsonschema.exceptions.ValidationError:
                                self.fail(msg=f'Conference \033[1;31m{conf}\033[m contains invalid properties')


def run_test(testcase, msg):
    output = StringIO()
    suite = TestLoader().loadTestsFromTestCase(testcase)
    runner = TextTestRunner(output, verbosity=0)
    results = runner.run(suite)
    if not results.wasSuccessful():
        print(output.getvalue())
        print(msg.format(len(results.failures)))
        sys.exit(1)


def usage():
    print(__doc__)


if __name__ == '__main__':

    if '-h' in sys.argv or '--help' in sys.argv:
        usage()
        sys.exit(0)

    load_conference_yaml_schema()
    run_test(ConferenceTest,
             msg=('\033[1;31mThere are {0} error(s) inside repo. Please fix the errors and commit again.\033[m'))
