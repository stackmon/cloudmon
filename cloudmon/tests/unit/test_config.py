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
test_config
----------------------------------

Tests for `cloudmon.config` module.
"""
from pathlib import Path
import tempfile

from cloudmon.tests.unit import base

from cloudmon.config import CloudMonConfig


class TestConfig(base.TestCase):
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
          region_name: _r
          foo: bar
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
            - name: z1
              clouds:
                - name: e1
                  ref: c1
                - name: x
                  ref: x1
      matrix: []
      monitoring_zones:
        - name: zone1
          graphite_group_name: g1
          statsd_group_name: g2
        - name: zone2
          graphite_group_name: g3
          statsd_group_name: g4
      plugins: []
    """
    cfg2_part1 = """
      clouds_credentials:
        - name: c1
          profile: b1
        - name: c2
          profile: b2
          region_name: r2
      database:
        databases:
          - name: d1
            users:
              - name: d1u1
      environments:
        - name: e1
          env:
            OS_CLOUD: 1
          monitoring_zones:
            - name: z1
              clouds:
                - name: e1
                  ref: c1
                - name: x
                  ref: x1
      matrix: []
      monitoring_zones:
        - name: zone1
          graphite_group_name: g1
          statsd_group_name: g2
        - name: zone2
          graphite_group_name: g3
          statsd_group_name: g4
      plugins: []
    """
    cfg2_part2 = """
      clouds_credentials:
        - name: c1
          profile: xb1
          auth:
            x: y1
        - name: c2
          auth:
            x: y2
      database:
        postgres_postgres_password: abc
        databases:
          - name: d1
            users:
              - name: d1u1
                password: d1u1p
    """

    def test_config_get_env_clouds_credentials(self):
        config = self.get_config(self.cfg1)
        self.assertDictEqual(
            config.get_env_clouds_credentials(
                "e1",
                "z1",
            ),
            {
                "e1": {
                    "name": "e1",
                    "data": {"profile": "b1", "auth": {"x": "y1"}},
                },
                "x": {
                    "name": "x",
                    "data": {
                        "profile": "_b",
                        "auth": {"x": "_y"},
                        "region_name": "_r",
                        "foo": "bar",
                    },
                },
            },
        )

    def test_config_get_env_cloud_credentials(self):
        config = self.get_config(self.cfg1)
        self.assertDictEqual(
            config.get_env_cloud_credentials("e1", "z1", "x"),
            {
                "name": "x",
                "data": {
                    "profile": "_b",
                    "auth": {"x": "_y"},
                    "region_name": "_r",
                    "foo": "bar",
                },
            },
        )

    def test_hostvars(self):
        config = self.get_config(self.cfg1)
        config.inventory = dict(_meta=dict(hostvars=dict(h1=dict(foo="bar"))))
        self.assertDictEqual({"h1": {"foo": "bar"}}, config.hostvars())
        self.assertDictEqual({"foo": "bar"}, config.hostvars("h1"))

    def test_monitoring_zone_not_defined(self):
        config = self.get_config(self.cfg1)
        self.assertRaises(
            ValueError, config.model.get_monitoring_zone_by_name, "z1"
        )

    def test_get_statsd_zone_address(self):
        config = self.get_config(self.cfg1)
        config.inventory = dict(
            _meta=dict(
                hostvars=dict(
                    h1=dict(
                        internal_address="1.2.3.4", ansible_host="2.3.4.5"
                    ),
                    h2=dict(ansible_host="3.4.5.6"),
                )
            ),
            g2=dict(hosts=["h1"]),
            g4=dict(hosts=["h2"]),
        )
        self.assertEqual("1.2.3.4", config.get_statsd_zone_address("zone1"))
        self.assertEqual("3.4.5.6", config.get_statsd_zone_address("zone2"))

    def test_get_graphite_zone_address(self):
        config = self.get_config(self.cfg1)
        config.inventory = dict(
            _meta=dict(
                hostvars=dict(
                    h1=dict(
                        internal_address="1.2.3.4", ansible_host="2.3.4.5"
                    ),
                    h2=dict(ansible_host="3.4.5.6"),
                )
            ),
            g1=dict(hosts=["h1"]),
            g3=dict(hosts=["h2"]),
        )
        self.assertEqual("1.2.3.4", config.get_graphite_zone_address("zone1"))
        self.assertEqual("3.4.5.6", config.get_graphite_zone_address("zone2"))

    def test_config_merge(self):
        config = CloudMonConfig()
        with tempfile.TemporaryDirectory() as dir1, tempfile.TemporaryDirectory() as dir2:  # noqa
            with open(Path(dir1, "config.yaml"), "w") as cfg1, open(
                Path(dir2, "config.yaml"), "w"
            ) as cfg2:
                cfg1.write(self.cfg2_part1)
                cfg1.seek(0)
                cfg2.write(self.cfg2_part2)
                cfg2.seek(0)
                config.parse("config.yaml", Path(dir1), Path(dir2))

                self.maxDiff = None
                self.assertEqual(
                    [
                        {
                            "name": "c1",
                            "profile": "b1",
                            "auth": {"x": "y1"},
                            "region_name": None,
                        },
                        {
                            "name": "c2",
                            "profile": "b2",
                            "auth": {"x": "y2"},
                            "region_name": "r2",
                        },
                    ],
                    config.model.clouds_credentials.model_dump(),
                )
                self.assertEqual(
                    [
                        {
                            "name": "e1",
                            "env": {"OS_CLOUD": 1},
                            "monitoring_zones": [
                                {
                                    "name": "z1",
                                    "clouds": [
                                        {"name": "e1", "ref": "c1"},
                                        {"name": "x", "ref": "x1"},
                                    ],
                                }
                            ],
                        }
                    ],
                    config.model.environments.model_dump(),
                )
                self.assertEqual(
                    [
                        {
                            "name": "zone1",
                            "graphite_group_name": "g1",
                            "statsd_group_name": "g2",
                        },
                        {
                            "name": "zone2",
                            "graphite_group_name": "g3",
                            "statsd_group_name": "g4",
                        },
                    ],
                    config.model.monitoring_zones.model_dump(),
                )
                self.assertDictEqual(
                    {
                        "postgres_postgres_password": "abc",
                        "ha_mode": False,
                        "databases": [
                            {
                                "name": "d1",
                                "users": [
                                    {"name": "d1u1", "password": "d1u1p"}
                                ],
                            }
                        ],
                    },
                    config.model.database.model_dump(),
                )
