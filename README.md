# NYPRSetuptools

**nyprsetuptools** provides a set of extensions to python's **setuptools** to
enable cross-project access to common build/test/deploy routines.

## Including in setup.py

The method for including the extensions in this library is a bit unorthodox due
to the fact that `setup.py` is called before any dependencies are installed.
To utilize this library include these lines at the top of a project's `setup.py`
file.

```python
try:
    import nyprsetuptools
except ImportError:
    import pip
    pip.main(['install', '-U', 'git+https://github.com/nypublicradio/nyprsetuptools.git'])
    import nyprsetuptools
```

After the module is imported you can add commands to the `setup()` call's
`cmdclass` keyword argument.

```python
setup(
    name='myproject',
    version='0.0.2',
    ...
    cmdclass={
        'deploy': nyprsetuptools.LambdaDeploy,
        'requirements': nyprsetuptools.InstallRequirements,
        'test': nyprsetuptools.PyTest,
    }
    ...
)
```

The example above would enable the `deploy` and `requirements` commands and override the default test
behavior for `setup.py` with a pytest implementation.
