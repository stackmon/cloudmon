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

from cloudmon.service.grafana import GrafanaManager


class GrafanaProvision(Command):
    "Provision Grafana"
    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Provisioning Grafana")
        grafana_config = self.app.config.model.grafana
        manager = GrafanaManager(
            cloudmon_config=self.app.config,
            api_url=grafana_config.api_url,
            api_token=grafana_config.api_token,
        )
        manager.provision(parsed_args)


class GrafanaConfigure(Command):
    "Configure Grafana"

    log = logging.getLogger(__name__)

    def take_action(self, parsed_args):
        self.log.info("Configuring Grafana")
        grafana_config = self.app.config.model.grafana
        manager = GrafanaManager(
            cloudmon_config=self.app.config,
            api_url=grafana_config.api_url,
            api_token=grafana_config.api_token,
        )
        manager.provision_ds(parsed_args)
        manager.provision_dashboards(parsed_args)
