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
from pathlib import Path

from jinja2 import Environment
from jinja2 import PackageLoader

from cloudmon import utils


class StatusDashboardManager:
    log = logging.getLogger(__name__)

    def __init__(self, cloudmon_config):
        self.config = cloudmon_config

        self.env = Environment(loader=PackageLoader("cloudmon"))

    def provision(self, options):
        """Provision Status Dashboard"""

        kustomize_base_dir = Path(
            self.config.private_data_dir, "kustomize", "sdb"
        )
        utils.copy_kustomize_app_base(kustomize_base_dir, "sdb")
        overlays_dir = Path(kustomize_base_dir, "overlays")
        base = "../../base"
        for instance in self.config.model.status_dashboard:
            overlay_dir = utils.prepare_kustomize_overlay(
                overlays_dir=overlays_dir,
                base=base,
                name=instance.name,
                kustomization=instance.kustomization.__root__,
                config_dir=self.config.config_dir,
            )

            res = utils.apply_kustomize(
                overlay_dir=overlay_dir,
                kube_context=instance.kube_context,
                kube_namespace=instance.kube_namespace,
            )
            self.log.debug(res.stdout)
            self.log.error(res.stderr)
