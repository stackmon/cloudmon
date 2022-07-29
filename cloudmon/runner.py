import argparse
import logging
import sys
import yaml

import ansible_runner


COMMAND_CHOICES = ["configure", "stop", "start"]


class ApiMonConfig:
    def __init__(self):
        self.statsd_host = None
        self.graphite_host = None
        self.schedulers_group_name = None
        self.executors_group_name = None
        self.scheduler_host = None
        self.scheduler_image = None
        self.executor_image = None
        self.test_projects = dict()
        self.test_matrix = dict()
        self.test_environments = dict()
        self.clouds = dict()
        self.zone = None
        self.ref = None

    def __repr__(self):
        return (
            f"ApiMon("
            f"statsd_host:{self.statsd_host}; "
            f"scheduler_host: {self.scheduler_host}; "
            f"test_projects: {self.test_projects}; "
            f"test_matrix: {self.test_matrix}; "
            f"test_environments: {self.test_environments}; "
            f"clouds: {self.clouds}"
            f")"
        )


class CloudMonConfig:
    def __init__(self):
        self.config = None
        self.inventory = None
        self.inventory_path = None
        self.apimon_configs = dict()
        self.private_data_dir = None


class CloudMonCommand:
    pass


class CloudMonProvision(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser(
            "provision", help="Provision CloudMon components"
        )
        subparser.add_argument("--plugin", help="Plugin name")

    def provision_statsd(self, config, group_name, graphite_host, check):
        logging.info("Provisioning StatsD on %s", group_name)
        extravars = dict(
            statsd_hosts=group_name,
            statsd_graphite_host=graphite_host,
            statsd_graphite_port=2003,
            statsd_graphite_port_pickle=2004,
            statsd_graphite_protocol="pickle",
            statsd_legacy_namespace=False,
            statsd_server="./servers/udp",
            ansible_check_mode=check,
        )
        r = ansible_runner.run(
            private_data_dir=config.private_data_dir,
            playbook="install_statsd.yaml",
            inventory=config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error configuring StatsD")

    def provision_graphite(self, config, check):
        logging.info("Provisioning Graphite")
        extravars = dict(
            ansible_check_mode=check,
        )
        r = ansible_runner.run(
            private_data_dir=config.private_data_dir,
            playbook="install_graphite.yaml",
            inventory=config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error configuring Graphite")

    def provision_apimon_schedulers(self, config, check):
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Provisioning ApiMon Scheduler in monitoring zone %s",
                apimon_config.zone,
            )
            # Configure statsd
            self.provision_statsd(
                config,
                apimon_config.schedulers_group_name,
                apimon_config.graphite_host,
                check,
            )

            schedulers = config.inventory[apimon_config.schedulers_group_name][
                "hosts"
            ]
            if len(schedulers) > 1:
                raise RuntimeError(
                    "Deploying ApiMon Scheduler to more then one host is "
                    "currently not supported"
                )

            extravars = dict(
                ansible_check_mode=check,
                scheduler_config_file_name="apimon-scheduler.yaml",
                scheduler_secure_config_file_name="apimon-scheduler-secure.yaml",
                schedulers_group_name=apimon_config.schedulers_group_name,
            )
            if apimon_config.scheduler_image:
                extravars["scheduler_image"] = apimon_config.scheduler_image

            scheduler_config = dict(
                secure="/etc/apimon/apimon-scheduler-secure.yaml",
                gear=[dict(host="0.0.0.0", port=4730, start=True)],
                log=dict(config="/etc/apimon/logging.conf"),
                metrics=dict(
                    statsd=dict(host=apimon_config.statsd_host, port=8125)
                ),
                scheduler=dict(
                    socket="/tmp/scheduler.socket",
                    refresh_interval=10,
                    work_dir="/var/lib/apimon",
                    zone=apimon_config.zone,
                ),
                test_environments=list(
                    apimon_config.test_environments.values()
                ),
                test_projects=list(apimon_config.test_projects.values()),
                test_matrix=list(apimon_config.test_matrix.values()),
            )
            scheduler_secure_config = dict(
                clouds=list(apimon_config.clouds.values())
            )
            extravars["scheduler_config"] = scheduler_config
            extravars["scheduler_secure_config"] = scheduler_secure_config

            logging.debug("Scheduler extra vars: %s", extravars)

            r = ansible_runner.run(
                private_data_dir=config.private_data_dir,
                playbook="install_scheduler.yaml",
                inventory=config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning ApiMon Schedulers")

    def provision_apimon_executors(self, config, check):
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Provision ApiMon Executors for %s", apimon_config.zone
            )
            extravars = dict(
                executor_config_file_name="apimon-executor.yaml",
                executor_secure_config_file_name="apimon-executor-secure.yaml",
                executors_group_name=apimon_config.executors_group_name,
            )
            if apimon_config.executor_image:
                extravars["executor_image"] = apimon_config.executor_image

            executor_config = dict(
                ansible_check_mode=check,
                secure="/etc/apimon/apimon-executor-secure.yaml",
                gear=[dict(host=apimon_config.scheduler_host, port=4730)],
                log=dict(config="/etc/apimon/logging.conf"),
                metrics=dict(
                    statsd=dict(host=apimon_config.statsd_host, port=8125)
                ),
                executor=dict(
                    load_multiplier=2,
                    socket="/tmp/executor.socket",
                    work_dir="/var/lib/apimon",
                    zone=apimon_config.zone,
                    logs_cloud="swift",
                ),
            )
            executor_secure_config = dict()
            extravars["executor_config"] = executor_config
            extravars["executor_secure_config"] = executor_secure_config

            logging.debug("Executor extra vars: %s", extravars)

            r = ansible_runner.run(
                private_data_dir=config.private_data_dir,
                playbook="install_executor.yaml",
                inventory=config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning ApiMon Executors")

    def provision_grafana_ds(self, config, check):
        logging.debug("Configuring Grafana datasources")
        grafana_config = config.config["grafana"]
        grafana_datasources = dict()
        if "carbon" in grafana_config:
            carbon = grafana_config["carbon"]
            grafana_datasources["cloudmon"] = dict(
                grafana_url=grafana_config["api_url"],
                grafana_api_key=grafana_config["api_token"],
ds_type="graphite",
                ds_url=carbon["url"],
                tls_skip_veriy=carbon.get("tls_skip_verify", False)
            )
        extravars = dict(
            ansible_check_mode=check,
            grafana_datasources=grafana_datasources,
        )
        r = ansible_runner.run(
            private_data_dir=config.private_data_dir,
            playbook="manage_grafana_ds.yaml",
            inventory=config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error configuring datasources in Grafana")

    def execute(self, config, args):
        self.provision_graphite(config, args.check)
        if args.plugin == "apimon":
            logging.debug("Provisionings ApiMon")
            self.provision_apimon_schedulers(config, args.check)
            self.provision_apimon_executors(config, args.check)
        if not args.plugin:
            self.provision_grafana_ds(config, args.check)


class CloudMonStop(CloudMonCommand):
    @classmethod
    def argparse_arguments(cls, parser):
        subparser = parser.add_parser("stop", help="Stop CloudMon components")
        subparser.add_argument("--plugin", help="Plugin name")
        subparser.add_argument("--component", help="Plugin component")

    def execute(self, config, args):
        if args.plugin == "apimon":
            logging.debug("Stopping ApiMon")
            if not args.component:
                self.stop_apimon_schedulers(config, args.check)
                self.stop_apimon_executors(config, args.check)
            else:
                if args.component == "scheduler":
                    self.stop_apimon_schedulers(config, args.check)
                elif args.component == "executor":
                    self.stop_apimon_executors(config, args.check)

    def stop_apimon_schedulers(self, config, check):
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Stopping ApiMon Scheduler in monitoring zone %s",
                apimon_config.zone,
            )
            extravars = dict(
                ansible_check_mode=check,
                schedulers_group_name=apimon_config.schedulers_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=config.private_data_dir,
                playbook="stop_schedulers.yaml",
                inventory=config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error stopping ApiMon Schedulers")

    def stop_apimon_executors(self, config, check):
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Stopping ApiMon Executors in monitoring zone %s",
                apimon_config.zone,
            )
            extravars = dict(
                ansible_check_mode=check,
                executors_group_name=apimon_config.executors_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=config.private_data_dir,
                playbook="stop_executors.yaml",
                inventory=config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error stopping ApiMon Executors")


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
            if not args.component:
                self.start_apimon_schedulers(config, args.check)
                self.start_apimon_executors(config, args.check)
            else:
                if args.component == "scheduler":
                    self.start_apimon_schedulers(config, args.check)
                elif args.component == "executor":
                    self.start_apimon_executors(config, args.check)

    def start_apimon_schedulers(self, config, check):
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Starting ApiMon Scheduler in monitoring zone %s",
                apimon_config.zone,
            )
            extravars = dict(
                ansible_check_mode=check,
                schedulers_group_name=apimon_config.schedulers_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=config.private_data_dir,
                playbook="start_schedulers.yaml",
                inventory=config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error starting ApiMon Schedulers")

    def start_apimon_executors(self, config, check):
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Starting ApiMon Executors in monitoring zone %s",
                apimon_config.zone,
            )
            extravars = dict(
                ansible_check_mode=check,
                executors_group_name=apimon_config.executors_group_name,
            )
            r = ansible_runner.run(
                private_data_dir=config.private_data_dir,
                playbook="start_executors.yaml",
                inventory=config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error starting ApiMon Executors")


class CloudMon:
    def __init__(self):
        self.config = None
        self.inventory = None
        self.apimon_configs = dict()
        self.default_extravars = dict(
            distro_lookup_path=[
                "{{ ansible_facts.distribution }}.{{ ansible_facts.lsb.codename|default() }}.{{ ansible_facts.architecture }}.yaml"
                "{{ ansible_facts.distribution }}.{{ ansible_facts.lsb.codename|default() }}.yaml"
                "{{ ansible_facts.distribution }}.{{ ansible_facts.architecture }}.yaml"
                "{{ ansible_facts.distribution }}.yaml"
                "{{ ansible_facts.os_family }}.yaml"
                "default.yaml"
            ]
        )

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
        apimon_config = self.apimon_configs.setdefault(zone, ApiMonConfig())
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
        """Process every individual matrix entry and configure components
        correspondingly
        """
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
