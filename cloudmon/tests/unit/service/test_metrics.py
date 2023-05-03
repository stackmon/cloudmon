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
test_metrics
----------------------------------

"""

from pathlib import Path
from unittest import mock
import yaml

from cloudmon.tests.unit import base

from cloudmon.service import metrics


class TestMetrics(base.TestCase):
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
          domain_name: fqdn
          kustomization:
            foo: bar
      monitoring_zones: []
      plugins: []
    """
    inventory = """
    """

    def setUp(self):
        config = self.get_config(self.cfg1, self.inventory)
        self.sot = metrics.MetricsProcessorManager(config)

    class Opts:
        component: str

        def __init__(self):
            self.component = None

    @mock.patch(
        "subprocess.run", autospec=True, return_value=mock.MagicMock(rc=0)
    )
    def test_provision(self, runner_mock):
        self.sot.provision(self.Opts())
        overlay_dir = runner_mock.call_args.kwargs["cwd"]
        calls = [
            mock.call(
                args=[
                    "kubectl",
                    "--context",
                    "m1_context",
                    "--namespace",
                    "m1_ns",
                    "apply",
                    "-k",
                    ".",
                ],
                cwd=mock.ANY,
                check=True,
            )
        ]
        runner_mock.assert_has_calls(calls)
        with open(Path(overlay_dir, "kustomization.yaml")) as fp:
            kust = yaml.safe_load(fp)
            self.assertDictEqual(
                {
                    "apiVersion": "kustomize.config.k8s.io/v1beta1",
                    "foo": "bar",
                    "kind": "Kustomization",
                    "resources": ["../../base"],
                },
                kust,
            )
