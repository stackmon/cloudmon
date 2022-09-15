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


class StatsdManager:
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
