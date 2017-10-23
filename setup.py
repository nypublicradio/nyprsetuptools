"""
NYPR Setuptools Extensions
"""

from setuptools import setup

setup(
    name='nyprsetuptools',
    version='0.0.11',
    author='NYPR Digital',
    author_email='digitalops@nypublicradio.org',
    url='https://github.com/nypublicradio/nyprsetuptools',
    description=__doc__,
    long_description=__doc__,
    packages=[
        'nyprsetuptools',
        'nyprsetuptools.commands',
        'nyprsetuptools.util',
    ],
    package_dir={
        'nyprsetuptools': 'nyprsetuptools',
    },
    scripts=[
        'scripts/nyprsetuptools',
    ],
    zip_safe=True,
    license='BSD',
)
