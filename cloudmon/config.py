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


primitive_types = (int, str, bool, float)
str_types = str
list_types = (list, tuple)


class CloudMonConfig:
    log = logging.getLogger(__name__)

    def __init__(self):
        self.config = None
        self.config_dir = None
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

    def __repr__(self):
        return (
            f"CloudMonConfig(config={self.config}, "
            f"config_dir={self.config_dir}, "
            f"inventory={self.inventory}, "
            f"inventory_path={self.inventory_path}, "
            f"apimon_configs={self.apimon_configs}, "
            f"private_data_dir={self.private_data_dir}, "
            f"project_dir={self.project_dir}, "
            f"kustomize_dir={self.kustomize_dir}, "
            f"default_extravars={self.default_extravars}, "
            f"is_updated={self.is_updated})"
        )

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
            cloud_creds = self.model.get_cloud_creds_by_name(c_ref).model_dump(
                exclude_none=True
            )
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

    def parse(
        self, fname: str, config_dir: Path = ".", config_dir2: Path = None
    ):
        """Parse config

        :param str fname: Config file name
        :param Path config_dir: first directory with config file (values take
            priority)
        :param Path config_dir: optional supplementary directory content from
            which will be merged with the one from config_dir
        """
        xyaml = YAML()
        source = dict()

        with open(Path(config_dir, fname), "r") as f:
            source = yaml.safe_load(f)
            self.config = xyaml.load(f)

        if config_dir2 and config_dir2.exists():
            with open(Path(config_dir2, fname), "r") as f:
                supp_source = yaml.safe_load(f)
                source = self._deepmerge(supp_source, source)

        self.model = ConfigModel(**source)

    def parse_insecure(
        self, fname: Path,
    ):
        """Parse config

        :param str fname: Config file path
        """
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

    def _deepmerge(self, a, b):
        """Merge two objects"""
        if a is None or isinstance(b, primitive_types):
            a = b
        elif isinstance(a, list_types):
            if isinstance(b, list_types):
                a.extend(
                    bitem
                    for bitem in b
                    if bitem not in a
                    and (
                        isinstance(bitem, primitive_types)
                        or isinstance(bitem, list_types)
                    )
                )
                srcdicts = {}
                for bitem in b:
                    # convert b side list to dict by "name"
                    if isinstance(bitem, dict) and "name" in bitem:
                        srcdicts.update({bitem["name"]: bitem})
                for k, aitem in enumerate(a):
                    if isinstance(aitem, dict):
                        if "name" in aitem and aitem["name"] in srcdicts:
                            # we merge only if name in dict is matching
                            a[k] = self._deepmerge(
                                aitem, srcdicts[aitem["name"]]
                            )
                            del srcdicts[aitem["name"]]
                for k, v in srcdicts.items():
                    a.append(v)
            else:
                raise ValueError(
                    "can not merge %s with %s"
                    % (
                        a,
                        b,
                    )
                )
        elif isinstance(a, dict):
            if isinstance(b, dict):
                for k in b:
                    if k in a:
                        a[k] = self._deepmerge(a[k], b[k])
                    else:
                        a[k] = b[k]
            elif isinstance(b, list_types):
                for bd in b:
                    if isinstance(bd, dict):
                        a = self._deepmerge(a, bd)
                    else:
                        raise ValueError(
                            "can not merge element from list %s with %s"
                            % (
                                a,
                                b,
                            )
                        )
            else:
                raise ValueError(
                    "can not merge %s with %s"
                    % (
                        a,
                        b,
                    )
                )
        return a
