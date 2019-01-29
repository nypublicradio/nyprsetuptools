# NYPRSetuptools

**nyprsetuptools** provides a set of extensions to python's **setuptools** to
enable cross-project access to common build/test/deploy routines.

## Including in setup.py

To utilize this library include these lines in a project's `setup.py` file.
The commands specified in `entry_points` are optional and the names are arbitrary.
Developers may wish to swap `DockerDeploy` for `LambdaDeploy` or even include
multiple deployment methods by adding an additional command `deploy_lambda`, for example.

```python
    setup_requires=[
        'nyprsetuptools'
    ],
    dependency_links=[
        'https://github.com/nypublicradio/nyprsetuptools/tarball/master#egg=nyprsetuptools'
    ],
    entry_points={
        'distutils.commands': [
            'requirements = nyprsetuptools:InstallRequirements',
            'test = nyprsetuptools:PyTest',
            'test_requirements = nyprsetuptools:InstallTestRequirements',
            'deploy = nyprsetuptools:DockerDeploy',
        ],
        'distutils.setup_keywords': [
            'requirements = nyprsetuptools:setup_keywords',
            'test = nyprsetuptools:setup_keywords',
            'test_requirements = nyprsetuptools:setup_keywords',
            'deploy = nyprsetuptools:setup_keywords',
        ],
    }
```

The example above would enable the `deploy`, `requirements`, and `test_requirements`
commands and override the default test behavior for `setup.py` with a pytest implementation.

*TODO*: Version pinning is probably better than always targeting "master".

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
                                   [--test-user TEST_USER] [--fargate]
                                   [--execution-role EXECUTION_ROLE]
                                   [--no-service] [--wait WAIT]
                                   [--migrate MIGRATE]

optional arguments:
  -h, --help            show this help message and exit
  --environment ENVIRONMENT
                        Environment to deploy
  --ecs-cluster ECS_CLUSTER
                        Base name of AWS ECS target cluster
  --ecr-repository ECR_REPOSITORY
                        Base name of AWS ECR Docker repository
  --tag TAG             Docker image tag
  --memory-reservation MEMORY_RESERVATION
                        Soft memory reservation for container
  --memory-reservation-hard MEMORY_RESERVATION_HARD
                        Hard memory limit for container
  --cpu CPU             CPU resource limit for container
  --ports PORTS         Comma-delimited list of ports to expose on container
  --command COMMAND     Command override for container
  --test TEST           Command to test container after build
  --test-user TEST_USER
                        User within the container to run tests
  --fargate             Flag indicating that ECS task should run in Fargate
  --execution-role EXECUTION_ROLE
                        Required with --fargate flag
  --no-service          Flag indicating that ECS task is not a service
  --wait WAIT           Integer value in seconds to wait for new tasks to
                        start
  --migrate MIGRATE     Command to run migrations
```

### Using in CircleCI

This is an example that runs an application via Fargate, specifies additional tests,
and specifies a migration.

```yaml
    steps:
      - checkout
      - setup_remote_docker
      - run:
          name: Deploy
          command: |
            python -m venv ~/.venv
            . ~/.venv/bin/activate
            pip install  -U git+https://github.com/nypublicradio/nyprsetuptools.git
            if [[ "${CIRCLE_BRANCH}" == "demo" ]]; then
              ENV=demo
              TAG=demo
            elif echo "$CIRCLE_TAG" | grep -qE "v[0-9]+\.[0-9]+\.[0-9]+"; then
              ENV=prod
              TAG="$CIRCLE_TAG"
            else
              exit 1
            fi
            nyprsetuptools DockerDeploy --environment=$ENV \
                                        --cpu=256 \
                                        --ecr-repository=myrepo \
                                        --ecs-cluster=myrepo \
                                        --execution-role=myrepo-$ENV \
                                        --fargate \
                                        --memory-reservation=1024 \
                                        --migrate='./manage.py migrate' \
                                        --ports=80 \
                                        --tag=$TAG \
                                        --test='python setup.py test' \
                                        --wait=300
```

This is an example that runs an application on an EC2-backed ECS cluster.
This example does not run tests or migrations.

```yaml
    steps:
      - checkout
      - setup_remote_docker
      - run:
          name: Deploy
          command: |
            python -m venv ~/.venv
            . ~/.venv/bin/activate
            pip install  -U git+https://github.com/nypublicradio/nyprsetuptools.git
            if [[ "${CIRCLE_BRANCH}" == "demo" ]]; then
              ENV=demo
              TAG=demo
            elif echo "$CIRCLE_TAG" | grep -qE "v[0-9]+\.[0-9]+\.[0-9]+"; then
              ENV=prod
              TAG="$CIRCLE_TAG"
            else
              exit 1
            fi
            nyprsetuptools DockerDeploy --environment=$ENV \
                                        --ecr-repository=myrepo \
                                        --ecs-cluster=myrepo \
                                        --tag=$TAG \
                                        --wait=300
```

This is an example that deploys a new tagged image without any service changes.

```yaml
    steps:
      - checkout
      - setup_remote_docker
      - run:
          name: Deploy
          command: |
            python -m venv ~/.venv
            . ~/.venv/bin/activate
            pip install  -U git+https://github.com/nypublicradio/nyprsetuptools.git
            if [[ "${CIRCLE_BRANCH}" == "demo" ]]; then
              ENV=demo
              TAG=demo
            elif echo "$CIRCLE_TAG" | grep -qE "v[0-9]+\.[0-9]+\.[0-9]+"; then
              ENV=prod
              TAG="$CIRCLE_TAG"
            else
              exit 1
            fi
            nyprsetuptools DockerDeploy --environment=$ENV \
                                        --ecr-repository=myrepo \
                                        --ecs-cluster=myrepo \
                                        --tag=$TAG \
                                        --no-service
```
