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

from cloudmon.service.metrics import MetricsProcessorManager


class MetricsProcessorProvision(Command):
    "Provision Metrics Processor service"
    log = logging.getLogger(__name__)

    def get_parser(self, prog_name):
        parser = super(MetricsProcessorProvision, self).get_parser(prog_name)

        parser.add_argument(
            "--config-dir",
            help=(
                "Directory with additional configuration content (i.e. "
                "config files)"
            ),
        )

        return parser

    def take_action(self, parsed_args):
        self.log.info("Provisioning Metrics Processor")
        manager = MetricsProcessorManager(self.app.config)
        manager.provision(parsed_args)
