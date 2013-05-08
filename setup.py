from setuptools import setup
import sys

# Python 3 conversion
extra = {}
if sys.version_info >= (3,):
    extra['use_2to3'] = True

setup(
    name='python-mydns',
    version='1.0.1',
    description="A library to connect to mydns mysql database and manage them.",
    author='Renato Covarrubias',
    author_email='rnt [at] rnt.cl]',
    packages=['mydns'],
    license='GPL-3.0',
    url='https://github.com/rnt/python-mydns',
    classifiers=[
        'Environment :: Console',
        'Environment :: Web Environment',
        'Intended Audience :: Developers',
        'Intended Audience :: System Administrators',
        'License :: OSI Approved :: GPL-3.0 License',
        'Operating System :: OS Independent',
        'Programming Language :: Python',
        'Topic :: Software Development :: Libraries :: Python Modules',
    ],
    **extra
)
