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


class GlobalmonConfig:
    def __init__(self):
        self.zone = None
        self.image = None
        self.ansible_group_name = None
        self.environment = None
        self.watch_clouds = dict()
        self.services = dict()

    def __repr__(self):
        return (
            "Globalmon("
            f"zone: {self.zone}; "
            f"image: {self.image}; "
            f"ansible_group_name: {self.ansible_group_name}; "
            f"watch_clouds: {self.watch_clouds};"
            ")"
        )


class GlobalmonManager:
    log = logging.getLogger(__name__)

    def __init__(self, cloudmon_config):
        self.config = cloudmon_config
        self.globalmon_configs = dict()
        self.process_config()

    def process_config(self):
        # Process every plugin entry in config matrix
        for matrix_entry in self.config.model.matrix:
            self.log.debug("Processing %s", matrix_entry)
            for plugin in matrix_entry.plugins:
                self.log.debug("Processing plugin %s", plugin)
                plugin_data = self.config.model.get_plugin_by_name(plugin.name)
                if not plugin_data:
                    self.log.warn("Plugin is not known in cloudmon_plugins")
                if plugin_data.type == "globalmon":
                    # For now we only construct global globalmon config matrix
                    self.process_plugin_entry(
                        plugin_data, matrix_entry, plugin
                    )

    def process_plugin_entry(self, plugin_ref, matrix_entry, plugin):
        env_name = matrix_entry.env
        zone = matrix_entry.monitoring_zone
        globalmon_config = self.globalmon_configs.setdefault(
            zone, GlobalmonConfig())
        globalmon_config.environment = env_name
        globalmon_config.zone = zone
        ansible_group_name = plugin.globalmons_inventory_group_name
        globalmon_config.ansible_group_name = ansible_group_name
        globalmon_config.image = plugin_ref.image
        config = None

        # Read config file
        # TODO: we would most likely have same config - cache?
        yaml = YAML()
        with open(Path(plugin_ref.config), "r") as f:
            config = yaml.load(f)

        globalmon_config.services = config["services"]

        globalmon_config.watch_clouds[env_name] = dict(
            # which services
            services=globalmon_config.services,
            # how cloud is named
            cloud=plugin.cloud_name,
        )

    def provision(self, options):

        for _, globalmon_config in self.globalmon_configs.items():
            self.log.info(
                "Provisioning Globalmon in monitoring zone %s",
                globalmon_config.zone,
            )

            statsd_group_name = self.config.model.get_monitoring_zone_by_name(
                globalmon_config.zone
            ).statsd_group_name
            statsd_servers = self.config.inventory[statsd_group_name]["hosts"]
            statsd_host_vars = self.config.hostvars(statsd_servers[0])
            # internal_address or ansible_host or hostname
            statsd_address = statsd_host_vars.get(
                "internal_address",
                statsd_host_vars.get("ansible_host", statsd_servers[0]),
            )

            # FOR MORE DETAILED CONFIG FILE USE THIS.

            # globalmon_cfg = dict(
            #     globalmon=dict(
            #         clouds=[
            #             {k: dict(services=v["services"])}
            #             for (k, v) in globalmon_config.watch_clouds.items()
            #         ],
            #         socket="/tmp/globalmon.socket",
            #         zone=globalmon_config.zone,
            #     ),
            #     # log=dict(config="/etc/globalmon/logging.conf"),
            #     metrics=dict(
            #         statsd=dict(host=statsd_address, port=8125),
            #     ),
            #     secure="/etc/globalmon/globalmon-secure.yaml",
            # )

            environment = globalmon_config.environment
            zone = globalmon_config.zone
            globalmon_cfg = dict(
                services=globalmon_config.services,
                statsd=dict(
                    host=statsd_address,
                    port=8125,
                    path=f"globalmon.{environment}.{zone}"))

            clouds_creds = []
            # Construct list of cloud credentials for required environments
            for env, data in globalmon_config.watch_clouds.items():
                clouds_creds.append(
                    self.config.get_env_cloud_credentials(
                        env_name=env,
                        zone_name=globalmon_config.zone,
                        cloud_name=data["cloud"],
                    )
                )

            globalmon_secure_cfg = dict(clouds=clouds_creds)

            extravars = dict(
                globalmon_group_name=globalmon_config.ansible_group_name,
                globalmon_image=globalmon_config.image,
                globalmon_config_dir="/home/ubuntu",
                globalmon_secure_config_file_name="globalmon-secure.yaml",
                globalmon_config=globalmon_cfg,
                globalmon_secure_config=globalmon_secure_cfg,
            )

            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                artifact_dir=".cloudmon_artifact",
                project_dir=self.config.project_dir.as_posix(),
                playbook="install_globalmon.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=3,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning Globalmon")

    def stop(self, options):
        for _, globalmon_config in self.globalmon_configs.items():
            self.log.info(
                "Stopping Globalmon in monitoring zone %s",
                globalmon_config.zone,
            )
            extravars = dict(
                globalmon_group_name=globalmon_config.ansible_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                artifact_dir=".cloudmon_artifact",
                project_dir=self.config.project_dir.as_posix(),
                playbook="stop_globalmon.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error stopping Globalmon")

    def start(self, options):
        for _, globalmon_config in self.globalmon_configs.items():
            self.log.info(
                "Starting Globalmon in monitoring zone %s",
                globalmon_config.zone,
            )
            extravars = dict(
                globalmon_group_name=globalmon_config.ansible_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                artifact_dir=".cloudmon_artifact",
                project_dir=self.config.project_dir.as_posix(),
                playbook="start_globalmon.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error starting Globalmon")
