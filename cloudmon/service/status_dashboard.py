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

import importlib
import logging
from pathlib import Path
import shutil
import subprocess
import yaml

from jinja2 import Environment
from jinja2 import PackageLoader


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
        overlays_dir = Path(kustomize_base_dir, "overlays")
        kust_base_src = Path(
            importlib.resources.files("cloudmon"), "kustomize", "sdb"
        )
        shutil.copytree(kust_base_src, kustomize_base_dir)
        base = "../../base"
        for name, instance in self.config.status_dashboard.items():
            kustomization = dict(
                apiVersion="kustomize.config.k8s.io/v1beta1",
                kind="Kustomization",
            )
            for k, v in instance.kustomization.__dict__.items():
                kustomization[k] = v
            resources = kustomization.setdefault("resources", [])
            if base not in resources:
                resources.append(base)
            print(yaml.dump(kustomization))

            overlay_dir = Path(overlays_dir, name)
            overlay_dir.mkdir(parents=True, exist_ok=True)
            with open(Path(overlay_dir, "kustomization.yaml"), "w") as f:
                yaml.dump(kustomization, f)
            res = subprocess.run(
                args=[
                    "kubectl",
                    "--context",
                    instance.kube_context,
                    "--namespace",
                    instance.kube_namespace,
                    "apply",
                    "-k",
                    ".",
                ],
                cwd=overlay_dir,
                check=True,
            )
            self.log.debug(res.stdout)
            self.log.error(res.stderr)
