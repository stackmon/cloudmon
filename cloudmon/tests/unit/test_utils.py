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
test_utils
----------------------------------

"""
from pathlib import Path
import shutil
import tempfile
import yaml

from cloudmon.tests.unit import base

from cloudmon import utils


class TestUtils(base.TestCase):
    def test_prepare_kustomize_overlay(self):
        overlays_dir = tempfile.mkdtemp()
        overlay_dir = utils.prepare_kustomize_overlay(
            overlays_dir=overlays_dir,
            base="base_app",
            name="overlay_name",
            kustomization=dict(dummy={"foo": "bar"}),
        )
        self.assertEqual("overlay_name", overlay_dir.name)
        kust = Path(overlay_dir, "kustomization.yaml")
        kust_data = {}
        with open(kust.as_posix(), "r") as fp:
            kust_data = yaml.safe_load(fp)
        self.assertDictEqual(
            {
                "apiVersion": "kustomize.config.k8s.io/v1beta1",
                "dummy": {"foo": "bar"},
                "kind": "Kustomization",
                "resources": ["base_app"],
            },
            kust_data,
        )
        self.assertTrue(kust.exists())
        shutil.rmtree(overlays_dir)

    def test_prepare_kustomize_overlay_extra_files(self):
        overlays_dir = tempfile.mkdtemp()
        extra_dir = tempfile.mkdtemp()
        ef2_path = Path(extra_dir, "xconf")
        ef2_path.mkdir()
        (handle, ef1) = tempfile.mkstemp(dir=extra_dir, text=True)
        with open(handle, "w") as f:
            f.write("f1")
        ef1_path = Path(ef1)
        (handle, ef2) = tempfile.mkstemp(dir=ef2_path, text=True)
        with open(handle, "w") as f:
            f.write("f2")
        ef2_path = Path(ef2)

        overlay_dir = utils.prepare_kustomize_overlay(
            overlays_dir=overlays_dir,
            base="base_app",
            name="overlay_name",
            kustomization=dict(
                dummy={"foo": "bar"},
                extra_files=[
                    ef1_path.relative_to(extra_dir),
                    ef2_path.relative_to(extra_dir),
                ],
            ),
            config_dir=extra_dir,
        )
        self.assertEqual("overlay_name", overlay_dir.name)
        kust = Path(overlay_dir, "kustomization.yaml")
        kust_data = {}
        with open(kust.as_posix(), "r") as fp:
            kust_data = yaml.safe_load(fp)
        self.assertDictEqual(
            {
                "apiVersion": "kustomize.config.k8s.io/v1beta1",
                "dummy": {"foo": "bar"},
                "kind": "Kustomization",
                "resources": ["base_app"],
            },
            kust_data,
        )
        self.assertTrue(kust.exists())
        ef1_overlay_path = Path(overlay_dir, ef1_path.name)
        self.assertTrue(ef1_overlay_path.exists())
        with open(ef1_overlay_path, "r") as f:
            self.assertEqual("f1", f.read())
        ef2_overlay_path = Path(overlay_dir, "xconf", ef2_path.name)
        self.assertTrue(ef2_overlay_path.exists())
        with open(ef2_overlay_path, "r") as f:
            self.assertEqual("f2", f.read())

        shutil.rmtree(overlays_dir)
        shutil.rmtree(extra_dir)
