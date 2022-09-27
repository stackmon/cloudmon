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
import copy
import logging
import sys

import ansible_runner
from ruamel.yaml import YAML

from cloudmon.plugin import apimon
from cloudmon.plugin import epmon
from cloudmon.service import grafana
from cloudmon.service import statsd
from cloudmon.service import sqldb
from cloudmon.service import tsdb
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
        self.is_updated = False

    def get_statsd_zone_address(self, zone):
        statsd_group_name = self.config["monitoring_zones"][zone].get(
            "statsd_group_name", "statsd"
        )
        statsd_servers = self.inventory[statsd_group_name]["hosts"]
        statsd_host_vars = self.inventory["_meta"]["hostvars"].get(
            statsd_servers[0]
        )
        # internal_address or ansible_host or hostname
        statsd_address = statsd_host_vars.get(
            "internal_address",
            statsd_host_vars.get("ansible_host", statsd_servers[0]),
        )

        return statsd_address

    def get_graphite_zone_address(self, zone):
        graphite_group_name = self.config["monitoring_zones"][zone].get(
            "graphite_group_name", "graphite"
        )
        graphite_servers = self.inventory[graphite_group_name]["hosts"]
        graphite_host_vars = self.inventory["_meta"]["hostvars"].get(
            graphite_servers[0]
        )
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
        if "clouds_credentials" not in self.config:
            raise RuntimeError("clouds_credentials are not set in config")
        env = self.config["environments"][env_name]
        if zone_name not in env["monitoring_zones"]:
            raise RuntimeError(
                "Environment %s has no monitoring zone %s defined",
                env_name,
                zone_name,
            )
        clouds = env["monitoring_zones"][zone_name].get("clouds", [])
        res = dict()
        for cloud in clouds:
            c_name = cloud["name"]
            c_ref = cloud["ref"]
            cloud_creds = self.config["clouds_credentials"][c_ref]
            res[c_name] = dict(name=c_name, data=cloud_creds)

        return res

    def get_env_cloud_credentials(self, env_name, zone_name, cloud_name):
        data = self.get_env_clouds_credentials(env_name, zone_name)
        return data.get(cloud_name)


class CloudMonCommand:
    pass


class CloudMonProvision(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser(
            "provision", help="Provision CloudMon components"
        )
        subparser.add_argument("--plugin", help="Plugin name")
        subparser.add_argument("--service", help="Service name")

    def execute(self, config, args):
        # Provision services
        if not args.plugin:
            if args.service == "graphite" or not args.service:
                manager = tsdb.GraphiteManager(config)
                manager.provision(args.check)
            if args.service == "postgresql" or not args.service:
                manager = sqldb.PostgreSQLManager(config)
                manager.provision(args.check)
            if args.service == "statsd" or not args.service:
                manager = statsd.StatsdManager(config)
                manager.provision(args.check)
            if args.service == "grafana" or not args.service:
                grafana_config = config.config["grafana"]
                manager = grafana.GrafanaManager(
                    cloudmon_config=config,
                    api_url=grafana_config.get("api_url"),
                    api_token=grafana_config.get("api_token"),
                )

                manager.provision(config, args.check)
                manager.provision_ds(config, args.check)
                manager.provision_dashboards(config, args.check)

        # Provision plugins
        if not args.service:
            if args.plugin == "apimon" or not args.plugin:
                logging.debug("Provisionings ApiMon")
                manager = apimon.ApiMonManager(config)
                manager.provision(args.check)
            if args.plugin == "epmon" or not args.plugin:
                logging.debug("Provisionings EpMon")
                manager = epmon.EpmonManager(config)
                manager.provision(args.check)

class CloudMonStop(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser("stop", help="Stop CloudMon components")
        subparser.add_argument("--plugin", help="Plugin name")
        subparser.add_argument("--component", help="Plugin component")

    def execute(self, config, args):
        if args.plugin == "apimon":
            logging.debug("Stopping ApiMon")
            manager = apimon.ApiMonManager(config)
            manager.stop(args.component, args.check)
        elif args.plugin == "epmon":
            logging.debug("Stopping EpMon")
            manager = epmon.EpmonManager(config)
            manager.stop(args.check)


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
            manager = apimon.ApiMonManager(config)
            manager.start(args.component, args.check)
        elif args.plugin == "epmon":
            logging.debug("Starting EpMon")
            manager = epmon.EpmonManager(config)
            manager.start(args.check)


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

        yaml = YAML()
        with open(self.args.config, "r") as f:
            self.config = yaml.load(f)

        out, err = ansible_runner.get_inventory(
            action="list",
            inventories=[self.args.inventory],
            response_format="json",
            process_isolation=False,
        )
        self.inventory = out
        self.process_inventory()
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

        if config.is_updated:
            yaml.indent(offset=2, sequence=4)
            with open(self.args.config, "w") as f:
                yaml.dump(self.config, f)
            logging.info("Your config file was updated by the process")

        sys.exit(0)


def main():
    CloudMon().main()


if __name__ == "__main__":
    main()
