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
test_sql
----------------------------------

"""

from unittest import mock

from cloudmon.tests.unit import base

from cloudmon.service import sqldb


class TestSql(base.TestCase):
    cfg1 = """
      clouds_credentials: []
      database:
        postgres_postgres_password: abc
        databases: []
      environments: []
      matrix: []
      metrics_processor:
        - name: m1
          kube_context: m1_context
          kube_namespace: m1_ns
          datasource_url: fake_url
          status_dashboard_instance_name: sdb1
          environments:
            - name: e1
              attributes:
                foo: bar
          domain_name: fqdn
          kustomization:
            foo: bar
      monitoring_zones: []
      plugins: []
      status_dashboard:
        - name: sdb1
          domain_name: sdb_url
          kube_context: foo
          kube_namespace: bar
          kustomization: {}
          api_secret: secr
    """
    inventory = """
    """

    def setUp(self):
        config = self.get_config(self.cfg1, self.inventory)
        self.sot = sqldb.PostgreSQLManager(config)

    class Opts:
        component: str

        def __init__(self):
            self.component = None

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_provision(self, runner_mock):
        config = self.get_config(self.cfg1)
        self.sot.provision(self.Opts())
        runner_mock.assert_called_with(
            private_data_dir=mock.ANY,
            artifact_dir=".cloudmon_artifact",
            project_dir=config.project_dir.as_posix(),
            playbook="install_postgresql.yaml",
            inventory=mock.ANY,
            extravars=dict(
                distro_lookup_path=[
                    ("{{ ansible_facts.distribution }}"
                     ".{{ ansible_facts.lsb.codename|default() }}"
                     ".{{ ansible_facts.architecture }}.yaml"),
                    ("{{ ansible_facts.distribution }}"
                     ".{{ ansible_facts.lsb.codename|default() }}.yaml"),
                    ("{{ ansible_facts.distribution }}"
                     ".{{ ansible_facts.architecture }}.yaml"),
                    "{{ ansible_facts.distribution }}.yaml",
                    "{{ ansible_facts.os_family }}.yaml",
                    "default.yaml",
                ],
                postgresql_group_name="postgres",
                postgres_postgres_password="abc",
                ha_mode=False,
                databases=[],
            ),
            verbosity=1,
        )

    @mock.patch(
        "ansible_runner.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_provision_db(self, runner_mock):
        config = self.get_config(self.cfg1)
        self.sot.provision_db(self.Opts())
        runner_mock.assert_called_with(
            private_data_dir=mock.ANY,
            artifact_dir=".cloudmon_artifact",
            project_dir=config.project_dir.as_posix(),
            playbook="manage_databases.yaml",
            inventory=mock.ANY,
            extravars=dict(
                postgres_root_password='abc',
                postgresql_group_name='postgres',
                databases=[],
            ),
            verbosity=1,
        )
