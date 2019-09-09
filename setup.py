#!/usr/bin/env python3

# check python version
from sys import version_info
if version_info[0] != 3:
    raise RuntimeError("This module is written for Python 3.")

from distutils.core import setup

setup(
    name='PaperTTY',
    version='0.0.1',
    description='Display /dev/tty* on an e-Paper display.',
    author='Greg Meyer',
    author_email='gregory.meyer@gmail.com',
    packages=['papertty'],
    scripts=['bin/papertty'],
    include_package_data=True
)
