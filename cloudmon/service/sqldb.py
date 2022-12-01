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

import copy
import logging

import ansible_runner


class PostgreSQLManager:
    log = logging.getLogger(__name__)

    def __init__(self, cloudmon_config):
        self.config = cloudmon_config

    def provision(self, options):
        self.log.info("Provisioning PostgreSQL")

        playbook_name = "install_postgresql.yaml"
        if self.config.model.database.ha_mode:
            playbook_name = "install_postgresql_ha.yaml"

        cloudmon_config = self.config

        extravars = copy.deepcopy(cloudmon_config.default_extravars)
        extravars.update(
            dict(
                postgresql_group_name="postgres",
            )
        )
        extravars.update(cloudmon_config.model.database.dict())
        r = ansible_runner.run(
            private_data_dir=cloudmon_config.private_data_dir,
            artifact_dir=".cloudmon_artifact",
            project_dir=self.config.project_dir.as_posix(),
            playbook=playbook_name,
            inventory=cloudmon_config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error Installing PostgreSQL")

    def unprovision(self, options):
        self.log.info("Unprovisioning PostgreSQL")

        playbook_name = "uninstall_postgresql.yaml"
        if self.config.config["database"].get("ha_mode"):
            playbook_name = "uninstall_postgresql_ha.yaml"

        cloudmon_config = self.config

        extravars = copy.deepcopy(cloudmon_config.default_extravars)
        extravars.update(
            dict(
                postgresql_group_name="postgres",
            )
        )
        extravars.update(**cloudmon_config.config["database"])
        r = ansible_runner.run(
            private_data_dir=cloudmon_config.private_data_dir,
            artifact_dir=".cloudmon_artifact",
            project_dir=self.config.project_dir.as_posix(),
            playbook=playbook_name,
            inventory=cloudmon_config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )
        if r.rc != 0:
            raise RuntimeError("Error Uninstalling PostgreSQL")

    def provision_db(self, options):
        self.log.info("Managing PostgreSQL databases")

        extravars = dict(
            postgres_root_password=self.config.config["database"][
                "postgres_postgres_password"
            ],
            postgresql_group_name="postgres",
            databases=self.config.config["database"]["databases"],
        )
        if self.config.config["database"].get("ha_mode", False):
            extravars["postgres_port"] = 5000

        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            artifact_dir=".cloudmon_artifact",
            project_dir=self.config.project_dir.as_posix(),
            playbook="manage_databases.yaml",
            inventory=self.config.inventory_path,
            extravars=extravars,
            verbosity=1,
        )

        if r.rc != 0:
            raise RuntimeError("Error Configuring PostgreSQL databases")

    def stop(self, options):
        self.log.info("Stopping PostgreSQL")
        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            project_dir=self.config.project_dir.as_posix(),
            artifact_dir=".cloudmon_artifact",
            playbook="stop_postgresql.yaml",
            inventory=self.config.inventory_path,
            verbosity=3,
        )
        if r.rc != 0:
            raise RuntimeError("Error Stopping PostgreSQL")

    def start(self, options):
        self.log.info("Starting PostgreSQL")
        r = ansible_runner.run(
            private_data_dir=self.config.private_data_dir,
            artifact_dir=".cloudmon_artifact",
            project_dir=self.config.project_dir.as_posix(),
            playbook="start_postgresql.yaml",
            inventory=self.config.inventory_path,
            verbosity=3,
        )
        if r.rc != 0:
            raise RuntimeError("Error starting PostgreSQL")
