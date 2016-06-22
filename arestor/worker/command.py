"""The commands used by the client actions."""

import os
import re

from neutronclient.v2_0 import client as neutron_client

from arestor import resources as arestor_resources
from arestor.worker import base as worker_base


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

    def __init__(self, executor):
        super(InstallTempest, self).__init__(executor=executor)
        self._template = os.path.abspath(arestor_resources.__path__[0])
        self._config = os.path.join(self._venv, "etc", "tempest.conf")
        self._replace = {}
        self._neutron = None
        self._glance = None

    @property
    def neutron(self):
        """Expose the neutron client."""
        if not self._neutron:
            self._neutron = neutron_client.Client(
                username=os.environ.get("OS_USERNAME"),
                password=os.environ.get("OS_PASSWORD"),
                tenant_name=os.environ.get("OS_TENANT_NAME"),
                auth_url=os.environ.get("OS_AUTH_URL")
            )
        return self._neutron

    @property
    def config(self):
        """Expose the tempest config."""
        if not self._config:
            argus_image = self._get_image_id()
            self._config = {
                "flavor_ref_alt": "m1.large",
                "image_ref_alt": argus_image,
                "flavor_ref": "m1.large",
                "image_ref": argus_image,
                "admin_tenant_id": self._get_tenant_id(),
                "admin_tenant_name": os.environ.get("OS_TENANT_NAME"),
                "admin_password": os.environ.get("OS_PASSWORD"),
                "admin_username": os.environ.get("OS_USERNAME"),
                "default_network": self._get_default_network(),
                "public_router_id": self._get_router_id(),
                "public_network_id": self._get_network_id(),
            }
        return self._config

    def _get_default_network(self):
        """Return the CIDR of the public network."""
        public_id = self._get_network_id(name="public")
        network = self.neutron.show_network(public_id).get("network")
        for subnet_id in network.get("subnets"):
            subnet = self.neutron.show_subnet(subnet_id).get("subnet")
            if "cidr" in subnet:
                return subnet["cidr"]

    def _get_image_id(self, pattern="argus.*"):
        """Return the image identifier for the first image that
        matches the received pattern."""
        regexp = re.compile(pattern)
        raw_data, _ = self._execute(["glance", "image-list"])
        for line in raw_data.splitlines():
            try:
                image_id, image_name = line.strip(" -+|").split('|')
            except ValueError:
                pass

            if regexp.match(image_name):
                return image_id.strip()

    def _get_tenant_id(self):
        """Return the tenant id for the current user."""
        auth_info = self.neutron.get_auth_info()
        return auth_info.get("auth_tenant_id")

    def _get_network_id(self, name="public"):
        """Get the identifier for the received network name."""
        networks = self.neutron.list_networks()
        for network in networks.get("networks", []):
            if network["name"] == name:
                return network["id"]

    def _get_router_id(self, name="router1"):
        """Get the identifier for the received router name."""
        routers = self.neutron.list_routers()
        for router in routers.get("routers", []):
            if router["name"] == name:
                return router["id"]

    def _write_config(self):
        """Create the Tempest config file."""
        config = []
        with open(self._template, "r") as template:
            for line in template.readlines():
                key, sep, value = line.partition("=")
                if sep == "=":
                    value = self.config.get(key, value)
                    config.append("%s = %s" % (key, value))
                else:
                    config.append(line)

        with open(self._config, "w") as config_file:
            config_file.write("\n".join(config))

    def _work(self):
        """Install the tempest package and its requirements."""
        self._execute(["sudo", "-u", self.args["user"], self._pip,
                       "install", self.REPO % self.args["tempest_branch"]])

    def _epilogue(self):
        """Executed once after the command running."""
        self._execute(["sudo", "-u", self.args["user"], self._python,
                       "-c", "import tempest"])
        self._write_config()
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
