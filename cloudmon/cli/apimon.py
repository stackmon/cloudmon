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

from cloudmon.plugin.apimon import ApiMonManager


class ApiMonProvision(Command):
    "Provision Api Monitoring plugin"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning ApiMon")
        manager = ApiMonManager(self.app.config)
        manager.provision(parsed_args)


class ApiMonStop(Command):
    "Stop Api Monitoring plugin processes"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("--component", help="ApiMon component")
        return parser

    def take_action(self, parsed_args):
        self.log.info("Stopping ApiMon")
        manager = ApiMonManager(self.app.config)
        manager.stop(parsed_args)


class ApiMonStart(Command):
    "Starting Api Monitoring plugin processes"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super().get_parser(prog_name)
        parser.add_argument("--component", help="ApiMon component")
        return parser

    def take_action(self, parsed_args):
        self.log.info("Starting ApiMon")
        manager = ApiMonManager(self.app.config)
        manager.start(parsed_args)
