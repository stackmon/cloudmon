# -*- coding: utf-8 -*-

# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
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

from pathlib import Path
import tempfile
from unittest import TestCase

from cloudmon.config import CloudMonConfig


class TestCase(TestCase):

    """Test case base class for all unit tests."""

    def get_config(self, content, inventory=None):
        config = CloudMonConfig()
        with tempfile.NamedTemporaryFile() as cfg:
            cfg.write(content.encode())
            cfg.seek(0)
            config.parse(cfg.name)
            config.config_dir = Path(cfg.name).parent
        if inventory:
            with tempfile.NamedTemporaryFile() as fp:
                fp.write(inventory.encode())
                fp.seek(0)
                config.process_inventory(Path(fp.name).resolve())

        return config
