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

## Using stand-alone scripts

Aspects of the **nyprsetuptools** library can be used for non-python projects
via the `nyprsetuptools` command line interface.

To get started, install the package.

```bash
pip install -U git+https://github.com/nypublicradio/nyprsetuptools.git
```

### DockerDeploy

The `DockerDeploy` command is a wrapper for common tasks involved in deploying
images to AWS ECS.

```
usage: nyprsetuptools DockerDeploy [-h] [--environment ENVIRONMENT]
                                   [--ecs-cluster ECS_CLUSTER]
                                   [--ecr-repository ECR_REPOSITORY]
                                   [--tag TAG]
                                   [--memory-reservation MEMORY_RESERVATION]
                                   [--memory-reservation-hard MEMORY_RESERVATION_HARD]
                                   [--cpu CPU] [--ports PORTS]
                                   [--command COMMAND] [--test TEST]
                                   [--test-user TEST_USER]
                                   [--no-service] [--wait WAIT]

optional arguments:
  -h, --help            show this help message and exit
  --environment         Environment to deploy
  --ecs-cluster         Base name of AWS ECS target cluster
  --ecr-repository      Base name of AWS ECR Docker repository
  --tag                 Docker image tag
  --memory-reservation  Soft memory reservation for container
  --memory-reservation-hard
                        Hard memory limit for container
  --cpu                 CPU resource limit for container
  --ports               Comma-delimited list of ports to expose on container
  --command             Command override for container
  --test                Command to test container after build
  --test-user           Container user to run tests (eg. if they require root)
  --no-service          Flag indicating that ECS task is not a service
  --wait                Integer value in seconds to wait for new tasks to start
```
