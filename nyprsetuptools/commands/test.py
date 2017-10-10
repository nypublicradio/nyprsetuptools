import os
import shlex
import sys
from contextlib import contextmanager
from setuptools.command.test import test as TestCommand


@contextmanager
def cov():
    """ Context manager that will collect coverage for any tests
        executed within the "with" statement. This should be used
        in cases where coverage integration is not readily available
        (eg. Django).
    """
    import coverage
    cov = coverage.Coverage()
    cov.start()
    yield
    cov.stop()
    cov.save()
    report = cov.report()
    if cov.config.fail_under >= report:
        sys.exit('Minimum code coverage {}% not met.'
                 .format(cov.config.fail_under))


class DjangoTest(TestCommand):
    """ Tests a package using the Django test runner and coverage wrapper.
        If the --django-settings argument is not provided this command
        will attempt to target the settings based on a value set in the
        manage.py file. The auto-retrieval should work if a Django manage.py
        file uses the os.environ.setdefault command to set
        DJANGO_SETTINGS_MODULE (and if the command is contained in a single
        line).

        NOTE: The tests_require parameter should still be provided to setup().
    """

    user_options = [
        ('additional-test-args=', 'a', 'Arguments to pass to test suite.'),
        ('django-settings=', 'f', 'Django settings file to load for tests.'),
    ]

    @property
    def description(self):
        return self.__doc__

    def _set_django_settings_environment(self):
        """ If the --django-settings argument is not provided this command
            will attempt to retrieve the value from the manage.py file.
            This can fail if manage.py has been modified and no longer
            contains the os.environ.setdefault command in a single line.
        """
        if self.django_settings:
            os.environ['DJANGO_SETTINGS_MODULE'] = self.django_settings
        else:
            import re
            pattern = re.compile(
                r'^os\.environ\.setdefault\(["\']DJANGO_SETTINGS_MODULE["\'], '
                r'["\'](?P<module>[^"\']+)["\']\)$'
            )
            try:
                with open('manage.py', 'r') as f:
                    for match in (pattern.match(line.strip()) for line in f):
                        if match:
                            module = match.groupdict()['module']
                            os.environ['DJANGO_SETTINGS_MODULE'] = module
                            break
                    else:
                        raise IOError
            except IOError:
                sys.exit('Must provide --django-settings argument.')

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.additional_test_args = ''
        self.django_settings = None

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        self._set_django_settings_environment()
        import django
        from django.test.utils import get_runner
        from django.conf import settings
        django.setup()

        args = shlex.split(self.additional_test_args) + self.test_args

        with cov():
            TestRunner = get_runner(settings)
            test_runner = TestRunner(verbosity=1, interactive=True)
            failures = test_runner.run_tests(args)

        if bool(failures):
            sys.exit(1)


class PyTest(TestCommand):
    """ Tests a package with pytest. If a coverage report is needed developers
        should use pytest-cov rather than the coverage wrapper here.

        NOTE: The tests_require parameter should still be provided to setup().
    """
    description = 'Tests package with pytest.'
    user_options = [
        ('additional-test-args=', 'a', 'Arguments to pass to test suite.')
    ]

    @property
    def description(self):
        return self.__doc__

    def initialize_options(self):
        TestCommand.initialize_options(self)
        self.additional_test_args = ''

    def finalize_options(self):
        TestCommand.finalize_options(self)
        self.test_args = []
        self.test_suite = True

    def run_tests(self):
        import pytest
        args = shlex.split(self.additional_test_args) + self.test_args
        exit_code = pytest.main(args)
        sys.exit(exit_code)
