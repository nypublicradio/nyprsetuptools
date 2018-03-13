class TestDocker:
    def _run_cmd(self, settings, **kwargs):
        import os
        from setuptools.dist import Distribution
        from nyprsetuptools.commands.deploy import DockerDeploy
        os.chdir(settings['test_dir'])
        dist = Distribution()
        cmd = DockerDeploy(dist)
        cmd.initialize_options()
        cmd.environment = settings['env']
        cmd.ecs_cluster = settings['cluster']
        cmd.ecr_repository = settings['repository']
        cmd.tag = 'demo'
        cmd.memory_reservation = '512'
        cmd.cpu = '256'
        cmd.test = '/bin/true'
        cmd.fargate = True
        cmd.execution_role = settings['execution_role']
        cmd.wait = '60'
        for key, val in kwargs.items():
            setattr(cmd, key, val)
        cmd.finalize_options()
        cmd.run()

    def test_docker_full_deploy(self, settings):
        """
        Tests a deployment to an ECS cluster using Fargate.
        This will execute the full build/test/push/update-task/update-service
        workflow.
        """
        self._run_cmd(settings)

    def test_docker_partial_deploy(self, settings):
        """
        Tests a deployment that updates the ECS image and task definition
        but does not update any services. This is useful for tasks that
        are executed on an on-demand basis or for generating intermediate
        tasks to run migrations.
        """
        self._run_cmd(settings, no_service=True, wait=0)

    def test_docker_migration_deploy(self, settings):
        """
        Tests a deployment that updates the ECS image and task definition
        but does not update any services. This is useful for tasks that
        are executed on an on-demand basis or for generating intermediate
        tasks to run migrations.
        """
        self._run_cmd(settings, no_service=True, wait=0,
                      migrate='echo "migration complete"')
