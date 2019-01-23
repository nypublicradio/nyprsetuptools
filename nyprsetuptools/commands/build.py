from setuptools import Command


MODULE_NAME = 'nyprsetuptools'


class InstallBase(Command):
    user_options = []

    @staticmethod
    def _parse_git_requirement(pkg):
        import re
        return re.sub(r'^.*#egg=(.*)(?:-\d+\.\d+\.\d+)', r'\1', pkg)

    @property
    def description(self):
        return self.__doc__

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import subprocess
        install_from_git = {
            self._parse_git_requirement(pkg): pkg
            for pkg in self.distribution.dependency_links
        }
        package_list = []
        for pkg in getattr(self.distribution, self.package_attribute):
            if pkg not in install_from_git:
                package_list.append(pkg)
            elif pkg != MODULE_NAME:
                package_list.append(install_from_git[pkg])
        p = subprocess.Popen(['pip', 'install'] + package_list)
        p.communicate()


class InstallRequirements(InstallBase):
    """
    Installs package dependencies as if they were installed
    using `pip install -r requirements.txt`. This is useful for
    caching third-party packages in a Docker layer (preserving the cached
    layer until setup.py is modified with a new requirement).
    """
    package_attribute = 'install_requires'


class InstallTestRequirements(InstallBase):
    """
    Installs package test dependencies as if they were installed
    using `pip install -r test_requirements.txt`. This is useful for
    exposing test packages directly to developers (to allow `pytest` to be
    executed directly, for example).
    """
    package_attribute = 'tests_require'
