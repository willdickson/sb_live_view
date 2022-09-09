from setuptools import setup
from setuptools import find_packages
import os

setup(
    name='sb_live_view',
    version='0.0.0',
    description='A simple live viewer for OceanOptics spectrometers',
    long_description=__doc__,
    author='Will Dickson',
    author_email='wbd@caltech',
    license='MIT',

    classifiers=[
        'Development Status :: 3 - Alpha',
        'Intended Audience :: Science/Research',
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 2.7',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.3',
        'Programming Language :: Python :: 3.4',
        'Programming Language :: Python :: 3.5',
    ],

    packages=find_packages(exclude=['examples',]),
    #install_requires = [
    #    'matplotlib>=3.0.0', 
    #    'seabreeze>=2.0.0',
    #    ],
    entry_points = {
        'console_scripts' : [
            'sb-live-view=sb_live_view.live_view:main'
            ]
        }
)
