"""The commands used by the client actions."""

import os

from argusvm.worker import base as worker_base


class SetupEnvironment(worker_base.Command):

    """Command used for installing the global requirements."""

    def _work(self):
        """Install dependences for Argus-Ci."""
        self._execute(["sudo", "apt-get", "install", "-y", "build-essential",
                       "git", "python-dev", "libffi-dev", "libssl-dev"])
        self._execute(["sudo", "apt-get", "install", "-y", "python-pip"])
        self._execute(["sudo", "pip", "install", "virtualenv"])


class CreateEnvironment(worker_base.Command):

    """Command used for creating virtual environment for Argus-CI."""

    def _work(self):
        """Create the virtual environment for Argus-Ci and Tempest."""
        if not self._setup_venv:
            return

        if os.path.isdir(self._venv):
            self.logger.warning("The virtual environment already exists. %s",
                                self._venv)
        else:
            self._execute(["sudo", "-u", self.args["user"], "virtualenv",
                           self._venv, "--python", "/usr/bin/python2.7"])

    def _epilogue(self):
        """Executed once after the command running."""
        if self._setup_venv:
            self._execute(["sudo", "-u", self.args["user"],
                           self._pip, "install", "pip", "--upgrade"])


class InstallTempest(worker_base.Command):

    """Command used for installing tempest and its requirements."""

    REPO = 'git+https://github.com/openstack/tempest.git@%s'

    def _work(self):
        """Install the tempest package and its requirements."""
        self._execute(["sudo", "-u", self.args["user"], self._pip,
                       "install", self.REPO % self.args["tempest_branch"]])

    def _epilogue(self):
        """Executed once after the command running."""
        self._execute(["sudo", "-u", self.args["user"], self._python,
                       "-c", "import tempest"])
        # TODO(alexandrucoman): Create the config file

        super(InstallTempest, self)._epilogue()


class InstallArgusCi(worker_base.Command):

    """Command used for installing argus-ci and its requirements."""

    REPO = 'git+https://github.com/cloudbase/cloudbase-init-ci@%s'

    def __init__(self, executor):
        super(InstallArgusCi, self).__init__(executor=executor)

    def _work(self):
        """Install the argus-ci framework and its requirements."""
        self._execute(["sudo", "-u", self.args["user"], self._pip,
                       "install", self.REPO % self.args["argus_branch"]])

    def _epilogue(self):
        """Executed once after the command running."""
        self._execute(["sudo", "-u", self.args["user"], self._python,
                       "-c", "import argus"])
        # TODO(alexandrucoman): Create the config file
        super(InstallArgusCi, self)._epilogue()
