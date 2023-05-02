# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

"""
test_apimon
----------------------------------

Tests for `cloudmon.plugins.apimon` module.
"""
from unittest import mock

from cloudmon.tests.unit import base

from cloudmon.plugin import apimon


class TestApimon(base.TestCase):
    cfg1 = """
      clouds_credentials:
        - name: c1
          profile: b1
          auth:
            x: y1
        - name: c2
          profile: b2
          auth:
            x: y2
        - name: x1
          profile: _b
          auth:
            x: _y
      database:
        postgres_postgres_password: abc
        databases:
          - name: d1
            users:
              - name: d1u1
                password: d1u1p
      environments:
        - name: e1
          env:
            OS_CLOUD: 1
          monitoring_zones:
            - name: zone1
              clouds:
                - name: e1
                  ref: c1
                - name: x
                  ref: x1
        - name: e2
          env:
            OS_CLOUD: 1
          monitoring_zones:
            - name: zone2
              clouds:
                - name: e1
                  ref: c1
                - name: x
                  ref: x1
      monitoring_zones:
        - name: zone1
          graphite_group_name: g1
          statsd_group_name: g2
        - name: zone2
          graphite_group_name: g3
          statsd_group_name: g4
      plugins:
        - name: epmon
          type: epmon
          image: epmon_image
          config: config_epmon.yaml
        - name: apimon
          type: apimon
          scheduler_image: scheduler_image
          executor_image: executor_image
          tests_projects:
            - name: apimon_project
              repo_url: apimon_repo_url
              scenarios_location: playbooks
      matrix:
        - env: e1
          monitoring_zone: zone1
          db_entry: d1.d1u1
          plugins:
            - name: apimon
              schedulers_inventory_group_name: g1
              executors_inventory_group_name: g1
              tests_project: apimon_project
        - env: e2
          monitoring_zone: zone2
          db_entry: d1.d1u1
          plugins:
            - name: apimon
              schedulers_inventory_group_name: g2
              executors_inventory_group_name: g2
              tests_project: apimon_project
    """
    inventory = """
      all:
        hosts:
          h1:
            internal_address: 1
          h2:
            internal_address: 2
          h3:
            internal_address: 3
          h4:
            internal_address: 4
        children:
          g1:
            hosts:
              h1:
          g2:
            hosts:
              h2:
          g3:
            hosts:
              h3:
          g4:
            hosts:
              h4:
    """

    class Opts:
        component: str

        def __init__(self):
            self.component = None

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_stop(self, runner_mock):
        config = self.get_config(self.cfg1, self.inventory)
        manager = apimon.ApiMonManager(config)

        manager.stop(self.Opts())
        calls = [
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="stop_executors.yaml",
                inventory=mock.ANY,
                extravars={"executors_group_name": "g1"},
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="stop_schedulers.yaml",
                inventory=mock.ANY,
                extravars={"schedulers_group_name": "g1"},
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="stop_executors.yaml",
                inventory=mock.ANY,
                extravars={"executors_group_name": "g2"},
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="stop_schedulers.yaml",
                inventory=mock.ANY,
                extravars={"schedulers_group_name": "g2"},
                verbosity=1,
            ),
        ]
        runner_mock.assert_has_calls(calls)

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_start(self, runner_mock):
        config = self.get_config(self.cfg1, self.inventory)
        manager = apimon.ApiMonManager(config)

        manager.start(self.Opts())
        calls = [
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="start_executors.yaml",
                inventory=mock.ANY,
                extravars={"executors_group_name": "g1"},
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="start_schedulers.yaml",
                inventory=mock.ANY,
                extravars={"schedulers_group_name": "g1"},
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="start_executors.yaml",
                inventory=mock.ANY,
                extravars={"executors_group_name": "g2"},
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="start_schedulers.yaml",
                inventory=mock.ANY,
                extravars={"schedulers_group_name": "g2"},
                verbosity=1,
            ),
        ]
        runner_mock.assert_has_calls(calls)

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_provision(self, runner_mock):
        config = self.get_config(self.cfg1, self.inventory)
        manager = apimon.ApiMonManager(config)

        manager.provision(self.Opts())
        calls = [
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="install_scheduler.yaml",
                inventory=mock.ANY,
                extravars={
                    "scheduler_config_dir": "/etc/cloudmon",
                    "scheduler_config_file_name": "apimon-scheduler.yaml",
                    "scheduler_secure_config_file_name": (
                        "apimon-scheduler-secure.yaml"
                    ),
                    "schedulers_group_name": "g1",
                    "scheduler_image": "scheduler_image",
                    "scheduler_config": {
                        "secure": "/etc/apimon/apimon-scheduler-secure.yaml",
                        "gear": [
                            {"host": "0.0.0.0", "port": 4730, "start": True}
                        ],
                        "log": {"config": "/etc/apimon/logging.conf"},
                        "metrics": {"statsd": {"host": 1, "port": 8125}},
                        "scheduler": {
                            "socket": "/tmp/scheduler.socket",
                            "refresh_interval": 10,
                            "work_dir": "/var/lib/apimon",
                            "zone": "zone1",
                        },
                        "test_environments": [
                            {
                                "name": "e1",
                                "env": {"OS_CLOUD": 1},
                                "clouds": ["e1", "x"],
                            }
                        ],
                        "test_projects": [
                            {
                                "name": "apimon_project",
                                "repo_url": "apimon_repo_url",
                                "scenarios_location": "playbooks",
                            }
                        ],
                        "test_matrix": [
                            {
                                "env": "e1",
                                "project": "apimon_project",
                                "tasks": [],
                            }
                        ],
                    },
                    "scheduler_secure_config": {
                        "clouds": [
                            {
                                "name": "e1",
                                "data": {"profile": "b1", "auth": {"x": "y1"}},
                            },
                            {
                                "name": "x",
                                "data": {"profile": "_b", "auth": {"x": "_y"}},
                            },
                        ]
                    },
                },
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="install_scheduler.yaml",
                inventory=mock.ANY,
                extravars={
                    "scheduler_config_dir": "/etc/cloudmon",
                    "scheduler_config_file_name": "apimon-scheduler.yaml",
                    "scheduler_secure_config_file_name": (
                        "apimon-scheduler-secure.yaml"
                    ),
                    "schedulers_group_name": "g2",
                    "scheduler_image": "scheduler_image",
                    "scheduler_config": {
                        "secure": "/etc/apimon/apimon-scheduler-secure.yaml",
                        "gear": [
                            {"host": "0.0.0.0", "port": 4730, "start": True}
                        ],
                        "log": {"config": "/etc/apimon/logging.conf"},
                        "metrics": {"statsd": {"host": 2, "port": 8125}},
                        "scheduler": {
                            "socket": "/tmp/scheduler.socket",
                            "refresh_interval": 10,
                            "work_dir": "/var/lib/apimon",
                            "zone": "zone2",
                        },
                        "test_environments": [
                            {
                                "name": "e2",
                                "env": {"OS_CLOUD": 1},
                                "clouds": ["e1", "x"],
                            }
                        ],
                        "test_projects": [
                            {
                                "name": "apimon_project",
                                "repo_url": "apimon_repo_url",
                                "scenarios_location": "playbooks",
                            }
                        ],
                        "test_matrix": [
                            {
                                "env": "e2",
                                "project": "apimon_project",
                                "tasks": [],
                            }
                        ],
                    },
                    "scheduler_secure_config": {
                        "clouds": [
                            {
                                "name": "e1",
                                "data": {"profile": "b1", "auth": {"x": "y1"}},
                            },
                            {
                                "name": "x",
                                "data": {"profile": "_b", "auth": {"x": "_y"}},
                            },
                        ]
                    },
                },
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="install_executor.yaml",
                inventory=mock.ANY,
                extravars={
                    "executor_config_dir": "/etc/cloudmon",
                    "executor_config_file_name": "apimon-executor.yaml",
                    "executor_secure_config_file_name": (
                        "apimon-executor-secure.yaml"
                    ),
                    "executors_group_name": "g1",
                    "executor_image": "executor_image",
                    "executor_config": {
                        "secure": "/etc/apimon/apimon-executor-secure.yaml",
                        "gear": [{"host": 1, "port": 4730}],
                        "log": {"config": "/etc/apimon/logging.conf"},
                        "metrics": {"statsd": {"host": 1, "port": 8125}},
                        "executor": {
                            "load_multiplier": 2,
                            "socket": "/tmp/executor.socket",
                            "work_dir": "/var/lib/apimon",
                            "zone": "zone1",
                            "logs_cloud": "swift",
                        },
                    },
                    "executor_secure_config": {"executor": {}},
                },
                verbosity=1,
            ),
            mock.call(
                private_data_dir=mock.ANY,
                artifact_dir=".cloudmon_artifact",
                project_dir=config.project_dir.as_posix(),
                playbook="install_executor.yaml",
                inventory=mock.ANY,
                extravars={
                    "executor_config_dir": "/etc/cloudmon",
                    "executor_config_file_name": "apimon-executor.yaml",
                    "executor_secure_config_file_name": (
                        "apimon-executor-secure.yaml"
                    ),
                    "executors_group_name": "g2",
                    "executor_image": "executor_image",
                    "executor_config": {
                        "secure": "/etc/apimon/apimon-executor-secure.yaml",
                        "gear": [{"host": 2, "port": 4730}],
                        "log": {"config": "/etc/apimon/logging.conf"},
                        "metrics": {"statsd": {"host": 2, "port": 8125}},
                        "executor": {
                            "load_multiplier": 2,
                            "socket": "/tmp/executor.socket",
                            "work_dir": "/var/lib/apimon",
                            "zone": "zone2",
                            "logs_cloud": "swift",
                        },
                    },
                    "executor_secure_config": {"executor": {}},
                },
                verbosity=1,
            ),
        ]
        runner_mock.assert_has_calls(calls)
