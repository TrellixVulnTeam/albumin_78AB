#!/usr/bin/env python3

import os
import codecs
import setuptools

root = os.path.abspath(os.path.dirname(__file__))
with open(os.path.join(root, 'README.rst'), encoding='utf-8') as f:
    readme = f.read()

setuptools.setup(
    name='albumin',
    version='0.1.0',
    description='Manage photographs using a git-annex repository',
    long_description=readme,
    url='https://github.com/alpernebbi/albumin',
    author='Alper Nebi Yasak',
    author_email='alpernebiyasak@gmail.com',
    license='GPL3+',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: End Users/Desktop',
        'Topic :: Multimedia',
        'License :: OSI Approved :: GNU General Public License v3 or later (GPLv3+)',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.5',
    ],
    entry_points={
        'console_scripts': [
            'albumin=albumin.cli:main',
        ],
    },
    keywords=['git', 'annex', 'metadata', 'photo', 'photograph', 'library'],
    py_modules=['albumin'],
    install_requires=['git-annex-adapter', 'pytz', 'PyExifTool'],
)