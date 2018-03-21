import itertools
import os
import re
import sys
import time
from base64 import b64decode
from io import BytesIO
from setuptools import Command
from subprocess import Popen, STDOUT

from nyprsetuptools.util.environment import get_circle_environment_variables


ENVIRONMENTS = frozenset({'demo', 'prod'})


class DockerDeploy(Command):
    """ Deploys python project to AWS ECR.
        Requires the following parameters:
            --environment
            --ecs-cluster

        This command utilizes subprocess.Popen to execute Docker commands
        directly through the system's `docker` binary. A `docker` package
        is available in pypi but it should be avoided. The package often
        fails to correctly utilize Docker's cache, has trouble
        authenticating to AWS ECR, and does not provide an easy way to
        echo Docker's output to STDOUT.
    """
    user_options = [
        ('environment=', None, 'Environment to deploy'),
        ('ecs-cluster=', None, 'Base name of AWS ECS target cluster'),
        ('ecr-repository=', None, 'Base name of AWS ECR Docker repository'),
        ('tag=', None, 'Docker image tag'),
        ('memory-reservation=', None, 'Soft memory reservation for container'),
        ('memory-reservation-hard=', None, 'Hard memory limit for container'),
        ('cpu=', None, 'CPU resource limit for container'),
        ('ports=', None, 'Comma-delimited list of ports to expose on container'),
        ('command=', None, 'Command override for container'),
        ('test=', None, 'Command to test container after build'),
        ('test-user=', None, 'User within the container to run tests'),
        ('fargate', None, 'Flag indicating that ECS task should run in Fargate'),
        ('execution-role=', None, 'Required with --fargate flag'),
        ('no-service', None, 'Flag indicating that ECS task is not a service'),
        ('wait=', None, 'Integer value in seconds to wait for new tasks to start'),
        ('migrate=', None, 'Command to run migrations'),
    ]
    tag_pattern = re.compile(r'(?P<tag>v\d+\.\d+\.\d+|demo)')

    @property
    def description(self):
        return self.__doc__

    def initialize_options(self):
        self.environment = ''
        self.ecs_cluster = ''
        self.ecr_repository = ''
        self.tag = ''
        self.memory_reservation = ''
        self.memory_reservation_hard = ''
        self.cpu = ''
        self.ports = ''
        self.command = ''
        self.test = ''
        self.test_user = ''
        self.fargate = False
        self.execution_role = ''
        self.no_service = False
        self.wait = 0
        self.migrate = ''

    def finalize_options(self):
        import shlex
        # Required arguments.
        if self.environment not in ENVIRONMENTS:
            raise ValueError('--environment must be one of ({}).'
                             .format(','.join(ENVIRONMENTS)))
        tag_match = self.tag_pattern.match(self.tag)
        if not tag_match:
            raise ValueError('--tag must match expression {}'
                             .format(self.tag_pattern))
        if not self.ecs_cluster:
            raise ValueError('--ecs-cluster must be provided')
        else:
            self.ecs_cluster = '{}-{}'.format(self.ecs_cluster, self.environment)
        if not self.ecr_repository:
            raise ValueError('--ecr-repository must be provided')

        if (self.memory_reservation and self.memory_reservation_hard):
            raise ValueError('--memory-reservation and '
                             '--memory-reservation-hard are mutually exclusive')
        if (self.fargate and not (self.execution_role and self.memory_reservation and self.cpu)):
            raise ValueError('--fargate flag requires --execution-role, '
                             '--memory-reservation, and --cpu')
        self.wait = int(self.wait)

        # Optional arguments.
        if self.ports:
            self.ports = self.ports.split(',')
        if self.test:
            self.test = shlex.split(self.test)
        if self.migrate:
            self.migrate = shlex.split(self.migrate)

    @staticmethod
    def docker(*args):
        p = Popen(['docker'] + list(args), stderr=STDOUT)
        p.wait()
        if p.returncode > 0:
            raise IOError('Problem building docker container, aborting.')

    def build(self, tags=[]):
        """
        Builds the Docker image with tags  <repo>:<git_tag> and <repo>:latest.
        """
        # This scary bit of code generates all of the '-t' command line
        # flags for tagging images.
        flags = list(sum(zip(itertools.repeat('-t'), tags), ()))
        self.docker('build', *flags, os.getcwd())
        if self.test:
            test_tag = tags[0]
            test_flags = ['-u', self.test_user] if self.test_user else []
            self.docker('run', *test_flags, test_tag, *self.test)

    def push(self, registry, username, password, tags=[]):
        # Pushes the Docker image to ECR.
        self.docker('login', '-u', username, '-p', password, registry)
        for tag in tags:
            self.docker('push', tag)

    def run(self):
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            self.distribution.fetch_build_eggs(['boto3'])
            import boto3
            from botocore.exceptions import ClientError

        ecr = boto3.client('ecr')
        ecs = boto3.client('ecs')
        iam = boto3.client('iam')

        # The repository URI should be included in the tag.
        resp = ecr.describe_repositories(repositoryNames=[self.ecr_repository])
        repository_uri = resp['repositories'][0]['repositoryUri']
        registry_id = resp['repositories'][0]['registryId']
        full_tag = '{}:{}'.format(repository_uri, self.tag)
        latest_tag = '{}:latest'.format(repository_uri)

        # Builds the Docker image.
        self.build(tags=[full_tag, latest_tag])

        # Authenticates with ECR.
        resp = ecr.get_authorization_token(registryIds=[registry_id])
        auth = resp['authorizationData'][0]
        auth_token = b64decode(auth['authorizationToken']).decode()
        username, password = auth_token.split(':')
        registry = auth['proxyEndpoint']

        # Pushes the Docker image.
        self.push(registry, username, password, tags=[full_tag, latest_tag])

        # Creates the ECS task definition from an existing task definition.
        task_name = '{}-{}'.format(self.ecr_repository, self.environment)
        env_vars = get_circle_environment_variables(self.environment)

        resp = ecs.describe_task_definition(taskDefinition=task_name)
        container_defs = resp['taskDefinition']['containerDefinitions']
        if len(container_defs) > 1:
            raise NotImplementedError('This command currently only supports '
                                      'single-container tasks')
        task_def = container_defs[0]
        task_def['image'] = full_tag
        if env_vars:
            task_def['environment'] = [{'name': k, 'value': v}
                                       for k, v in env_vars.items()]
        if self.memory_reservation:
            task_def['memoryReservation'] = int(self.memory_reservation)
        elif self.memory_reservation_hard:
            task_def['memory'] = self.memory_reservation_hard
        if self.cpu:
            task_def['cpu'] = int(self.cpu)
        if self.ports:
            task_def['portMappings'] = [{'containerPort': int(p)} for p in self.ports]
        if self.command:
            task_def['command'] = self.command

        additional_args = {}
        if self.fargate:
            execution_role_arn = iam.get_role(RoleName=self.execution_role)['Role']['Arn']
            additional_args.update({
                'networkMode': 'awsvpc',
                'requiresCompatibilities': ['EC2', 'FARGATE'],
                'executionRoleArn': execution_role_arn,
                'cpu': str(self.cpu),
                'memory': str(self.memory_reservation),
            })

        # Update the ECS task definition with the newly pushed Docker image.
        print('Updating task definition {}.'.format(task_name))
        resp = ecs.register_task_definition(
            containerDefinitions=[
                task_def,
            ],
            family=task_name,
            **additional_args,
        )
        task_definition_arn = resp['taskDefinition']['taskDefinitionArn']
        revision = resp['taskDefinition']['revision']
        print('Task definition updated to revision {}.'.format(revision))

        # The ECS cluster naming convention is a little strange due to
        # the '-cluster' string appended to some clusters. This lookup
        # helps reduce the burden of determining whether the suffix is present.
        for cluster in ecs.list_clusters()['clusterArns']:
            if cluster.split('/', 1)[-1].startswith(self.ecs_cluster):
                cluster_name = cluster
                break
        else:
            raise ValueError('Cluster {} does not exist, aborting.'
                             .format(self.ecs_cluster))

        # If a migration command is provided, run the migration.
        if self.migrate:
            options = {
                'cluster': cluster_name,
                'taskDefinition': task_definition_arn,
                'overrides': {
                    'containerOverrides': [
                        {
                            'command': self.migrate,
                            'name': task_name,
                        },
                    ]
                },
                'launchType': 'EC2',
                'count': 1,
            }
            if self.fargate:
                cwl = boto3.client('logs')
                service = ecs.describe_services(
                    cluster=cluster_name,
                    services=[task_name],
                )['services'][0]
                network_config = service['networkConfiguration']
                options['launchType'] = 'FARGATE'
                options['networkConfiguration'] = network_config

                retry_delay = 5
                now = time.time()
                while (time.time() - now) < (60 * 5):
                    migration_task = ecs.run_task(**options)
                    if migration_task['tasks']:
                        break
                    time.sleep(retry_delay)
                    retry_delay = retry_delay * 1.5

                uuid = migration_task['tasks'][0]['taskArn'].split('/')[-1]
                resp = ecs.describe_task_definition(
                    taskDefinition=task_name
                )
                log_config = resp['taskDefinition']['containerDefinitions'][0]['logConfiguration']['options']
                log_group_name = log_config['awslogs-group']
                log_stream_name = '{prefix}/{family}/{uuid}'.format(
                    prefix=log_config['awslogs-stream-prefix'],
                    family=resp['taskDefinition']['family'],
                    uuid=uuid,
                )

                def read_logs(next_token=None, wait_until=None, retry_delay=5):
                    if time.time() > wait_until:
                        sys.exit('Could not find logs for migration command.')
                    options = {
                        'logGroupName': log_group_name,
                        'logStreamName': log_stream_name,
                        'startFromHead': True,
                    }
                    if next_token:
                        options['startFromHead'] = False
                        options['nextToken'] = next_token
                    try:
                        resp = cwl.get_log_events(**options)
                        for event in resp['events']:
                            print(event['message'])
                        else:
                            return
                        read_logs(resp['nextForwardToken'], wait_until=wait_until)
                    except ClientError:
                        time.sleep(retry_delay)
                        read_logs(wait_until=wait_until, retry_delay=retry_delay * 1.5)
                read_logs(wait_until=time.time() + (60 * 5))

        # If the ECS task definition has an associated service, the service
        # is updated with the latest task definition revision.
        if self.no_service is False:
            print('Updating service {} with new definition {} on {}.'
                  .format(task_name, revision, cluster_name))
            ecs.update_service(
                service=task_name,
                cluster=cluster_name,
                taskDefinition=task_definition_arn,
            )

            # When a --wait value is provided this will block
            # until the service is fully swapped or the timeout is reached.
            to_stop = to_start = None
            while ((to_stop is None and to_start is None) or
                    (self.wait > 0 and to_stop + to_start > 0)):
                start_time = time.time()
                resp = ecs.describe_services(
                    services=[task_name],
                    cluster=cluster_name
                )

                # The new task can be easily determined via the ARN
                # of the latest task definition, however this script is
                # unaware of the previous task definition ARN.
                # The key not matching the new ARN will be retrieved as 'old'.
                deployments = {d['taskDefinition']: d
                               for d in resp['services'][0]['deployments']}
                new = deployments.pop(task_definition_arn)
                if deployments:
                    old = deployments.pop(list(deployments.keys())[0])
                else:
                    old = {'runningConut': 0}

                to_stop = old['runningCount']
                to_start = new['desiredCount'] - new['runningCount']
                print('Waiting for {} old tasks to stop and {} new tasks to start '
                      '[{}s until timeout].'
                      .format(to_stop, to_start, int(self.wait)))
                time.sleep(5)
                end_time = time.time()
                self.wait = self.wait - (end_time - start_time)
                if to_stop + to_start == 0:
                    print('Deployment complete.')
                    break


