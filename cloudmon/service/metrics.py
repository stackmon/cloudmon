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
import yaml

from jinja2 import Environment
from jinja2 import PackageLoader

from cloudmon import utils


class MetricsProcessorManager:
    log = logging.getLogger(__name__)

    def __init__(self, cloudmon_config):
        self.config = cloudmon_config

        self.env = Environment(loader=PackageLoader("cloudmon"))

    def provision(self, options):
        """Provision Metrics Processor"""

        kustomize_base_dir = Path(
            self.config.private_data_dir, "kustomize", "metrics_processor"
        )
        utils.copy_kustomize_app_base(kustomize_base_dir, "metrics_processor")
        overlays_dir = Path(kustomize_base_dir, "overlays")
        base = "../../base"
        for instance in self.config.model.metrics_processor:
            cm_gen = instance.kustomization.root.setdefault(
                "configMapGenerator", []
            )
            cm_gen.append(
                dict(
                    name="metrics-processor-config",
                    behavior="merge",
                    files=["config.yaml"],
                )
            )
            overlay_dir = utils.prepare_kustomize_overlay(
                overlays_dir=overlays_dir,
                base=base,
                name=instance.name,
                kustomization=instance.kustomization.root,
                config_dir=self.config.config_dir,
            )

            with open(Path(overlay_dir, "config.yaml"), "w") as fp:
                mp_config = dict(
                    datasource=dict(
                        url=instance.datasource_url,
                        type=instance.datasource_type,
                    ),
                    environments=[i.dict() for i in instance.environments],
                    server={"port": 3005},
                )
                if instance.status_dashboard_instance_name:
                    sdb = self.config.model.get_sdb_by_name(
                        instance.status_dashboard_instance_name
                    )
                    if not sdb:
                        raise ValueError(
                            "status dashboard %s is refered from metrics "
                            "processor, but not defined"
                            % instance.status_dashboard_instance_name
                        )
                    mp_config.update(
                        dict(
                            status_dashboard=dict(
                                secret=sdb.api_secret,
                                url="https://" + sdb.domain_name,
                            )
                        )
                    )
                yaml.dump(mp_config, fp)

            res = utils.apply_kustomize(
                overlay_dir=overlay_dir,
                kube_context=instance.kube_context,
                kube_namespace=instance.kube_namespace,
            )
            self.log.debug(res.stdout)
            self.log.error(res.stderr)
