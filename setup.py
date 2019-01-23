"""
NYPR Setuptools Extensions
"""

from setuptools import setup, find_packages

setup(
    author='NYPR Digital',
    author_email='digitalops@nypublicradio.org',
    description=__doc__,
    license='BSD',
    long_description=__doc__,
    name='nyprsetuptools',
    package_dir={},
    packages=find_packages(exclude=['tests']),
    url='https://github.com/nypublicradio/nyprsetuptools',
    version='0.0.15',
    scripts=[
        'scripts/nyprsetuptools',
    ],
    tests_require=[
        'pytest',
    ],
    zip_safe=True,
)
