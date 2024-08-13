========
cloudmon
========

StackMon as name suggest consists of multiple components required for running
the tests, capturing and storing metrics, processing metrics and managing
incidents in the status dashboard. It is not an easy task to ensure all of the
components do what they need to do and get a corresponding configuration.
CloudMon controller is a tool to automate installation and configuration
management of all those components. It can be compared with Ansible AWX, since
it actually even invokes ansible-runner to do the work.

CloudMon controller is supposed to become a central operating tool responsible
for provisioning of all corresponding conmponents and their maintenance. It is
not required to use it, but it can help to dramatically reduce operations
efforts.

Please note the project is in the early development phase therefore bugs and
missing features are expected to exist.

* Free software: Apache license
* Source: https://github.com/stackmon/cloudmon

Quickstart
----------

CloudMon requires currently 2 things to work:

- configuration file
- inventory

Inventory represents an Ansible inventory for the whole CloudMon installation.
It defines hosts and groups onto which CloudMon components would be installed

.. code-block:: yaml
   :caption: ansible/inventory/hosts

   all:
     hosts:
       # All-In-One VM
       1.2.3.4:
         ansible_user: ubuntu
         internal_address: 192.168.1.2
     children:
       # Manage graphite
       graphite:
         hosts:
           1.2.3.4:
       # ApiMon Schedulers
       schedulers:
         hosts:
           1.2.3.4:
       # ApiMon Executors
       executors:
         hosts:
           1.2.3.4:

Configuration file is responsible for defining which CloudMon plugins are going
to be used, which environments need to be monitored and with which settings.

.. literalinclude:: /../../etc/sample_config.yaml
   :language: yaml

CloudMon can be invoked specifying path to the config repository and the config directory containing config.yaml and inventory.yml files. 
(absolute paths)
Config repo contains the public part of the configuration whereas the secret part can be stored in the config.yaml in config directory.

.. code-block:: console

   # Provision everything
   cloudmon --config-dir PATH/TO/CONFIG_DIR --config-repo https://your-repo-url.git provision

   # Using specific branch of config repo
   cloudmon --config-dir PATH/TO/CONFIG_DIR --config-repo https://your-repo-url.git --config-repo-branch BRANCH_NAME provision 

   # Provision apimon
   cloudmon --config-dir PATH/TO/CONFIG_DIR --config-repo https://your-repo-url.git apimon provision
   

   # Stopping
   cloudmon --config-dir PATH/TO/CONFIG_DIR --config-repo https://your-repo-url.git apimon stop

   # Starting
   cloudmon --config-dir PATH/TO/CONFIG_DIR --config-repo https://your-repo-url.git apimon start


**NOTE:** A sample of config repo can be found `here <https://github.com/opentelekomcloud-infra/stackmon-config>`_.

CloudMon can also be invoked in insecure mode specifying path to the config file and inventory file
(absolute paths). Sample files can be found in **./etc** directory.

.. code-block:: console

   # Provision everything
   cloudmon --config ./etc/config.yaml --inventory ./etc/inventory_quickstart/ provision

   # Provision apimon
   cloudmon --config ./etc/config.yaml --inventory ./etc/inventory_quickstart/ apimon provision

   # Stopping
   cloudmon --config ./etc/config.yaml --inventory ./etc/inventory_quickstart/ apimon stop

   # Starting
   cloudmon --config ./etc/config.yaml --inventory ./etc/inventory_quickstart/ apimon start


Unless CloudMon release process and invocation interface are clarified it is
possible to use it from the local checkout and install it locally:

- python3 setup.py develop

or

- tox -epy39 --notest && source .tox/py39/bin/activate