class LambdaDeploy(Command):
    """ Deploys python function to AWS Lambda.
        Requires the following parameters:
            --environment
            --function-name
            --function-handler

        This command will create a zip file <function-name>-<environment>.zip
        and save the file in s3://nypr-lambda-<function-name>-<environment>.
        If the --no-s3 flag is passed the zip file will be uploaded directly
        to the Lambda instead.

        NOTE: Before executing this command the required Lambda function
        (and preferrably the target S3 bucket if used) should be created via Terraform.
    """
    user_options = [
        ('environment=', None, 'Environment to deploy'),
        ('function-name=', None, 'Base name of AWS Lambda target function'),
        ('function-handler=', None, 'Dot-delimited path to python function'),
        ('package-dir=', None, '(Optional) target directory to zip + deploy'),
        ('no-s3', None, 'Upload zip directly to Lamdba, bypassing S3'),
    ]

    @property
    def description(self):
        return self.__doc__

    def initialize_options(self):
        self.environment = ''
        self.function_name = ''
        self.function_handler = ''
        self.package_dir = None
        self.no_s3 = False

    def finalize_options(self):
        if self.environment not in ENVIRONMENTS:
            raise ValueError('--environment must be one of ({}).'
                             .format(','.join(ENVIRONMENTS)))
        elif not self.function_name:
            raise ValueError('--function-name must be provided.')
        elif not self.function_handler:
            raise ValueError('--function-handler must be provided.')

        if self.package_dir:
            self.package_dir = os.path.expanduser(self.package_dir)
            if not os.path.isdir(self.package_dir):
                raise FileNotFoundError('--package-dir not a valid directory.')

    @staticmethod
    def save_dir_to_zip(zip_file, directory):
        exclude_files = {'__pycache__'}
        for root, dirs, filenames in os.walk(directory):
            for filename in filenames:
                if filename not in exclude_files:
                    abs_path = os.path.join(root, filename)
                    rel_path = os.path.relpath(abs_path, directory)
                    zip_file.write(abs_path, rel_path)

    def run_for_venv(self):
        """
        Use this method for applications built within a virtualenvironment
        with:
            pip install -e .
        """
        from distutils.sysconfig import get_python_lib
        import zipfile
        site_packages = get_python_lib()
        cwd = os.getcwd()
        code_dir = os.path.join(cwd, self.function_handler.split('.')[0])
        file_obj = BytesIO()
        with zipfile.ZipFile(file_obj, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            self.save_dir_to_zip(zip_file, code_dir)
            self.save_dir_to_zip(zip_file, site_packages)
        file_obj.seek(0)
        return file_obj

    def run_for_package_dir(self):
        """
        Use this method for applications built in a clean directory with:
            pip install . -t /path/to/clean_dir
        """
        import zipfile
        file_obj = BytesIO()
        with zipfile.ZipFile(file_obj, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            self.save_dir_to_zip(zip_file, self.package_dir)
        file_obj.seek(0)
        return file_obj

    def run(self):
        try:
            import boto3
            from botocore.exceptions import ClientError
        except ImportError:
            self.distribution.fetch_build_eggs(['boto3'])
            import boto3
            from botocore.exceptions import ClientError

        function_name = '{0.function_name}-{0.environment}'.format(self)
        function_handler = self.function_handler

        if self.package_dir:
            file_obj = self.run_for_package_dir()
        else:
            file_obj = self.run_for_venv()

        client = boto3.client('lambda')

        if self.no_s3:
            try:
                client.update_function_code(
                    FunctionName=function_name,
                    ZipFile=file_obj.read(),
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    sys.exit('The lambda function {} needs to be created '
                             'via terraform.'.format(function_name))
                else:
                    raise
        else:
            # The zip file is uploaded to S3, the bucket is created if it does
            # not exist.
            s3 = boto3.resource('s3')
            bucket = s3.Bucket('nypr-lambda-{}'.format(function_name))
            bucket.create()
            s3_obj = bucket.Object('{}.zip'.format(function_name))
            s3_obj.upload_fileobj(file_obj)

            try:
                client.update_function_code(
                    FunctionName=function_name,
                    S3Bucket=bucket.name,
                    S3Key=s3_obj.key,
                    Publish=True
                )
            except ClientError as e:
                if e.response['Error']['Code'] == 'ResourceNotFoundException':
                    sys.exit('The lambda function {} needs to be created '
                             'via terraform.'.format(function_name))
                else:
                    raise

        # If the deploy function is not executed on CircleCI the settings
        # will not be updated.
        env = get_circle_environment_variables(self.environment, exclude_aws=True)
        if env:
            client.update_function_configuration(
                FunctionName=function_name,
                Handler=function_handler,
                Environment={
                    'Variables': env
                },
            )
