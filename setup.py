"""
NYPR Setuptools Extensions
"""

from setuptools import setup

setup(
    name='nyprsetuptools',
    version='0.0.16',
    author='NYPR Digital',
    author_email='digitalops@nypublicradio.org',
    url='https://github.com/nypublicradio/nyprsetuptools',
    description=__doc__.strip(),
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
    tests_require=[
        'pytest',
    ],
    zip_safe=True,
    license='BSD',
)
