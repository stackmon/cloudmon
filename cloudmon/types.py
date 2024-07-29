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
from typing import List
from typing import Literal
from typing import Union

from pydantic import BaseModel
from pydantic import ConfigDict
from pydantic import Field
from pydantic import RootModel


class CloudCredentialModel(BaseModel):
    """Cloud Credentials"""
    model_config = ConfigDict(extra='allow')

    name: str
    """Credential name (for reference)"""
    profile: str = None
    """Optional OpenStack profile to use with credentials"""
    auth: dict
    """Auth block (as in clouds.yaml)"""
    region_name: str = None
    """Optional OpenStack profile region name"""


class CloudCredentialsModel(RootModel):
    root: List[CloudCredentialModel]

    def get_by_name(self, name) -> CloudCredentialModel:
        for item in self.root:
            if item.name == name:
                return item

    def items(self):
        for item in self.root:
            yield (item.name, item)


class DatabaseUserModel(BaseModel):
    """Database user"""

    name: str
    """DB user name"""
    password: str
    """DB user password"""


class DatabaseInstanceModel(BaseModel):
    """Database instance"""

    name: str
    """DB name"""
    users: List[DatabaseUserModel]
    """DB users list"""


class DatabaseModel(BaseModel):
    """Database configuration"""

    postgres_postgres_password: str
    """Password of the postgres user (used to create Databases)"""
    ha_mode: bool = False
    """HighAvailability mode (based on Patroni, requires SSL certificates
    to be managed externally)"""
    databases: List[DatabaseInstanceModel]
    """Databases list"""


class EnvZoneCloudModel(BaseModel):
    """Environment Zone Cloud credentials entry"""

    name: str
    """Cloud name (clouds.yaml) to use while deploying"""
    ref: str
    """Reference to the cloud_credentials name to use"""


class EnvZoneCloudsModel(RootModel):
    root: List[EnvZoneCloudModel]

    def get_by_name(self, name) -> EnvZoneCloudModel:
        for item in self.root:
            if item.name == name:
                return item

    def items(self):
        for item in self.root:
            yield (item.name, item)


class EnvMonitoringZoneModel(BaseModel):
    """Configuration of the monitoring zone for certain environment"""

    name: str
    """Zone name"""
    clouds: List[EnvZoneCloudModel]
    """List of cloud credentials to be deployed"""


class EnvMonitoringZonesModel(RootModel):
    root: List[EnvMonitoringZoneModel]

    def items(self):
        for item in self.root:
            yield (item.name, item)


class EnvironmentModel(BaseModel):
    """Target environment to be tested"""

    name: str
    """Environment name"""
    env: dict
    """Environment variables to be set for this env"""
    monitoring_zones: EnvMonitoringZonesModel
    """Monitoring zones from which environment will be tested"""

    def get_zone_by_name(self, name) -> EnvMonitoringZoneModel:
        for item in self.monitoring_zones.root:
            if item.name == name:
                return item
        raise RuntimeError(
            "Monitoring zone %s for environment %s is not defined"
            % (name, self.name)
        )


class EnvironmentsModel(RootModel):
    root: List[EnvironmentModel]

    def items(self):
        for item in self.root:
            yield (item.name, item)


class GitRepoModel(BaseModel):
    """Git repository"""

    repo_url: str
    """Git repo url"""
    repo_ref: str = "main"
    """Git repo reference (branch)"""


class GrafanaDashboardRepoModel(GitRepoModel):
    """Grafana dashboard repository configuration"""

    name: str
    """Repository name"""
    path: str = "dashboards/grafana"
    """Path to the dashboards definitions inside the repository"""


class GrafanaModel(BaseModel):
    """Grafana configuration"""

    api_url: str = None
    """API url"""
    api_token: str = None
    """API token"""
    datasources: List[dict]
    """List of datasources to install into the Grafana instance"""
    k8_config: dict = None
    """Kubernetes configuration to use for deploying Grafana to K8"""
    config: dict
    """Configuration options to use for deploying on VMs"""
    dashboards: List[GrafanaDashboardRepoModel]
    """List of dashboards to be managed in the instance"""


class Kustomization(RootModel):
    """Basic Kustomization properties to use for overlay building"""

    root: dict


class MetricProcessorEnvironmentModel(BaseModel):
    """Metric Processor Environment configuration"""

    name: str
    """Environment name"""
    attributes: dict
    """Status Dashboard attributes linked to the environment"""


class MetricsProcessorModel(BaseModel):
    """Metrics Processor configuration"""

    name: str
    """Instance name"""
    kube_context: str
    """Kubernetes context to use for deployment"""
    kube_namespace: str
    """Kubernetes namespace name for deploy"""
    datasource_url: str
    """URL to the datasource (the one where graphite is deployed)"""
    datasource_type: str = "graphite"
    """Datasource type"""
    domain_name: str
    """FQDN"""
    environments: List[MetricProcessorEnvironmentModel]
    """Environments configuration"""
    kustomization: Kustomization
    """Kustomize overlay options"""
    status_dashboard_instance_name: str = None
    """Reference name of the associated Status Dashboard instance name"""


class MonitoringZoneModel(BaseModel):
    """Monitoring Zone"""

    name: str
    """Zone name"""

    graphite_group_name: str = "graphite"
    """ansible group name of the graphite hosts to use"""

    statsd_group_name: str = "statsd"
    """ansible group name of the statsd hosts to use"""


