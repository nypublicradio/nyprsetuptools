import os


def get_circle_environment_variables(environment):
    """ Returns a dictionary with environment-prefixed environment variables
        (stripped of their prefixes).
        eg. PROD_CMS_URL --> CMS_URL

        If this function is not executed on CircleCI it will return None.
    """
    if os.environ.get('CIRCLECI') == 'true':
        match_prefix = '{}_'.format(environment.upper())
        environment_variables = {
            key[len(match_prefix):]: val for key, val in os.environ.items()
            if key.startswith(match_prefix)
        }
        return environment_variables
