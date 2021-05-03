"""
How to upload
python setup.py clean sdist bdist_wheel
twine upload dist/*
"""


# Always prefer setuptools over distutils
from setuptools import setup, find_packages

# To use a consistent encoding
from codecs import open
from os import path
import os

HERE = path.abspath(path.dirname(__file__))

with open(path.join(HERE, 'README.md')) as fd:
    md = fd.read()

version = md.split('version:', 1)[1].split('\n', 1)[0]
version = version.strip()


package_dir = {'': 'src'}

packages = ['termcontrol']

package_data = {'': ['*']}

entry_points = {'console_scripts': ['termcontrol = termcontrol.cli:main']}


def build_hijack_c():
    h = os.getcwd()
    os.chdir('./src/termcontrol')
    os.system('make')
    os.chdir(h)


build_hijack_c()

setup(
    name='termcontrol',
    version=version,
    description='Terminal TTY IO Control',
    long_description=md,
    long_description_content_type='text/markdown',
    # for async rx we assume rx is installed:
    install_requires=[],
    tests_require=['pytest2md>=20190430'],
    include_package_data=True,
    setup_requires=['wheel'],
    url='https://github.com/axiros/termcontrol',
    author='Gunther Klessinger',
    author_email='gklessinger@gmx.de',
    license='BSD',
    # See https://pypi.python.org/pypi?%3Aaction=list_classifiers
    classifiers=[
        # How mature is this project? Common values are
        #   3 - Alpha
        #   4 - Beta
        #   5 - Production/Stable
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Developers',
        'Operating System :: POSIX',
        'License :: OSI Approved :: BSD License',
        'Topic :: Terminals',
        'Topic :: Utilities',
        'Topic :: System :: Shells',
        'Topic :: System :: System Shells',
        # Specify the Python versions you support here. In particular, ensure
        # that you indicate whether you support Python 2, Python 3 or both.
        'Programming Language :: Python :: 2',
        # most will work, tests are done for 3 only though, using py3 excl. constructs:
        'Environment :: Console',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: C',
    ],
    keywords=['fzf', 'terminal', 'tty', 'pty', 'IO', 'hijack'],
    py_modules=['termcontrol'],
    zip_safe=False,
    package_dir=package_dir,
    packages=packages,
    package_data=package_data,
    entry_points=entry_points,
)
