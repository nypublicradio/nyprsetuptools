import os
import shlex
import sys
from collections import defaultdict
from contextlib import contextmanager
from operator import itemgetter
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


class PyTestParallelCollector:
    """ Private class that iterates over each pytest file collected
        and determines if it has been marked with the 'slow' marker.
        Yields the collected items one-by-one with the 'slow' items
        in sequence. If the 'time' kwarg was provided to the 'slow' marker
        the items will be returned from longest to shortest (defaulting to 0
        in cases where a test is marked 'slow' but time is not provided).
    """
    def __init__(self):
        self.tests = {
            'slow': defaultdict(int),
            'fast': set(),
        }

    def gather(self, node_total, node_index):
        nodes = {n: {'time': 0, 'tests': [], 'index': n} for n in range(node_total)}

        # The longest running tests are moved to the start of the list.
        # When tests are marked with the same duration the filename will
        # be used as an alternative sort key (to ensure the same order is
        # returned for each node this test command is executed on).
        sorted_slow = sorted(self.tests['slow'].items(),
                             key=itemgetter(1, 0), reverse=True)
        sorted_fast = sorted(test_file for test_file in self.tests['fast']
                             if test_file not in self.tests['slow'])

        # Tests are balanced between nodes, granting tests to the
        # least-busy test node and falling back to a round-robin approach
        # when nodes have equal test distribution or an estimated
        # test time is not provided to the pytest marker.
        for i, (test_file, time_) in enumerate(sorted_slow):
            node = i % node_total
            min_node = min(nodes.values(), key=itemgetter('time'))
            if time_ and (min_node['time'] < nodes[node]['time']):
                index = min_node['index']
            else:
                index = node
            nodes[index]['time'] += time_
            nodes[index]['tests'].append(test_file)

        # The 'fast' tests are distributed evenly among nodes.
        for i, test_file in enumerate(sorted_fast):
            node = i % node_total
            nodes[node]['tests'].append(test_file)

        for test_file in nodes[node_index]['tests']:
            yield test_file

    def pytest_collection_modifyitems(self, items):
        for item in items:
            test_file = item.nodeid.split(':', 1)[0]
            if test_file.endswith('__init__.py') or not test_file.endswith('.py'):
                continue
            marker = item.get_marker('slow')
            if marker:
                self.tests['slow'][test_file] = marker.kwargs.get('time', 0)
            else:
                self.tests['fast'].add(test_file)


class PyTestDistributed(PyTest):
    """ Tests a package with pytest. If running on CircleCI test will be
        distributed between available test nodes based on the arguments
        provided. Slow tests (marked with pytest.mark.slow) will be split
        among available nodes first.

        NOTE: Coverage reports rely on the ability for Circle to create buckets
              in the format test-nypr-...
    """

    user_options = [
        ('additional-test-args=', 'a', 'Arguments to pass to test suite.'),
        ('circle-node-index=', None, 'The index of the container.'),
        ('circle-node-total=', None, 'The total number of test containers.'),
        ('circle-s3-cache=', None, 'The bucket used to share files.'),
        ('circle-test-reports=', None, 'Directory to save test_reports [Default: ~/test_reports]'),
        ('circle-artifacts=', None, 'The bucket used to share files [Default: ~/artifacts].'),
    ]

    def initialize_options(self):
        PyTest.initialize_options(self)
        self.circle_node_index = 0
        self.circle_node_total = 1
        self.circle_s3_cache = ''
        self.circle_args = []

        home = os.path.expanduser('~')
        self.circle_test_reports = os.path.join(home, 'test_reports')
        self.circle_artifacts = os.path.join(home, 'artifacts')

    def finalize_options(self):
        PyTest.finalize_options(self)
        self.circle_ci = os.environ.get('CIRCLECI') == 'true'
        self.circle_sha1 = os.environ.get('CIRCLE_SHA1')
        self.circle_node_total = int(self.circle_node_total)
        self.circle_node_index = int(self.circle_node_index)

    def _collect_coverage(self):
        """Running tests on multiple Circle nodes requires coverage
        reports to be combined at the end of the testing period.
        Containers do not share data so each report must be uploaded
        to s3, downloaded, and then combined by the last-to-finish
        node.
        """
        import os
        import boto3
        s3 = boto3.resource('s3')
        bucket = s3.create_bucket(Bucket=self.circle_s3_cache)
        coverage_key_prefix = 'cov_{}'.format(self.circle_sha1)
        coverage_key_file = '.coverage.{}'.format(self.circle_node_index)
        coverage_key = '/'.join((coverage_key_prefix, coverage_key_file))
        bucket.upload_file('.coverage', coverage_key)
        coverage_reports = list(bucket.objects.filter(Prefix=coverage_key_prefix))
        if len(coverage_reports) == self.circle_node_total:
            cov_combine_dir = '.cov-combine'
            os.mkdir(cov_combine_dir)
            for coverage_report in coverage_reports:
                filename = os.path.join(
                    cov_combine_dir,
                    os.path.basename(coverage_report.key)
                )
                s3_obj = coverage_report.Object()
                s3_obj.download_file(filename)
                s3_obj.delete()

    def run_tests(self):
        import shlex
        import sys
        import pytest
        if self.circle_ci:
            self.circle_s3_cache = (self.circle_s3_cache or
                                    'test-nypr-{CIRCLE_PROJECT_REPONAME}-cache'
                                    .format(**os.environ))

            # CircleCI collects test artifacts for readable test reports.
            os.makedirs(self.circle_test_reports, exist_ok=True)
            self.circle_args.append(
                '--junitxml={0.circle_test_reports}/node_{0.circle_node_index}.xml'
                .format(self)
            )

            # When running tests on a single Circle node
            # no coverage aggregation is required.
            os.makedirs(self.circle_artifacts, exist_ok=True)
            if self.circle_node_total == 1:
                self.circle_args.append(
                    '--cov-report=html:{0.circle_artifacts}/coverage.html'
                    .format(self)
                )
            # A custom collector groups slow-running tests to ensure
            # they are distributed between available nodes.
            collector = PyTestParallelCollector()
            pytest.main([
                '--collect-only',
                '-p', 'no:terminal',
                '-p', 'no:sugar'
            ], plugins=[collector])
            for test in collector.gather(self.circle_node_total, self.circle_node_index):
                self.circle_args.append(test)
        args = shlex.split(self.additional_test_args) + self.circle_args
        print('running pytest with args: {}'.format(args))
        exit_code = pytest.main(args)
        # This is wrapped in a catch-all try/except block
        # because a bug in collecting coverage is not worth
        # producing a failure on 20+ minutes of testing.
        if self.circle_ci and self.circle_node_total > 1:
            try:
                self._collect_coverage()
            except Exception as e:
                print('There was a problem collecting the coverage report.')
                print(e)
        sys.exit(exit_code)
