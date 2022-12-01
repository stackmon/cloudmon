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

import copy
import logging
from pathlib import Path
import shutil
import yaml

import requests
from urllib.parse import urljoin

import ansible_runner

from cloudmon import utils


class GrafanaSession(requests.Session):
    def __init__(self, base_url=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.base_url = base_url


class GrafanaManager:
    log = logging.getLogger(__name__)

    def __init__(self, cloudmon_config, api_url, api_token):
        self.config = cloudmon_config
        self.base_url = api_url
        self._prepare_session(api_url, api_token)

    def _prepare_session(self, api_url, api_token):
        self.base_url = api_url
        self._session = GrafanaSession(base_url=api_url)
        self._session.headers.update({"Authorization": f"Bearer {api_token}"})

    def request(self, method, url, *args, **kwargs):
        if not url.startswith("http"):
            url = urljoin(self.base_url, url)
        return self._session.request(method, url, *args, **kwargs)

    def ensure_folder(self, uid, title, **kwargs):
        logging.debug("Verifying Grafana folder existence")
        response = self.request(method="GET", url=f"/api/folders/{uid}")
        if response.status_code == 404:
            response = self.request(
                method="POST",
                url="/api/folders",
                json=dict(uid=uid, title=title, **kwargs),
            )
        if response.status_code != 200:
            raise RuntimeError(
                "Error creating folder %s: %s" % (title, response.text)
            )
        folder = response.json()

        return folder

    def provision_ds(self, options):
        self.log.debug("Configuring Grafana datasources")
        grafana_config = self.config.model.grafana
        for ds in grafana_config.datasources:
            self.log.debug("Configuring DS %s" % ds["name"])
            port = ds.pop("port", None)
            ds_body = dict(
                access="proxy",
                name=ds["name"],
                type=ds["type"],
            )
            ds_body.update(ds)
            if "url" not in ds:
                # Warning: ds_type is used as group name - beware
                host = self.config.inventory[ds["type"]]["hosts"][0]
                host_vars = self.config.hostvars(host)
                host_ip = host_vars.get(
                    "internal_address", host_vars.get("ansible_host", host)
                )
                ds_body["url"] = host_ip
                if port:
                    ds_body["url"] += f":{port}"

            response = self.request(
                method="GET", url=f"/api/datasources/name/{ds['name']}"
            )

            if response.status_code == 200:
                # Update DS
                response = self.request(
                    method="PUT",
                    url=f"/api/datasources/{response.json()['id']}",
                    json=ds_body,
                )
            elif response.status_code == 404:
                # Create DS
                response = self.request(
                    method="POST", url="/api/datasources", json=ds_body
                )
            else:
                raise RuntimeError(
                    f"Error checking datasources in Grafana: {response.text}"
                )

            if response.status_code != 200:
                raise RuntimeError(
                    "Error configuring datasources in Grafana: "
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
            self.log.debug(f"Processing panel {panel}")
            panel.pop("order", None)
            if "datasource" not in panel:
                panel["datasource"] = "cloudmon"
            panels.append(panel)
        return panels

    def provision_dashboard(self, dashboard_def, panels):
        self.log.debug(
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
                            definition="stats.counters.openstack.api.*",
                            query="stats.counters.openstack.api.*",
                            label="Environment",
                            name="environment",
                            regex="/^(?!swift)(.*)$/",
                            sort=1,
                            type="query",
                        ),
                        dict(
                            datasource="cloudmon",
                            definition="stats.counters.openstack.api.*.*",
                            query="stats.counters.openstack.api.*.*",
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

    def provision_dashboards(self, options):
        self.log.debug("Configuring Grafana dashboards")
        grafana_config = self.config.model.grafana
        work_dir = "."

        dashboards_dir = Path(work_dir, "_dashboards")
        dashboards_dir.mkdir(parents=True, exist_ok=True)
        # Checkout all dashboard repos and merge results
        for repo in grafana_config.dashboards:
            repo_dir = Path(work_dir, "git_repos", repo.name)
            utils.checkout_git_repository(repo_dir, repo)
            src = Path(repo_dir, repo.path)
            if src.exists():
                shutil.copytree(
                    Path(repo_dir, repo.path),
                    dashboards_dir,
                    dirs_exist_ok=True,
                )

        # Ensure target folder exists
        self.ensure_folder(uid="CloudMon", title="CloudMon")
        for dashboard_file in dashboards_dir.glob("**/dashboard.yaml"):
            self.log.debug(f"Found Dashboard definition {dashboard_file}")
            with open(dashboard_file, "r") as f:
                dashboard_def = yaml.load(f, Loader=yaml.SafeLoader)
            dashboard_panels = []
            for panel_file in dashboard_file.parent.glob("*.yaml"):
                if panel_file.name == "dashboard.yaml":
                    continue
                self.log.debug(
                    f"Found Dashboard panel definition {panel_file}"
                )
                with open(panel_file, "r") as f:
                    dashboard_panels.append(
                        yaml.load(f, Loader=yaml.SafeLoader)
                    )

            self.provision_dashboard(dashboard_def, dashboard_panels)

    def provision(self, options):
        grafana_config = self.config.model.grafana
        if grafana_config.k8_config:
            # Deploy Grafana into K8
            logging.debug("Installing Grafana into K8")
            raise NotImplementedError

        else:
            # Deploy Grafana onto VMs
            logging.debug("Installing Grafana into VMs")
            extravars = copy.deepcopy(self.config.default_extravars)
            # For now group_name is hardcoded to grafana
            extravars["grafana_group_name"] = "grafana"
            extravars.update(grafana_config.get("config", {}))
            if "grafana_database_host" not in extravars:
                db_host = self.config.inventory["postgres"]["hosts"][0]
                db_host_vars = self.config.hostvars(db_host)
                db_port = None
                if self.config.model.database.ha_mode:
                    db_port = "5000"
                extravars["grafana_database_host"] = db_host_vars.get(
                    "internal_address",
                    db_host_vars.get("ansible_address", db_host),
                )
                if db_port:
                    extravars["grafana_database_host"] += ":" + db_port

            r = ansible_runner.run(
                private_data_dir=self.config.private_data_dir,
                project_dir=self.config.project_dir.as_posix(),
                artifact_dir=".cloudmon_artifact",
                playbook="install_grafana.yaml",
                inventory=self.config.inventory_path,
                extravars=extravars,
                verbosity=2,
            )
            if r.rc != 0:
                raise RuntimeError("Error provisioning Grafana")

        if "api_token" not in grafana_config:
            self.generate_api_token()

    def generate_api_token(self):
        grafana_config = self.config.config["grafana"]
        grafana_host = self.config.inventory["grafana"]["hosts"][0]
        grafana_host_vars = self.config.hostvars(grafana_host)
        grafana_ip = grafana_host_vars.get("ansible_host", grafana_host)
        api_url = f"http://{grafana_ip}:3000"

        self.log.debug(
            "Grafana host %s",
            self.config.hostvars(grafana_host),
        )
        auth = requests.auth.HTTPBasicAuth(
            "admin",
            grafana_config["config"].get(
                "grafana_security_admin_password", "admin"
            ),
        )
        response = requests.get(
            f"{api_url}/api/serviceaccounts/search?query=stackmon", auth=auth
        )
        cloudmon_sa = None
        if response.status_code == 200:
            data = response.json()
            if len(data["serviceAccounts"]) == 1:
                # If we have more then one result we do not want to guess
                cloudmon_sa = data["serviceAccounts"][0]
        if not cloudmon_sa:
            response = requests.post(
                f"{api_url}/api/serviceaccounts",
                json=dict(name="stackmon", role="Admin", is_disabled=False),
                auth=auth,
            )
            if response.status_code != 201:
                raise RuntimeError(
                    f"Error generating Grafana ServiceAccount: {response.text}"
                )
            cloudmon_sa = response.json()

        response = requests.post(
            f"{api_url}/api/serviceaccounts/{cloudmon_sa['id']}/tokens",
            json=dict(name="stackmon", role="Admin", is_disabled=False),
            auth=auth,
        )
        if response.status_code != 200:
            raise RuntimeError(
                "Error generating Grafana SA Token: "
                f"{response.text}. Please drop the token manually and rerun "
                "or add grafna.api_token to the config directly"
            )
        api_token = response.json()["key"]
        self.config.config["grafana"]["api_url"] = api_url
        self.config.config["grafana"]["api_token"] = api_token
        self._prepare_session(api_url, api_token)
        self.config.is_updated = True
