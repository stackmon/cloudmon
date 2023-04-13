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

from cloudmon.tests.unit import base


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
                    "data": {"profile": "_b", "auth": {"x": "_y"}},
                },
            },
        )

    def test_config_get_env_cloud_credentials(self):
        config = self.get_config(self.cfg1)
        self.assertDictEqual(
            config.get_env_cloud_credentials("e1", "z1", "x"),
            {
                "name": "x",
                "data": {"profile": "_b", "auth": {"x": "_y"}},
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
