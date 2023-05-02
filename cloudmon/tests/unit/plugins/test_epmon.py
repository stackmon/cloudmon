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
test_epmon
----------------------------------

Tests for `cloudmon.plugins.epmon` module.
"""
from unittest import mock

from cloudmon.tests.unit import base

from cloudmon.plugin import epmon


class TestEpmon(base.TestCase):
    epmon_cfg = """
      elements:
        ee1:
          service_type: foo
          urls:
            - /
            - /bar
        ee2:
          service_type: foo2
          urls:
            - /
            - /bar2
    """
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
      matrix:
        - env: e1
          monitoring_zone: zone1
          db_entry: d1.d1u1
          plugins:
            - name: epmon
              epmon_inventory_group_name: g1
              cloud_name: e1
        - env: e2
          monitoring_zone: zone2
          db_entry: d1.d1u1
          plugins:
            - name: epmon
              epmon_inventory_group_name: g1
              cloud_name: e1
              config_elements: ["ee1"]
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

    def test_process_config(self):
        config = self.get_config(self.cfg1)
        manager = None
        # mock reading of epmon config
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=self.epmon_cfg)
        ):
            manager = epmon.EpmonManager(config)
        expected_config1 = epmon.EpmonConfig()
        expected_config1.zone = "zone1"
        expected_config1.image = "epmon_image"
        expected_config1.ansible_group_name = "g1"
        expected_config1.environment = "e1"
        expected_config1.watch_clouds = dict(e1=dict(services={}, cloud="e1"))
        expected_config2 = epmon.EpmonConfig()
        expected_config2.zone = "zone2"
        expected_config2.image = "epmon_image"
        expected_config2.ansible_group_name = "g1"
        expected_config2.environment = "e2"
        expected_config2.watch_clouds = dict(
            e2=dict(services={"foo": {"urls": ["/", "/bar"]}}, cloud="e1")
        )
        self.assertDictEqual(
            vars(expected_config1), vars(manager.epmon_configs["zone1"])
        )
        self.assertDictEqual(
            vars(expected_config2), vars(manager.epmon_configs["zone2"])
        )

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_stop(self, runner_mock):
        config = self.get_config(self.cfg1)
        # mock reading of epmon config
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=self.epmon_cfg)
        ):
            manager = epmon.EpmonManager(config)

        manager.stop(None)
        runner_mock.assert_called_with(
            private_data_dir=mock.ANY,
            artifact_dir=".cloudmon_artifact",
            project_dir=config.project_dir.as_posix(),
            playbook="stop_epmon.yaml",
            inventory=None,
            extravars={"epmons_group_name": "g1"},
            verbosity=1,
        )

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_start(self, runner_mock):
        config = self.get_config(self.cfg1)
        # mock reading of epmon config
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=self.epmon_cfg)
        ):
            manager = epmon.EpmonManager(config)

        manager.start(None)
        runner_mock.assert_called_with(
            private_data_dir=mock.ANY,
            artifact_dir=".cloudmon_artifact",
            project_dir=config.project_dir.as_posix(),
            playbook="start_epmon.yaml",
            inventory=None,
            extravars={"epmons_group_name": "g1"},
            verbosity=1,
        )

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_provision(self, runner_mock):
        config = self.get_config(self.cfg1, self.inventory)
        # mock reading of epmon config
        with mock.patch(
            "builtins.open", mock.mock_open(read_data=self.epmon_cfg)
        ):
            manager = epmon.EpmonManager(config)

        manager.provision(None)
        runner_mock.assert_called_with(
            private_data_dir=mock.ANY,
            artifact_dir=".cloudmon_artifact",
            project_dir=config.project_dir.as_posix(),
            playbook="install_epmon.yaml",
            inventory=mock.ANY,
            extravars={
                "epmons_group_name": "g1",
                "epmon_image": "epmon_image",
                "epmon_config_dir": "/etc/cloudmon",
                "epmon_secure_config_file_name": "epmon-secure.yaml",
                "epmon_config": {
                    "epmon": {
                        "clouds": [
                            {
                                "e2": {
                                    "service_override": {
                                        "foo": {"urls": ["/", "/bar"]}
                                    }
                                }
                            }
                        ],
                        "socket": "/tmp/epmon.socket",
                        "zone": "zone2",
                    },
                    "log": {"config": "/etc/apimon/logging.conf"},
                    "metrics": {"statsd": {"host": 4, "port": 8125}},
                    "secure": "/etc/apimon/epmon-secure.yaml",
                },
                "epmon_secure_config": {
                    "clouds": [
                        {
                            "name": "e1",
                            "data": {"profile": "b1", "auth": {"x": "y1"}},
                        }
                    ]
                },
            },
            verbosity=3,
        )
