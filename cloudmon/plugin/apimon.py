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

import ansible_runner


class ApiMonConfig:
    def __init__(self):
        self.statsd_host = None
        self.schedulers_group_name = None
        self.executors_group_name = None
        self.scheduler_host = None
        self.scheduler_image = None
        self.executor_image = None
        self.test_projects = dict()
        self.test_matrix = dict()
        self.test_environments = dict()
        self.clouds = dict()
        self.db_url = None
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


class ApiMonManager:
    def __init__(self, cloudmon_config):
        self.config = cloudmon_config
        self.apimon_configs = dict()
        self.process_config()

    def process_config(self):
        """Process config

        Process every individual matrix entry and configure components
        correspondingly

        """
        for matrix_entry in self.config.config["matrix"]:
            logging.debug("Processing %s", matrix_entry)
            for plugin in matrix_entry["plugins"]:
                logging.debug("Processing plugin %s", plugin)
                plugin_data = self.config.config["cloudmon_plugins"].get(
                    plugin["name"]
                )
                if not plugin_data:
                    logging.warn("Plugin is not known in cloudmon_plugins")
                if plugin_data.get("type") == "apimon":
                    # For now we only construct global apimon config matrix
                    self.process_plugin_entry(
                        plugin_data, matrix_entry, plugin
                    )
        logging.debug(f"ApiMon config: {self.apimon_configs}")

    def process_plugin_entry(self, plugin_ref, matrix_entry, plugin):
        plugin_ref = self.config.config["cloudmon_plugins"][plugin["name"]]
        env_name = matrix_entry["env"]
        zone = matrix_entry["monitoring_zone"]
        if zone in self.apimon_configs:
            raise RuntimeError(
                f"ApiMon entry for zone {zone} is already present. "
                "Having multiple entries is not supported yet"
            )
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
        if "db_url" in matrix_entry:
            apimon_config.db_url = matrix_entry["db_url"]
        elif "db_entry" in matrix_entry:
            (db_name, user_name) = matrix_entry["db_entry"].split(".")
            for db in self.config.config["database"]["databases"]:
                if db["name"] == db_name:
                    for user in db["users"]:
                        if user["name"] == user_name:
                            db_host = self.config.inventory["postgres"][
                                "hosts"
                            ][0]
                            db_host_vars = self.config.inventory["_meta"][
                                "hostvars"
                            ][db_host]

                            db_host_ip = db_host_vars.get(
                                "internal_address", db_host
                            )
                            db_url = (
                                f"postgresql://{user_name}:{user['password']}"
                                f"@{db_host_ip}:5432/{db_name}"
                            )
                            apimon_config.db_url = db_url

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
            apimon_config.clouds.update(
                self.config.get_env_clouds_credentials(env_name, zone)
            )

        statsd_address = self.config.get_statsd_zone_address(zone)

        schedulers = self.config.inventory[
            apimon_config.schedulers_group_name
        ]["hosts"]
        random_scheduler_host = schedulers[0]
        scheduler_host_vars = self.config.inventory["_meta"]["hostvars"].get(
            random_scheduler_host
        )
        apimon_config.scheduler_host = scheduler_host_vars.get(
            "internal_address", random_scheduler_host
        )
        apimon_config.statsd_host = scheduler_host_vars.get(
            "internal_address", statsd_address
        )
        apimon_config.scheduler_image = plugin_ref.get("scheduler_image")
        apimon_config.executor_image = plugin_ref.get("executor_image")

        self.apimon_configs[zone] = apimon_config

    def get_apimon_env(self, env_name, zone):
        if env_name not in self.config.config["environments"]:
            raise RuntimeError("Environment %s is not known", env_name)
        env = self.config.config["environments"][env_name]
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

    def provision(self, check):
        self.provision_schedulers(check)
        self.provision_executors(check)

    def provision_schedulers(self, check):
        for _, apimon_config in self.apimon_configs.items():
            logging.info(
                "Provisioning ApiMon Scheduler in monitoring zone %s",
                apimon_config.zone,
            )

            schedulers = self.config.inventory[
                apimon_config.schedulers_group_name
            ]["hosts"]
            if len(schedulers) > 1:
                raise RuntimeError(
                    "Deploying ApiMon Scheduler to more then one host is "
                    "currently not supported"
                )

            extravars = dict(
                ansible_check_mode=check,
                scheduler_config_dir="/etc/cloudmon",
                scheduler_config_file_name="apimon-scheduler.yaml",
                scheduler_secure_config_file_name=(
                    "apimon-scheduler-secure.yaml"),
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
                private_data_dir=self.config.private_data_dir,
                playbook="install_scheduler.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning ApiMon Schedulers")

    def provision_executors(self, check):
        for _, apimon_config in self.apimon_configs.items():
            logging.info(
                "Provision ApiMon Executors for %s", apimon_config.zone
            )
            extravars = dict(
                executor_config_dir="/etc/cloudmon",
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
            executor_secure_config = dict(executor={})
            if apimon_config.db_url:
                executor_secure_config["executor"] = dict(
                    db_url=apimon_config.db_url
                )
            extravars["executor_config"] = executor_config
            extravars["executor_secure_config"] = executor_secure_config

            logging.debug("Executor extra vars: %s", extravars)

            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                playbook="install_executor.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=1,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning ApiMon Executors")

    def stop(self, component=None, check=False):
        for _, apimon_config in self.apimon_configs.items():
            if not component:
                self.stop_executors(apimon_config, check)
                self.stop_schedulers(apimon_config, check)
            elif component == "executor":
                self.stop_executors(apimon_config, check)
            elif component == "scheduler":
                self.stop_schedulers(apimon_config, check)

    def start(self, component=None, check=False):
        for _, apimon_config in self.apimon_configs.items():
            if not component:
                self.start_executors(apimon_config, check)
                self.start_schedulers(apimon_config, check)
            elif component == "executor":
                self.start_executors(apimon_config, check)
            elif component == "scheduler":
                self.start_schedulers(apimon_config, check)

    def stop_schedulers(self, apimon_config, check):
        logging.info(
            "Stopping ApiMon Scheduler in monitoring zone %s",
            apimon_config.zone,
        )
        extravars = dict(
            ansible_check_mode=check,
            schedulers_group_name=apimon_config.schedulers_group_name,
        )
        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            playbook="stop_schedulers.yaml",
            inventory=self.config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error stopping ApiMon Schedulers")

    def stop_executors(self, apimon_config, check):
        logging.info(
            "Stopping ApiMon Executors in monitoring zone %s",
            apimon_config.zone,
        )
        extravars = dict(
            ansible_check_mode=check,
            executors_group_name=apimon_config.executors_group_name,
        )
        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            playbook="stop_executors.yaml",
            inventory=self.config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error stopping ApiMon Executors")

    def start_schedulers(self, apimon_config, check):
        logging.info(
            "Starting ApiMon Scheduler in monitoring zone %s",
            apimon_config.zone,
        )
        extravars = dict(
            ansible_check_mode=check,
            schedulers_group_name=apimon_config.schedulers_group_name,
        )
        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            playbook="start_schedulers.yaml",
            inventory=self.config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error starting ApiMon Schedulers")

    def start_executors(self, apimon_config, check):
        logging.info(
            "Starting ApiMon Executors in monitoring zone %s",
            apimon_config.zone,
        )
        extravars = dict(
            ansible_check_mode=check,
            executors_group_name=apimon_config.executors_group_name,
        )
        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            playbook="start_executors.yaml",
            inventory=self.config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error starting ApiMon Executors")
