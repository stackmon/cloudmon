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

import logging
from pathlib import Path
import shutil
import sys
import tempfile

from ruamel.yaml import YAML

from cliff.app import App
from cliff.commandmanager import CommandManager

from cloudmon.config import CloudMonConfig


class CloudMon(App):
    def __init__(self):
        super().__init__(
            description="CloudMon manager process",
            version="0.1",
            command_manager=CommandManager("cloudmon.manager"),
            deferred_help=True,
        )
        self.config = None
        self.inventory = None
        self.is_priv_tmp = False

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super().build_option_parser(
            description, version, argparse_kwargs
        )
        parser.add_argument(
            "--config",
            dest="config",
            default="config.yaml",
            help="specify the config file",
        )
        parser.add_argument(
            "--private-data-dir",
            help="Ansible-runner project dir",
        )
        parser.add_argument(
            "--inventory",
            default="ansible/inventory",
            help="specify the Inventory path",
        )

        return parser

    def initialize_app(self, argv):
        self.LOG.debug("initialize_app %s", argv)

        self.config = CloudMonConfig()

        if "help" not in argv:
            if not self.options.private_data_dir:
                self.config.private_data_dir = Path(
                    tempfile.mkdtemp(prefix="cloudmon")
                )
                self.is_priv_tmp = True
            else:
                self.config.private_data_dir = Path(
                    self.options.private_data_dir
                ).resolve()

            if (
                self.options.config is not None
                and Path(self.options.config).exists()
                and self.options.inventory is not None
                and Path(self.options.inventory).exists()
            ):
                self.config.parse(self.options.config)
                # yaml = YAML()
                # with open(self.options.config, "r") as f:
                #     self.config.config = yaml.load(f)

                self.config.process_inventory(
                    Path(self.options.inventory).resolve()
                )

    def prepare_to_run_command(self, cmd):
        self.LOG.debug("prepare_to_run_command %s", cmd.__class__.__name__)
        if self.config.private_data_dir:
            self.config.private_data_dir.mkdir(parents=True, exist_ok=True)

    def clean_up(self, cmd, result, err):
        self.LOG.debug("clean_up %s", cmd.__class__.__name__)
        if err:
            self.LOG.error("got an error: %s", err)

        if (
            self.config
            and self.config.is_updated
            and self.config.config.items()
        ):
            yaml = YAML()
            yaml.indent(offset=2, sequence=4)
            with open(self.options.config, "w") as f:
                yaml.dump(self.config.config, f)
            logging.info("Your config file was updated by the process")

        if self.is_priv_tmp and self.config.private_data_dir:
            shutil.rmtree(self.config.private_data_dir)


#    def process_inventory(self):
#        """Pre-process passed inventory"""
#        if "graphite" in self.inventory:
#            random_graphite_host = self.inventory["graphite"]["hosts"][0]
#            graphite_host_vars = self.inventory["_meta"]["hostvars"].get(
#                random_graphite_host
#            )
#            self.graphite_address = graphite_host_vars.get(
#                "internal_address", random_graphite_host
#            )
#        elif "graphite" in self.config.config:
#            self.graphite_address = self.config.config["graphite"].get("host")


def main(argv=sys.argv[1:]):
    app = CloudMon()
    return app.run(argv)


if __name__ == "__main__":
    main()
