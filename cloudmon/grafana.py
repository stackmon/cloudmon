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
import shutil
import yaml

from requests import Session
from urllib.parse import urljoin

from cloudmon import utils


class GrafanaSession(Session):
    def __init__(self, base_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url


class GrafanaManager:
    def __init__(self, api_url, api_token):
        self.base_url = api_url
        self._session = GrafanaSession(base_url=api_url)
        self._session.headers.update({"Authorization": f"Bearer {api_token}"})

    def request(self, method, url, *args, **kwargs):
        if not url.startswith("http"):
            url = urljoin(self.base_url, url)
        return self._session.request(method, url, *args, **kwargs)

    def ensure_folder(self, uid, title, **kwargs):
        response = self.request(method="GET", url=f"/api/folders/{uid}")
        if response.status_code == 404:
            response = self.request(
                method="POST",
                url="/api/folders",
                json=dict(uid=uid, title=title, **kwargs),
            )
        folder = response.json()

        return folder

    def provision_ds(self, config, check):
        logging.debug("Configuring Grafana datasources")
        if "carbon" in config:
            carbon = config["carbon"]
            ds_body = dict(
                access="proxy",
                name="cloudmon",
                type="graphite",
            )
            ds_body.update(carbon)
            response = self.request(
                method="GET", url="/api/datasources/name/cloudmon"
            )
            if response.status_code == 404:
                # Create DS
                response = self.request(
                    method="POST", url="/api/datasources", json=ds_body
                )
            else:
                # Update DS
                response = self.request(
                    method="PUT",
                    url=f"/api/datasources/{response.json()['id']}",
                    json=ds_body,
                )
            if response.status_code != 200:
                raise RuntimeError(
                    f"Error configuring datasources in Grafana: "
                    f"{response.text}"
                )

    def _get_panels(self, panel_defs):
        panels = []
        # Add header
        panels.append(
            dict(
                gridPos={"x": 0, "y": 0, "h": 2, "w": 24},
                type="text",
                transparent=True,
                options=dict(
                    content=(
                        "This Dashboard is managed by CloudMon. "
                        "All changes will be lost"
                    ),
                    mode="markdown",
                ),
            )
        )
        for panel in sorted(panel_defs, key=lambda k: k.get("order", 100)):
            logging.debug(f"Processing panel {panel}")
            panel.pop("order", None)
            panel["datasource"] = "cloudmon"
            panels.append(panel)
        return panels

    def provision_dashboard(self, dashboard_def, panels):
        logging.debug(
            f"Configuring Grafana dashboard {dashboard_def['title']}"
        )
        dashboard_uid = dashboard_def["uid"]
        folder_uid = dashboard_def.get("folderUid", "CloudMon")

        self.ensure_folder(uid=folder_uid, title="CloudMon")
        body = dict(
            folderUid=folder_uid,
            overwrite=True,
            message="Update Dashboard",
            dashboard=dict(
                uid=dashboard_uid,
                title=dashboard_def["title"],
                refresh="10s",
                templating=dict(
                    list=[
                        dict(
                            datasource="cloudmon",
                            definition="stats.counters.apimon.metric.*",
                            query="stats.counters.apimon.metric.*",
                            label="Environment",
                            name="environment",
                            regex="/^(?!swift)(.*)$/",
                            sort=1,
                            type="query",
                        ),
                        dict(
                            datasource="cloudmon",
                            definition="stats.counters.apimon.metric.*.*",
                            query="stats.counters.apimon.metric.*.*",
                            label="Monitoring Zone",
                            name="zone",
                            regex="/^(?!swift)(.*)$/",
                            sort=1,
                            multi=True,
                            includeAll=True,
                            type="query",
                        ),
                    ]
                ),
            ),
        )
        if "description" in dashboard_def:
            body["dashboard"]["description"] = dashboard_def["description"]
        panels = self._get_panels(panels)
        body["dashboard"]["panels"] = panels
        response = self.request(
            method="POST", url="/api/dashboards/db", json=body
        )
        if response.status_code != 200:
            raise RuntimeError(
                f"Error configuring dashboard {dashboard_uid} "
                f"in Grafana: {response.text}"
            )

    def provision_dashboards(self, config, check):
        logging.debug("Configuring Grafana dashboards")
        work_dir = "."

        dashboards_dir = Path(work_dir, "_dashboards")
        dashboards_dir.mkdir(parents=True, exist_ok=True)
        # Checkout all dashboard repos and merge results
        for repo in config.get("dashboards", {}):
            repo_dir = Path(work_dir, "git_repos", repo["name"])
            # utils.checkout_git_repository(repo_dir, repo)
            src = Path(repo_dir, repo.get("path", "dashboards/grafana"))
            if src.exists():
                shutil.copytree(
                    Path(repo_dir, repo.get("path", "dashboards/grafana")),
                    dashboards_dir,
                    dirs_exist_ok=True,
                )

        # Ensure target folder exists
        self.ensure_folder(uid="CloudMon", title="CloudMon")
        for dashboard_file in dashboards_dir.glob("**/dashboard.yaml"):
            logging.debug(f"Found Dashboard definition {dashboard_file}")
            with open(dashboard_file, "r") as f:
                dashboard_def = yaml.load(f, Loader=yaml.SafeLoader)
            dashboard_panels = []
            for panel_file in dashboard_file.parent.glob("*.yaml"):
                if panel_file.name == "dashboard.yaml":
                    continue
                logging.debug(f"Found Dashboard panel definition {panel_file}")
                with open(panel_file, "r") as f:
                    dashboard_panels.append(
                        yaml.load(f, Loader=yaml.SafeLoader)
                    )

            self.provision_dashboard(dashboard_def, dashboard_panels)
