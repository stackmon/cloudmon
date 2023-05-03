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

from ruamel.yaml import YAML

from cliff.app import App
from cliff.commandmanager import CommandManager

from cloudmon.config import CloudMonConfig
from cloudmon.types import GitRepoModel
from cloudmon import utils


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
        self.is_priv_tmp = True

    def build_option_parser(self, description, version, argparse_kwargs=None):
        parser = super().build_option_parser(
            description, version, argparse_kwargs
        )
        parser.add_argument(
            "--config-dir",
            help="Specify the config directory",
        )
        parser.add_argument(
            "--config",
            default="config.yaml",
            help="Specify the config file name (relative to config-dir)",
        )
        parser.add_argument(
            "--config-repo",
            help=(
                "Specify Git repository with supplementary configs. "
                "(config file must be same as `--config`)"
            ),
        )
        parser.add_argument(
            "--private-data-dir",
            help="Ansible-runner project dir",
        )
        parser.add_argument(
            "--inventory",
            default="inventory.yaml",
            help="Specify the Inventory path (relative to `--config-dir`)",
        )
        return parser

    def initialize_app(self, argv):
        self.LOG.debug("initialize_app %s", argv)

        self.config = CloudMonConfig()

        if "help" not in argv:
            if self.options.private_data_dir:
                self.config.private_data_dir = Path(
                    self.options.private_data_dir
                ).resolve()
                self.is_priv_tmp = False

            final_config_dir = Path(self.config.private_data_dir, "_config")
            # final_config_dir.mkdir(parents=True, exist_ok=True)
            config_dir2 = None
            if self.options.config_repo is not None:
                # Checkout config-repo into separate dir and use it as a base
                # in final_config_dir
                config_dir2 = Path(self.config.private_data_dir, "config_repo")
                repo = GitRepoModel(repo_url=self.options.config_repo)
                utils.checkout_git_repository(config_dir2, repo)
                shutil.copytree(
                    config_dir2, final_config_dir, dirs_exist_ok=True
                )

            if (
                self.options.config_dir is not None
                and self.options.config is not None
                and Path(self.options.config_dir, self.options.config).exists()
                and self.options.inventory is not None
                and Path(
                    self.options.config_dir, self.options.inventory
                ).exists()
            ):
                shutil.copytree(
                    self.options.config_dir,
                    final_config_dir,
                    dirs_exist_ok=True,
                )
                self.config.config_dir = final_config_dir
                self.config.parse(
                    self.options.config,
                    Path(self.options.config_dir).resolve(),
                    config_dir2,
                )

                self.config.process_inventory(
                    Path(
                        self.options.config_dir, self.options.inventory
                    ).resolve()
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


def main(argv=sys.argv[1:]):
    app = CloudMon()
    return app.run(argv)


if __name__ == "__main__":
    main()