class MonitoringZonesModel(RootModel):
    root: List[MonitoringZoneModel]

    def get_by_name(self, name) -> MonitoringZoneModel:
        for item in self.root:
            if item.name == name:
                return item

    def items(self):
        for item in self.root:
            yield (item.name, item)


class PluginApimonModel(BaseModel):
    """ApiMon plugin configration"""

    name: str
    """Plugin name"""
    type: Literal["apimon"]
    scheduler_image: str
    """ApiMon scheduler image to use"""
    executor_image: str
    """Executor image to use"""
    tests_projects: List[dict]
    """List of git repositories with tests"""


class PluginApimonRefModel(BaseModel):
    """ApiMon plugin invocation"""

    name: str
    """plugin name (as used in the plugins section)"""
    schedulers_inventory_group_name: str = "schedulers"
    """ansible group name to deploy scheduler component"""
    executors_inventory_group_name: str = "executor"
    """ansible group name to deploy executors"""
    tests_project: str
    """Name of the project with tests (one from defined in
    the plugin configuration)"""
    tasks: List[str] = list()
    """Optional list of tasks (playbooks) to schedule"""


class PluginEpmonModel(BaseModel):
    """Endpoint Monitoring plugin"""

    name: str
    """plugin name"""
    type: Literal["epmon"]
    image: str
    """Epmon image to use"""
    config: str
    """Path to the epmon configuration elements
    (which service which endpoints)
    """


class PluginEpmonRefModel(BaseModel):
    """Epmon plugin invocation"""

    name: str
    """plugin name"""
    cloud_name: str = None
    """Cloud name to test in the environment"""
    config_elements: List[str] = list()
    """List of configuration entries of the epmon"""
    epmon_inventory_group_name: str = "epmons"
    """ansible group name to deploy epmon process"""


class PluginGlobalmonModel(BaseModel):
    """Endpoint Monitoring plugin"""

    name: str
    """plugin name"""
    type: Literal["globalmon"]
    image: str
    """Globalmon image to use"""
    config: str
    """Path to the globalmon configuration elements
    (which service which endpoints)
    """


class PluginGlobalmonRefModel(BaseModel):
    """Globalmon plugin invocation"""

    name: str
    """plugin name"""
    cloud_name: str = None
    """Cloud name to test in the environment"""
    globalmons_inventory_group_name: str = "globalmons"
    """ansible group name to deploy globalmon process"""

class PluginGeneralModel(BaseModel):
    """General plugin"""

    name: str
    """plugin name"""
    type: Literal["general"]
    init_image: str
    """Init image (this image is invoked to optionally initialize
    infrastructure for further testing) """


class PluginModel(RootModel):
    root: Union[
        PluginApimonModel, PluginEpmonModel, PluginGlobalmonModel, PluginGeneralModel
    ] = Field(..., discriminator="type")


class PluginRefModel(RootModel):
    root: Union[PluginApimonRefModel, PluginEpmonRefModel, PluginGlobalmonRefModel, PluginGeneralModel]


class StatusDashboardModel(BaseModel):
    """Status Dashboard configuration"""

    name: str
    """Instance name"""
    kube_context: str
    """Kubernetes context to use for deployment"""
    kube_namespace: str
    """Kubernetes namespace name for deploy"""
    api_secret: str = None
    """API secret"""
    domain_name: str
    """FQDN"""
    kustomization: Kustomization
    """Kustomize overlay options"""


class MatrixModel(BaseModel):
    """Testing Matrix entry"""

    env: str
    """Environment to test"""

    monitoring_zone: str
    """From which monitoring zone to test"""

    db_entry: str
    """Which DB to use for storing logs"""

    plugins: List[
        Union[PluginApimonRefModel, PluginEpmonRefModel, PluginGlobalmonRefModel, PluginGeneralModel]
    ]
    """Which plugins to use for testing"""


class ConfigModel(BaseModel):
    """CloudMon Config"""

    clouds_credentials: CloudCredentialsModel
    """Cloud Credentials section"""

    database: DatabaseModel
    """Databases configuration"""

    environments: EnvironmentsModel
    """Environments to be tested"""

    grafana: GrafanaModel = None
    """Grafana configuration"""

    matrix: List[MatrixModel]
    """Testing matrix (where to, from where and what)"""

    metrics_processor: List[MetricsProcessorModel] = []

    monitoring_zones: MonitoringZonesModel
    """Monitoring zones from which to test"""

    plugins: List[PluginModel]
    """Registered plugins to enable for testing"""

    status_dashboard: List[StatusDashboardModel] = []
    """Status dashboard configuration"""

    def get_env_by_name(self, name) -> EnvironmentModel:
        for item in self.environments.root:
            if item.name == name:
                return item
        raise ValueError("Environment %s is not defined" % (name))

    def get_cloud_creds_by_name(self, name) -> CloudCredentialModel:
        for item in self.clouds_credentials.root:
            if item.name == name:
                return item
        raise ValueError("Cloud %s is not defined" % (name))

    def get_monitoring_zone_by_name(self, name) -> MonitoringZoneModel:
        for item in self.monitoring_zones.root:
            if item.name == name:
                return item
        raise ValueError("Monitoring Zone %s is not defined" % (name))

    def get_plugin_by_name(self, name) -> dict:
        for item in self.plugins:
            if item.root.name == name:
                return item.root
        raise ValueError("Plugin %s is not defined" % (name))

    def get_sdb_by_name(self, name) -> dict:
        for item in self.status_dashboard:
            if item.name == name:
                return item
        raise ValueError("Status dashboard %s is not defined" % (name))
