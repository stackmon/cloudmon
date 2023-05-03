# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import importlib.resources
import logging
from pathlib import Path
import tempfile
import yaml

import ansible_runner
from ruamel.yaml import YAML

from cloudmon.types import ConfigModel


class CloudMonConfig:
    log = logging.getLogger(__name__)

    def __init__(self):
        self.config = None
        self.inventory = None
        self.inventory_path = None
        self.apimon_configs = dict()
        self.private_data_dir = None
        self.project_dir = Path(
            importlib.resources.files("cloudmon"), "ansible", "project"
        )
        self.kustomize_dir = Path(
            importlib.resources.files("cloudmon"), "kustomize"
        )

        self.default_extravars = dict(
            distro_lookup_path=[
                (
                    "{{ ansible_facts.distribution }}"
                    ".{{ ansible_facts.lsb.codename|default() }}"
                    ".{{ ansible_facts.architecture }}.yaml"
                ),
                (
                    "{{ ansible_facts.distribution }}"
                    ".{{ ansible_facts.lsb.codename|default() }}.yaml"
                ),
                (
                    "{{ ansible_facts.distribution }}"
                    ".{{ ansible_facts.architecture }}.yaml"
                ),
                "{{ ansible_facts.distribution }}.yaml",
                "{{ ansible_facts.os_family }}.yaml",
                "default.yaml",
            ]
        )
        self.is_updated = False

        self.private_data_dir = Path(tempfile.mkdtemp(prefix="cloudmon"))

    def hostvars(self, host=None):
        hostvars = self.inventory["_meta"]["hostvars"]
        if host:
            return hostvars[host]
        else:
            return hostvars

    def get_statsd_zone_address(self, zone):
        statsd_group_name = self.model.get_monitoring_zone_by_name(
            zone
        ).statsd_group_name
        statsd_servers = self.inventory[statsd_group_name]["hosts"]
        statsd_host_vars = self.hostvars(statsd_servers[0])
        # internal_address or ansible_host or hostname
        statsd_address = statsd_host_vars.get(
            "internal_address",
            statsd_host_vars.get("ansible_host", statsd_servers[0]),
        )

        return statsd_address

    def get_graphite_zone_address(self, zone):
        graphite_group_name = self.model.get_monitoring_zone_by_name(
            zone
        ).graphite_group_name
        graphite_servers = self.inventory[graphite_group_name]["hosts"]
        graphite_host_vars = self.hostvars(graphite_servers[0])
        # internal_address or ansible_host or hostname
        graphite_address = graphite_host_vars.get(
            "internal_address",
            graphite_host_vars.get("ansible_host", graphite_servers[0]),
        )

        return graphite_address

    def get_env_clouds_credentials(
        self,
        env_name,
        zone_name,
    ):
        env = self.model.get_env_by_name(env_name)
        zone = env.get_zone_by_name(zone_name)
        res = dict()
        for cloud in zone.clouds:
            c_name = cloud.name
            c_ref = cloud.ref
            cloud_creds = self.model.get_cloud_creds_by_name(c_ref).dict()
            # We do not need name on that level - it is anyway not what we
            # would expect
            cloud_creds.pop("name")
            res[c_name] = dict(name=c_name, data=cloud_creds)

        return res

    def get_env_cloud_credentials(self, env_name, zone_name, cloud_name):
        data = self.get_env_clouds_credentials(env_name, zone_name)
        if cloud_name not in data:
            raise RuntimeError(
                "Cloud with name %s for environment %s in zone %s is not found"
                % (cloud_name, env_name, zone_name)
            )
        return data.get(cloud_name)

    def parse(self, fname):
        xyaml = YAML()
        source = dict()
        with open(fname, "r") as f:
            source = yaml.safe_load(f)
            self.config = xyaml.load(f)

        self.model = ConfigModel(**source)

    def process_inventory(self, inventory_path: Path):
        self.log.debug("Processing inventory file %s" % inventory_path)
        out, err = ansible_runner.get_inventory(
            action="list",
            inventories=[inventory_path.as_posix()],
            response_format="json",
            process_isolation=False,
            quiet=True,
        )
        self.inventory = out
        self.inventory_path = inventory_path.as_posix()
