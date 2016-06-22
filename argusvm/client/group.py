"""The commands used by the command line parser."""

import os

from argusvm.client import base as client_base
from argusvm.worker import command


class InstallArgusCiDependences(client_base.Command):

    """Install the Argus-CI dependences on the current machine."""

    def setup(self):
        """Extend the parser configuration in order to expose all
        the received commands.
        """
        parser = self._parser.add_parser(
            "dependences",
            help="Install the Argus-CI dependences on the current machine.")

        parser.set_defaults(work=self.run)

    def _work(self):
        """Install the Argus-CI on the current machine."""

        # Create the virtual environment for Argus-Ci
        task = command.SetupEnvironment(self)
        return task.run()


class InstallArgusCi(client_base.Command):

    """Install the Argus-CI on the current machine."""

    def __init__(self, parent, parser):
        super(InstallArgusCi, self).__init__(parent, parser)
        self.__status = True

    def setup(self):
        """Extend the parser configuration in order to expose all
        the received commands.
        """
        parser = self._parser.add_parser(
            "argus",
            help="Install the Argus-CI on the current machine.")

        parser.add_argument("--user", dest="user", default="root",
                            help="Run the commands as specified user.")

        parser.add_argument(
            "--argus-branch", dest="argus_branch",
            default=os.environ.get("ARGUS_BRANCH", "master"),
            help="the required branch / revision of argus repository "
                 "(Default: master)")
        parser.add_argument(
            "--tempest-branch", dest="tempest_branch",
            default=os.environ.get("TEMPEST_BRANCH", "tags/7"),
            help="the required branch / revision of argus repository "
                 "(Default: tags/7)")
        parser.add_argument(
            "--build", dest="build", type=str, required=True,
            help="The unique identifier for the current job."
        )

        parser.set_defaults(work=self.run)

    def on_task_fail(self, task, exc):
        """Callback for task fail."""
        self.__status = False
        self.logger.error("Task %s failed: %s", task.name, exc)

    def _work(self):
        """Install the Argus-CI on the current machine."""
        tasks = (
            # Create the virtual environment for Argus-Ci
            command.CreateEnvironment,
            # Install Tempest and its requirements
            command.InstallTempest,
            # Install Arugs-Ci and its requirements
            command.InstallArgusCi
        )

        for task in tasks:
            if not self.__status:
                break
            task(self).run()

        return self.__status


class InstallGroup(client_base.Group):

    """Group for all install commands."""

    commands = [
        (InstallArgusCi, "install"),
        (InstallArgusCiDependences, "install"),
    ]

    def setup(self):
        """Extend the parser configuration in order to expose all
        the received commands.
        """
        parser = self._parser.add_parser(
            "install",
            help="Install Argus-CI resources on the current machine.")

        install_action = parser.add_subparsers()
        self._register_parser("install", install_action)
