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

import argparse
import logging
import sys
import yaml

import ansible_runner

from cloudmon import apimon
from cloudmon import grafana
from cloudmon import utils


COMMAND_CHOICES = ["configure", "stop", "start"]


class CloudMonConfig:
    def __init__(self):
        self.config = None
        self.inventory = None
        self.inventory_path = None
        self.apimon_configs = dict()
        self.private_data_dir = None
        self.default_extravars = dict(
            distro_lookup_path=[
                "{{ ansible_facts.distribution }}.{{ ansible_facts.lsb.codename|default() }}.{{ ansible_facts.architecture }}.yaml",
                "{{ ansible_facts.distribution }}.{{ ansible_facts.lsb.codename|default() }}.yaml",
                "{{ ansible_facts.distribution }}.{{ ansible_facts.architecture }}.yaml",
                "{{ ansible_facts.distribution }}.yaml",
                "{{ ansible_facts.os_family }}.yaml",
                "default.yaml",
            ]
        )


class CloudMonCommand:
    pass


class CloudMonProvision(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser(
            "provision", help="Provision CloudMon components"
        )
        subparser.add_argument("--plugin", help="Plugin name")

    def provision_graphite(self, config, check):
        logging.info("Provisioning Graphite")
        extravars = dict(
            ansible_check_mode=check,
        )
        # TODO: it is bad to override with defaults after assignment
        extravars.update(config.default_extravars)
        r = ansible_runner.run(
            private_data_dir=config.private_data_dir,
            playbook="install_graphite.yaml",
            inventory=config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error configuring Graphite")

    def execute(self, config, args):
        self.provision_graphite(config, args.check)
        if args.plugin == "apimon":
            logging.debug("Provisionings ApiMon")
            apimon_manager = apimon.ApiMonManager()
            apimon_manager.provision_schedulers(config, args.check)
            apimon_manager.provision_executors(config, args.check)
        if not args.plugin:
            grafana_config = config.config["grafana"]
            grafana_manager = grafana.GrafanaManager(
                api_url=grafana_config["api_url"],
                api_token=grafana_config["api_token"],
            )

            grafana_manager.provision_ds(grafana_config, args.check)
            grafana_manager.provision_dashboards(grafana_config, args.check)


class CloudMonStop(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser("stop", help="Stop CloudMon components")
        subparser.add_argument("--plugin", help="Plugin name")
        subparser.add_argument("--component", help="Plugin component")

    def execute(self, config, args):
        if args.plugin == "apimon":
            logging.debug("Stopping ApiMon")
            apimon_manager = apimon.ApiMonManager()
            if not args.component:
                apimon_manager.stop_schedulers(config, args.check)
                apimon_manager.stop_executors(config, args.check)
            else:
                if args.component == "scheduler":
                    apimon_manager.stop_schedulers(config, args.check)
                elif args.component == "executor":
                    apimon_manager.stop_executors(config, args.check)


class CloudMonStart(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser(
            "start", help="Start CloudMon components"
        )
        subparser.add_argument("--plugin", help="Plugin name")
        subparser.add_argument("--component", help="Plugin component")

    def execute(self, config, args):
        if args.plugin == "apimon":
            logging.debug("Starting ApiMon")
            apimon_manager = apimon.ApiMonManager()
            if not args.component:
                apimon_manager.start_schedulers(config, args.check)
                apimon_manager.start_executors(config, args.check)
            else:
                if args.component == "scheduler":
                    apimon_manager.start_schedulers(config, args.check)
                elif args.component == "executor":
                    apimon_manager.start_executors(config, args.check)


class CloudMon:
    def __init__(self):
        self.config = None
        self.inventory = None
        self.apimon_configs = dict()

    def create_parser(self):
        parser = argparse.ArgumentParser(description="CloudMon Controller")
        subparsers = parser.add_subparsers(dest="command", help="command help")
        parser.add_argument(
            "--config",
            dest="config",
            default="config.yaml",
            help="specify the config file",
        )
        parser.add_argument(
            "--private-data-dir",
            dest="private_data_dir",
            default="ansible",
            help="Ansible-runner project dir",
        )
        parser.add_argument(
            "--inventory",
            dest="inventory",
            default="ansible/inventory",
            help="specify the Inventory path",
        )
        parser.add_argument(
            "--check", action="store_true", help="Check mode. Don't work yet."
        )

        CloudMonProvision.argparse_arguments(subparsers)
        CloudMonStop.argparse_arguments(subparsers)
        CloudMonStart.argparse_arguments(subparsers)

        return parser

    def parse_arguments(self, args=None):
        parser = self.create_parser()
        self.args = parser.parse_args(args)

        return parser

    def process_apimon_entry(self, matrix_entry, plugin):
        logging.debug("Here comes the apimon instance")
        plugin_ref = self.config["cloudmon_plugins"][plugin["name"]]
        env_name = matrix_entry["env"]
        zone = matrix_entry["monitoring_zone"]
        apimon_config = self.apimon_configs.setdefault(
            zone, apimon.ApiMonConfig()
        )
        apimon_config.zone = zone
        schedulers_group_name = plugin.get(
            "schedulers_inventory_group_name", "schedulers"
        )
        executors_group_name = plugin.get(
            "executors_inventory_group_name", "executor"
        )
        if (
            apimon_config.schedulers_group_name
            and apimon_config.schedulers_group_name != schedulers_group_name
        ):
            raise RuntimeError(
                "Cannot have different ApiMon Scheduler groups for same "
                "monitoring zone"
            )
        if (
            apimon_config.executors_group_name
            and apimon_config.executors_group_name != executors_group_name
        ):
            raise RuntimeError(
                "Cannot have different ApiMon Scheduler groups for same "
                "monitoring zone"
            )
        apimon_config.schedulers_group_name = schedulers_group_name
        apimon_config.executors_group_name = executors_group_name

        if plugin["tests_project"] not in apimon_config.test_projects:
            for project in plugin_ref["tests_projects"]:
                if project["name"] == plugin["tests_project"]:
                    apimon_config.test_projects[
                        plugin["tests_project"]
                    ] = project
                    break

        key = "%s:%s" % (env_name, plugin["tests_project"])
        if key in apimon_config.test_matrix:
            raise RuntimeError(
                "Something absolutely wrong - %s is already known", key
            )
        apimon_matrix_entry = dict(
            env=env_name,
            project=plugin["tests_project"],
            tasks=plugin.get("tasks"),
        )
        apimon_config.test_matrix[key] = apimon_matrix_entry
        if env_name not in apimon_config.test_environments:
            apimon_config.test_environments[env_name] = self.get_apimon_env(
                env_name, zone
            )
            apimon_config.clouds.update(self.get_apimon_clouds(env_name, zone))

        schedulers = self.inventory[apimon_config.schedulers_group_name][
            "hosts"
        ]
        random_scheduler_host = schedulers[0]
        scheduler_host_vars = self.inventory["_meta"]["hostvars"].get(
            random_scheduler_host
        )
        apimon_config.scheduler_host = scheduler_host_vars.get(
            "internal_address", random_scheduler_host
        )
        apimon_config.statsd_host = scheduler_host_vars.get(
            "internal_address", random_scheduler_host
        )
        apimon_config.scheduler_image = plugin_ref.get("scheduler_image")
        apimon_config.executor_image = plugin_ref.get("executor_image")
        apimon_config.graphite_host = plugin.get(
            "graphite_host", self.graphite_address
        )

        self.apimon_configs[zone] = apimon_config

    def get_apimon_env(self, env_name, zone):
        if env_name not in self.config["environments"]:
            raise RuntimeError("Environment %s is not known", env_name)
        env = self.config["environments"][env_name]
        if zone not in env["monitoring_zones"]:
            raise RuntimeError(
                "Environment %s has no monitoring zone %s defined",
                env_name,
                zone,
            )
        clouds = env["monitoring_zones"][zone].get("clouds", [])
        res = dict(name=env_name, env=env.get("env"), clouds=list())
        for cloud in clouds:
            res["clouds"].append(cloud["name"])
        return res

    def get_apimon_clouds(self, env_name, zone):
        if "clouds_credentials" not in self.config:
            raise RuntimeError("clouds_credentials are not set in config")
        env = self.config["environments"][env_name]
        if zone not in env["monitoring_zones"]:
            raise RuntimeError(
                "Environment %s has no monitoring zone %s defined",
                env_name,
                zone,
            )
        clouds = env["monitoring_zones"][zone].get("clouds", [])
        res = dict()
        for cloud in clouds:
            c_name = cloud["name"]
            c_ref = cloud["ref"]
            cloud_creds = self.config["clouds_credentials"][c_ref]
            res[c_name] = dict(name=c_name, data=cloud_creds)

        return res

    def process_matrix(self):
        """Process every individual matrix entry and configure components correspondingly"""
        for matrix_entry in self.config["matrix"]:
            logging.debug("Processing %s", matrix_entry)
            for plugin in matrix_entry["plugins"]:
                logging.debug("Processing plugin %s", plugin)
                plugin_data = self.config["cloudmon_plugins"].get(
                    plugin["name"]
                )
                if not plugin_data:
                    logging.warn("Plugin is not known in cloudmon_plugins")
                if plugin_data.get("type") == "apimon":
                    # For now we only construct global apimon config matrix
                    self.process_apimon_entry(matrix_entry, plugin)

    def process_inventory(self):
        """Pre-process passed inventory"""
        if "graphite" in self.inventory:
            random_graphite_host = self.inventory["graphite"]["hosts"][0]
            graphite_host_vars = self.inventory["_meta"]["hostvars"].get(
                random_graphite_host
            )
            self.graphite_address = graphite_host_vars.get(
                "internal_address", random_graphite_host
            )
        elif "graphite" in self.config:
            self.graphite_address = self.config["graphite"].get("host")

    def main(self):
        self.parse_arguments()
        logging.basicConfig(level=logging.DEBUG)

        with open(self.args.config, "r") as f:
            self.config = yaml.load(f, Loader=yaml.SafeLoader)

        out, err = ansible_runner.get_inventory(
            action="list",
            inventories=[self.args.inventory],
            response_format="json",
            process_isolation=False,
        )
        self.inventory = out
        self.process_inventory()
        self.process_matrix()
        config = CloudMonConfig()
        config.config = self.config
        config.inventory = self.inventory
        config.inventory_path = self.args.inventory
        config.apimon_configs = self.apimon_configs
        config.private_data_dir = self.args.private_data_dir

        if self.args.command == "stop":
            CloudMonStop().execute(config, self.args)
        elif self.args.command == "start":
            CloudMonStart().execute(config, self.args)
        elif self.args.command == "provision":
            CloudMonProvision().execute(config, self.args)
        sys.exit(0)


def main():
    CloudMon().main()


if __name__ == "__main__":
    main()
