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


class Kustomization(BaseModel):
    __root__: dict


class MonitoringZoneModel(BaseModel):
    name: str
    graphite_group_name: str = "graphite"
    statsd_group_name: str = "statsd"


class MonitoringZonesModel(BaseModel):
    __root__: List[MonitoringZoneModel]

    def get_by_name(self, name) -> MonitoringZoneModel:
        for item in self.__root__:
            if item.name == name:
                return item

    def items(self):
        for item in self.__root__:
            yield (item.name, item)


class DatabaseUserModel(BaseModel):
    name: str
    password: str


class DatabaseInstanceModel(BaseModel):
    name: str
    users: List[DatabaseUserModel]


class DatabaseModel(BaseModel):
    postgres_postgres_password: str
    ha_mode: bool = False
    databases: List[DatabaseInstanceModel]


class StatusDashboardModel(BaseModel):
    name: str
    kube_context: str
    kube_namespace: str
    domain_name: str
    kustomization: Kustomization


class StatusDashboardsModel(BaseModel):
    __root__: List[StatusDashboardModel]


class CloudCredentialModel(BaseModel):
    name: str
    profile: str = None
    auth: dict


class CloudCredentialsModel(BaseModel):
    __root__: List[CloudCredentialModel]

    def get_by_name(self, name) -> CloudCredentialModel:
        for item in self.__root__:
            if item.name == name:
                return item

    def items(self):
        for item in self.__root__:
            yield (item.name, item)


class EnvZoneCloudModel(BaseModel):
    name: str
    ref: str


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
    name: str
    clouds: List[EnvZoneCloudModel]


class EnvMonitoringZonesModel(BaseModel):
    __root__: List[EnvMonitoringZoneModel]

    def items(self):
        for item in self.__root__:
            yield (item.name, item)


class EnvironmentModel(BaseModel):
    name: str
    env: dict
    monitoring_zones: EnvMonitoringZonesModel

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
    repo_url: str
    repo_ref: str = "main"


class GrafanaDashboardRepoModel(GitRepoModel):
    name: str
    path: str = "dashboards/grafana"


class GrafanaModel(BaseModel):
    api_url: str = None
    api_token: str = None
    datasources: List[dict]
    k8_config: dict = None
    config: dict
    dashboards: List[GrafanaDashboardRepoModel]


class PluginApimonModel(BaseModel):
    name: str
    type: Literal["apimon"]
    scheduler_image: str
    executor_image: str
    tests_projects: List[dict]


class PluginApimonRefModel(BaseModel):
    name: str
    schedulers_inventory_group_name: str = "schedulers"
    executors_inventory_group_name: str = "executor"
    tests_project: str
    tasks: List[str] = list()


class PluginEpmonModel(BaseModel):
    name: str
    type: Literal["epmon"]
    image: str
    config: str
    # cloud_name: str = None
    # config_elements: List[str] = list()


class PluginEpmonRefModel(BaseModel):
    name: str
    cloud_name: str = None
    config_elements: List[str] = list()
    epmon_inventory_group_name: str = "epmons"


class PluginGeneralModel(BaseModel):
    name: str
    type: Literal["general"]
    init_image: str


class PluginModel(BaseModel):
    __root__: Union[
        PluginApimonModel, PluginEpmonModel, PluginGeneralModel
    ] = Field(..., discriminator="type")


class PluginRefModel(BaseModel):
    __root__: Union[
        PluginApimonRefModel, PluginEpmonRefModel, PluginGeneralModel
    ]


class MatrixModel(BaseModel):
    env: str
    monitoring_zone: str
    db_entry: str
    plugins: List[
        Union[PluginApimonRefModel, PluginEpmonRefModel, PluginGeneralModel]
    ]


class ConfigModel(BaseModel):
    clouds_credentials: CloudCredentialsModel
    database: DatabaseModel
    environments: EnvironmentsModel
    grafana: GrafanaModel = None
    matrix: List[MatrixModel]
    monitoring_zones: MonitoringZonesModel
    plugins: List[PluginModel]
    status_dashboard: StatusDashboardsModel = None

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
