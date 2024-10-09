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

import logging
from pathlib import Path

from ruamel.yaml import YAML

import ansible_runner


class EpmonConfig:
    def __init__(self):
        self.zone = None
        self.image = None
        self.ansible_group_name = None
        self.environment = None
        self.watch_clouds = dict()

    def __repr__(self):
        return (
            "EpMon("
            f"zone: {self.zone}; "
            f"image: {self.image}; "
            f"ansible_group_name: {self.ansible_group_name}; "
            f"watch_clouds: {self.watch_clouds};"
            ")"
        )


class EpmonManager:
    log = logging.getLogger(__name__)

    def __init__(self, cloudmon_config):
        self.config = cloudmon_config
        self.epmon_configs = dict()
        self.process_config()

    def process_config(self):
        """Process config

        Process every individual matrix entry and configure
        components correspondingly
        """
        for matrix_entry in self.config.model.matrix:
            self.log.debug("Processing %s", matrix_entry)
            for plugin in matrix_entry.plugins:
                self.log.debug("Processing plugin %s", plugin)
                plugin_data = self.config.model.get_plugin_by_name(plugin.name)
                if not plugin_data:
                    self.log.warn("Plugin is not known in cloudmon_plugins")
                if plugin_data.type == "epmon":
                    # For now we only construct global apimon config matrix
                    self.process_plugin_entry(
                        plugin_data, matrix_entry, plugin
                    )
        self.log.debug(f"Epmon config: {self.epmon_configs}")

    def process_plugin_entry(self, plugin_ref, matrix_entry, plugin):
        env_name = matrix_entry.env
        zone = matrix_entry.monitoring_zone
        epmon_config = self.epmon_configs.setdefault(zone, EpmonConfig())
        epmon_config.environment = env_name
        epmon_config.zone = zone
        ansible_group_name = plugin.epmon_inventory_group_name
        epmon_config.ansible_group_name = ansible_group_name
        epmon_config.image = plugin_ref.image
        config = None

        # Read config file
        # TODO: we would most likely have same config - cache?
        yaml = YAML()
        if self.config.config_dir is not None and Path(
                        self.config.config_dir, plugin_ref.config
                        ).exists():
            with open(Path(self.config.config_dir, plugin_ref.config), "r") as f:
                config = yaml.load(f)
        elif Path(plugin_ref.config).exists():
            with open(Path(plugin_ref.config), "r") as f:
                config = yaml.load(f)
        else:
            raise RuntimeError("Epmon config not found. Please either use --config-dir and relative path for epmon config in cloudmon config OR use --insecure option with full path of epmon config in cloudmon config") # noqa


        services = dict()
        # Find requested config elements to know which services we want to
        # watch in this env
        for config_element_ref in plugin.config_elements:
            if config_element_ref in config["elements"]:
                config_element = config["elements"][config_element_ref]
                service_entry = dict()
                if len(config_element.get("urls", [])) > 0:
                    service_entry["urls"] = config_element["urls"]
                    if "sdk_proxy" in config_element:
                        service_entry["service"] = config_element["sdk_proxy"]
                services[config_element["service_type"]] = service_entry
        epmon_config.watch_clouds[env_name] = dict(
            # which services
            services=services,
            # how cloud is named
            cloud=plugin.cloud_name,
        )

    def provision(self, options):
        for _, epmon_config in self.epmon_configs.items():
            self.log.info(
                "Provisioning EpMon in monitoring zone %s",
                epmon_config.zone,
            )

            statsd_group_name = self.config.model.get_monitoring_zone_by_name(
                epmon_config.zone
            ).statsd_group_name
            statsd_servers = self.config.inventory[statsd_group_name]["hosts"]
            statsd_host_vars = self.config.hostvars(statsd_servers[0])
            # internal_address or ansible_host or hostname
            statsd_address = statsd_host_vars.get(
                "internal_address",
                statsd_host_vars.get("ansible_host", statsd_servers[0]),
            )

            epmon_cfg = dict(
                epmon=dict(
                    clouds=[
                        {k: dict(service_override=v["services"])}
                        for (k, v) in epmon_config.watch_clouds.items()
                    ],
                    socket="/tmp/epmon.socket",
                    zone=epmon_config.zone,
                ),
                log=dict(config="/etc/apimon/logging.conf"),
                metrics=dict(
                    statsd=dict(host=statsd_address, port=8125),
                ),
                secure="/etc/apimon/epmon-secure.yaml",
            )
            clouds_creds = []
            # Construct list of cloud credentials for required environments
            for env, data in epmon_config.watch_clouds.items():
                clouds_creds.append(
                    self.config.get_env_cloud_credentials(
                        env_name=env,
                        zone_name=epmon_config.zone,
                        cloud_name=data["cloud"],
                    )
                )

            epmon_secure_cfg = dict(clouds=clouds_creds)
            extravars = dict(
                epmons_group_name=epmon_config.ansible_group_name,
                epmon_image=epmon_config.image,
                epmon_config_dir="/etc/cloudmon",
                epmon_secure_config_file_name="epmon-secure.yaml",
                epmon_config=epmon_cfg,
                epmon_secure_config=epmon_secure_cfg,
            )
            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                artifact_dir=".cloudmon_artifact",
                project_dir=self.config.project_dir.as_posix(),
                playbook="install_epmon.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=3,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning EpMon")

    def stop(self, options):
        for _, epmon_config in self.epmon_configs.items():
            self.log.info(
                "Stopping EpMon in monitoring zone %s",
                epmon_config.zone,
            )
            extravars = dict(
                epmons_group_name=epmon_config.ansible_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                artifact_dir=".cloudmon_artifact",
                project_dir=self.config.project_dir.as_posix(),
                playbook="stop_epmon.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error stopping EpMon")

    def start(self, options):
        for _, epmon_config in self.epmon_configs.items():
            self.log.info(
                "Starting EpMon in monitoring zone %s",
                epmon_config.zone,
            )
            extravars = dict(
                epmons_group_name=epmon_config.ansible_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                artifact_dir=".cloudmon_artifact",
                project_dir=self.config.project_dir.as_posix(),
                playbook="start_epmon.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error startgin EpMon")
