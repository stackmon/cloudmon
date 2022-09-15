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

from cloudmon import statsd


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


class ApiMonManager:
    def provision_schedulers(self, config, check):
        statsd_manager = statsd.StatsdManager()
        for _, apimon_config in config.apimon_configs.items():
            logging.info(
                "Provisioning ApiMon Scheduler in monitoring zone %s",
                apimon_config.zone,
            )
            # Configure statsd
            statsd_manager.provision_statsd(
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

    def provision_executors(self, config, check):
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

    def stop_schedulers(self, config, check):
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

    def stop_executors(self, config, check):
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

    def start_schedulers(self, config, check):
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

    def start_executors(self, config, check):
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
