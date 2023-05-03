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
from pydantic import Field


class CloudCredentialModel(BaseModel):
    """Cloud Credentials"""

    name: str
    """Credential name (for reference)"""
    profile: str = None
    """Optional OpenStack profile to use with credentials"""
    auth: dict
    """Auth block (as in clouds.yaml)"""


class CloudCredentialsModel(BaseModel):
    __root__: List[CloudCredentialModel]

    def get_by_name(self, name) -> CloudCredentialModel:
        for item in self.__root__:
            if item.name == name:
                return item

    def items(self):
        for item in self.__root__:
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


class EnvZoneCloudsModel(BaseModel):
    __root__: List[EnvZoneCloudModel]

    def get_by_name(self, name) -> EnvZoneCloudModel:
        for item in self.__root__:
            if item.name == name:
                return item

    def items(self):
        for item in self.__root__:
            yield (item.name, item)


class EnvMonitoringZoneModel(BaseModel):
    """Configuration of the monitoring zone for certain environment"""

    name: str
    """Zone name"""
    clouds: List[EnvZoneCloudModel]
    """List of cloud credentials to be deployed"""


class EnvMonitoringZonesModel(BaseModel):
    __root__: List[EnvMonitoringZoneModel]

    def items(self):
        for item in self.__root__:
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
        for item in self.monitoring_zones.__root__:
            if item.name == name:
                return item
        raise RuntimeError(
            "Monitoring zone %s for environment %s is not defined"
            % (name, self.name)
        )


class EnvironmentsModel(BaseModel):
    __root__: List[EnvironmentModel]

    def items(self):
        for item in self.__root__:
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


class Kustomization(BaseModel):
    """Basic Kustomization properties to use for overlay building"""

    __root__: dict


class MetricsProcessorModel(BaseModel):
    """Metrics Processor configuration"""

    name: str
    """Instance name"""
    kube_context: str
    """Kubernetes context to use for deployment"""
    kube_namespace: str
    """Kubernetes namespace name for deploy"""
    domain_name: str
    """FQDN"""
    kustomization: Kustomization
    """Kustomize overlay options"""


class MetricsProcessorsModel(BaseModel):
    """Metrics Processor list"""

    __root__: List[MetricsProcessorModel]


class MonitoringZoneModel(BaseModel):
    """Monitoring Zone"""

    name: str
    """Zone name"""

    graphite_group_name: str = "graphite"
    """ansible group name of the graphite hosts to use"""

    statsd_group_name: str = "statsd"
    """ansible group name of the statsd hosts to use"""


class MonitoringZonesModel(BaseModel):
    __root__: List[MonitoringZoneModel]

    def get_by_name(self, name) -> MonitoringZoneModel:
        for item in self.__root__:
            if item.name == name:
                return item

    def items(self):
        for item in self.__root__:
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


class PluginGeneralModel(BaseModel):
    """General plugin"""

    name: str
    """plugin name"""
    type: Literal["general"]
    init_image: str
    """Init image (this image is invoked to optionally initialize infrastructure
    for further testing)
    """


class PluginModel(BaseModel):
    __root__: Union[
        PluginApimonModel, PluginEpmonModel, PluginGeneralModel
    ] = Field(..., discriminator="type")


class PluginRefModel(BaseModel):
    __root__: Union[
        PluginApimonRefModel, PluginEpmonRefModel, PluginGeneralModel
    ]


class StatusDashboardModel(BaseModel):
    """Status Dashboard configuration"""

    name: str
    """Instance name"""
    kube_context: str
    """Kubernetes context to use for deployment"""
    kube_namespace: str
    """Kubernetes namespace name for deploy"""
    domain_name: str
    """FQDN"""
    kustomization: Kustomization
    """Kustomize overlay options"""


class StatusDashboardsModel(BaseModel):
    __root__: List[StatusDashboardModel]


class MatrixModel(BaseModel):
    """Testing Matrix entry"""

    env: str
    """Environment to test"""

    monitoring_zone: str
    """From which monitoring zone to test"""

    db_entry: str
    """Which DB to use for storing logs"""

    plugins: List[
        Union[PluginApimonRefModel, PluginEpmonRefModel, PluginGeneralModel]
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

    metrics_processor: MetricsProcessorsModel = None

    monitoring_zones: MonitoringZonesModel
    """Monitoring zones from which to test"""

    plugins: List[PluginModel]
    """Registered plugins to enable for testing"""

    status_dashboard: StatusDashboardsModel = None
    """Status dashboard configuration"""

    def get_env_by_name(self, name) -> EnvironmentModel:
        for item in self.environments.__root__:
            if item.name == name:
                return item
        raise ValueError("Environment %s is not defined" % (name))

    def get_cloud_creds_by_name(self, name) -> CloudCredentialModel:
        for item in self.clouds_credentials.__root__:
            if item.name == name:
                return item
        raise ValueError("Cloud %s is not defined" % (name))

    def get_monitoring_zone_by_name(self, name) -> MonitoringZoneModel:
        for item in self.monitoring_zones.__root__:
            if item.name == name:
                return item
        raise ValueError("Monitoring Zone %s is not defined" % (name))

    def get_plugin_by_name(self, name) -> dict:
        for item in self.plugins:
            if item.__root__.name == name:
                return item.__root__
        raise ValueError("Plugin %s is not defined" % (name))
