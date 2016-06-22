"""
Worker base-classes:
    (Beginning of) the contract that workers and commands must follow.
"""
from __future__ import print_function

import abc
import os
import sys
import subprocess
import platform
import time

import six


def do_nothing():
    """Do nothing"""
    pass


@six.add_metaclass(abc.ABCMeta)
class Worker(object):

    """Contract class for all the commands and clients."""

    def _prologue(self):
        """Executed once before the command running."""
        pass

    @abc.abstractmethod
    def _work(self):
        """Override this with your desired procedures."""
        pass

    def _epilogue(self):
        """Executed once after the command running."""
        pass

    def run(self):
        """Run the command."""
        result = None
        self._prologue()
        result = self._work()
        self._epilogue()
        return result


@six.add_metaclass(abc.ABCMeta)
class Command(Worker):

    """Contract class for all the commands."""

    ROUTES = {
        "linux2": {"default": ""},
        "win32": {"default": "_win"},
    }

    def __init__(self, executor):
        super(Command, self).__init__()

        self._executor = executor

        self._attemts = self._executor.args.get('attempts', 1)
        self._retry_interval = self._executor.args.get('retry_interval', 0)
        self._setup_venv = self._executor.args.get("setup_venv")
        self._venv = os.path.join("/tmp/argus-env",
                                  self._executor.args.get("build"))

        if self._setup_venv:
            self._python = os.path.join(self._venv, "bin", "python")
            self._pip = os.path.join(self._venv, "bin", "pip")
        else:
            self._python = "/usr/bin/python"
            self._pip = "/usr/local/bin/pip"

    @property
    def args(self):
        """Expose the args object."""
        return self._executor.args

    @property
    def logger(self):
        """Expose the logger object."""
        return self._executor.logger

    @property
    def name(self):
        """Return the name of the task."""
        return self.__class__.__name__

    def _execute(self, command, **kwargs):
        """Helper method to shell out and execute a command through subprocess.

        :param attempts:        How many times to retry running the command.
        :param binary:          On Python 3, return stdout and stderr as bytes
                                if binary is True, as Unicode otherwise.
        :param check_exit_code: Single bool, int, or list of allowed exit
                                codes.  Defaults to [0].  Raise
                                :class:`CalledProcessError` unless
                                program exits with one of these code.
        :param command:         The command passed to the subprocess.Popen.
        :param cwd:             Set the current working directory
        :param env_variables:   Environment variables and their values that
                                will be set for the process.
        :param retry_interval:  Interval between execute attempts, in seconds
        :param shell:           whether or not there should be a shell used to
                                execute this command.

        :param admin:           run command as superuser

        :raises:                :class:`subprocess.CalledProcessError`
        """
        # pylint: disable=too-many-locals

        attempts = kwargs.pop("attempts", self._attemts)
        binary = kwargs.pop('binary', False)
        check_exit_code = kwargs.pop('check_exit_code', [0])
        cwd = kwargs.pop('cwd', None)
        env_variables = kwargs.pop("env_variables", None)
        retry_interval = kwargs.pop("retry_interval", self._retry_interval)
        shell = kwargs.pop("shell", False)
        command = [str(argument) for argument in command]

        if cwd and not os.path.isdir(cwd):
            self.logger.warning("Invalid value for cwd: %s", cwd)
            cwd = None

        ignore_exit_code = False
        if isinstance(check_exit_code, bool):
            ignore_exit_code = not check_exit_code
            check_exit_code = [0]
        elif isinstance(check_exit_code, int):
            check_exit_code = [check_exit_code]

        for attempt in range(attempts):
            self.logger.debug("Execute command: %r (attempt %d)",
                              command, attempt + 1)
            try:
                process = subprocess.Popen(command,
                                           stdin=subprocess.PIPE,
                                           stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, shell=shell,
                                           cwd=cwd, env=env_variables)
                result = process.communicate()
                return_code = process.returncode
                self.logger.debug("%r (return code %s)", command, return_code)

                if six.PY3 and not binary and result is not None:
                    # pylint: disable=no-member

                    # Decode from the locale using using the surrogate escape
                    # error handler (decoding cannot fail)
                    (stdout, stderr) = result
                    stdout = os.fsdecode(stdout)
                    stderr = os.fsdecode(stderr)
                else:
                    stdout, stderr = result

                if not ignore_exit_code and return_code not in check_exit_code:
                    raise subprocess.CalledProcessError(
                        returncode=return_code, cmd=command,
                        output=(stdout, stderr))
                else:
                    return (stdout, stderr)
            except subprocess.CalledProcessError:
                if attempt == attempts - 1:
                    raise
                time.sleep(retry_interval)

    def _done(self, result):
        """What to execute after successfully finished processing a task."""
        callback = getattr(self._executor, "on_task_done", None)
        if callback:
            callback(self, result)
        else:
            self.logger.debug("%r: No callback found for task_done in %r",
                              self.name, self._executor.name)

    def _fail(self, exc):
        """What to do when the program fails processing a task."""
        callback = getattr(self._executor, "on_task_fail", None)
        if callback:
            callback(self, exc)
        else:
            self.logger.debug("%r: No callback found for task_fail in %r",
                              self.name, self._executor.name)

    def run(self):
        """Run the command."""
        result = None
        distributions = self.ROUTES.get(sys.platform, {})
        prefix = distributions.get(platform.dist(), "")

        prologue = getattr(self, "_prologue%s" % prefix, do_nothing)
        work = getattr(self, "_work%s" % prefix, do_nothing)
        epilogue = getattr(self, "_epilogue%s" % prefix, do_nothing)

        if work is do_nothing:
            self.logger.warning("%s not available on %r - %r", self.name,
                                sys.platform, platform.dist())
            return

        try:
            prologue()
            result = work()
            epilogue()
        except Exception as exc:
            self._fail(exc)
        else:
            self._done(result)
        return result

    def _prologue(self):
        """Executed once before the command running."""
        self.logger.debug("%r in prologue section", self.name)

    @abc.abstractmethod
    def _work(self):
        """Override this with your desired procedures."""
        pass

    def _epilogue(self):
        """Executed once after the command running."""
        self.logger.debug("%r in epilogue section.", self.name)
