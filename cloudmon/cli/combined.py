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

from cloudmon.cli import apimon
from cloudmon.cli import epmon
from cloudmon.cli import graphite
from cloudmon.cli import postgres
from cloudmon.cli import statsd


class Provision(Command):
    "Provision all necessary StackMon components"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        graphite_cmd = graphite.GraphiteProvision(self.app, self.app_args)
        statsd_cmd = statsd.StatsdProvision(self.app, self.app_args)
        pg_cmd = postgres.PostgreSQLProvision(self.app, self.app_args)
        epmon_cmd = epmon.EpmonProvision(self.app, self.app_args)
        apimon_cmd = apimon.ApiMonProvision(self.app, self.app_args)

        graphite_cmd.take_action(parsed_args)
        statsd_cmd.take_action(parsed_args)
        pg_cmd.take_action(parsed_args)
        epmon_cmd.take_action(parsed_args)
        apimon_cmd.take_action(parsed_args)
