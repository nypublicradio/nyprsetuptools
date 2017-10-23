from setuptools import Command


class InstallRequirements(Command):
    """ Installs package dependencies as if they were installed
        using `pip install -r requirements.txt`. This is useful for
        caching third-party packages in a Docker layer (preserving the cached
        layer until setup.py is modified with a new requirement).
    """

    user_options = []

    @property
    def description(self):
        return self.__doc__

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pip
        install_from_git = [pkg.split('=')[:len('#egg=')] for pkg
                            in self.distribution.dependency_links]
        install_from_pypi = [pkg for pkg in self.distribution.install_requires
                             if pkg not in install_from_git]
        pip.main(['install'] + self.distribution.dependency_links +
                 install_from_pypi)


class InstallTestRequirements(Command):
    """ Installs package test dependencies as if they were installed
        using `pip install -r test_requirements.txt`. This is useful for
        exposing test packages directly to developers (to allow `pytest` to be
        executed directly, for example).
    """

    user_options = []

    @property
    def description(self):
        return self.__doc__

    def initialize_options(self):
        pass

    def finalize_options(self):
        pass

    def run(self):
        import pip
        install_from_git = [pkg.split('=')[:len('#egg=')] for pkg
                            in self.distribution.dependency_links]
        install_from_pypi = [pkg for pkg in self.distribution.tests_require
                             if pkg not in install_from_git]
        pip.main(['install'] + self.distribution.dependency_links +
                 install_from_pypi)
