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

from cliff.command import Command

from cloudmon.service.sqldb import PostgreSQLManager


class PostgreSQLProvision(Command):
    "Provision PostgreSQL Database servers"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning PostgreSQL")
        manager = PostgreSQLManager(self.app.config)
        manager.provision(parsed_args)


class PostgreSQLUnprovision(Command):
    "Unprovision PostgreSQL Database servers"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning PostgreSQL")
        manager = PostgreSQLManager(self.app.config)
        manager.unprovision(parsed_args)


class PostgreSQLProvisionDB(Command):
    "Create PostgreSQL Databases and Users"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning PostgreSQL database")
        manager = PostgreSQLManager(self.app.config)
        manager.provision_db(parsed_args)


class PostgreSQLStop(Command):
    "Stop PostgreSQL Database"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning PostgreSQL database")
        manager = PostgreSQLManager(self.app.config)
        manager.stop(parsed_args)


class PostgreSQLStart(Command):
    "Start PostgreSQL Database"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning PostgreSQL database")
        manager = PostgreSQLManager(self.app.config)
        manager.start(parsed_args)
