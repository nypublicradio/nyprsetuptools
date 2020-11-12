import os

def strip_prefix(variable, prefix):
    # with python 3.9, could use 'removeprefix'
    # without py3.9, this ugly snippet
    variable = variable.strip()
    return variable[len(prefix):]

def get_circle_environment_variables(environment, exclude_aws=False):
    """ Returns a dictionary with environment-prefixed environment variables
        (stripped of their prefixes).
        eg. PROD_CMS_URL --> CMS_URL

        If this function is not executed on CircleCI it will return None.
        When the exclude_aws argument is True reserved AWS variables
        will not be returned. This is useful for avoiding situations where
        providing AWS_ variables is forbidden (eg. Lambda).
    """
    aws_reserved_variables = [
        'AWS_ACCESS_KEY_ID',
        'AWS_SECRET_ACCESS_KEY',
        'AWS_DEFAULT_REGION',
    ]
    if os.environ.get('CIRCLECI') == 'true':
        match_prefix = '{}_'.format(environment.upper())
        environment_variables = {
            strip_prefix(key, match_prefix): val for key, val in os.environ.items()
            if key.startswith(match_prefix)
        }
        if exclude_aws:
            for key in aws_reserved_variables:
                try:
                    del environment_variables[key]
                except KeyError:
                    pass
        return environment_variables

def get_secrets(environment, secrets_manager):
    def arn_for_secret(secret_name):
        secret = secrets_manager.describe_secret(SecretId=secret_name)
        return secret['ARN']

    if os.environ.get('CIRCLECI') == 'true':
        task_secrets = {}
        match_prefix = '{}_'.format(environment.upper())
        try:
            with open('./SECRETS', 'r') as secrets:
                for secret in secrets:
                    if secret.startswith(match_prefix):
                        varname, secretname = secret.split(':')
                        arn = arn_for_secret(secretname.strip())
                        task_secrets[strip_prefix(varname, match_prefix)] = arn
        except FileNotFoundError:
            print("no SECRETS file found.")
        return task_secrets
