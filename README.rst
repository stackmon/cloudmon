========
cloudmon
========

CloudMon controller is a logical continuation of the ApiMon concept for
monitoring clouds from a user perspective for operators. In difference to pure
ApiMon it is able to monitor also static resources (i.e. loadbalancers) to
ensure not only user is able to provision cloud resources, but the resources he
provisioned are still functioning properly.

CloudMon controller is supposed to become a central operating tool responsible
for provisioning of all corresponding conmponents and their maintenance.

Please note the project is in the early development phase therefore bugs and
missing features are expected to exist.

* Free software: Apache license
* Documentation: https://docs.otc.t-systems.com/cloudmon
* Source: https://github.com/opentelekomcloud/cloudmon

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
           1.2.3.4
       # ApiMon Schedulers
       schedulers:
         hosts:
           1.2.3.4
       # ApiMon Executors
       executors:
         hosts:
           1.2.3.4

Configuration file is responsible for defining which CloudMon plugins are going
to be used, which environments need to be monitored and with which settings.

.. code-block:: yaml
   :caption: config.yaml

   # Target Environments
   environments:
     production:
       env:
         OS_CLOUD: production
       monitoring_zones:
         internal:
           clouds:
             - name: production
               ref: p1
             - name: swift
               ref: swift1
         external:
           clouds:
             - name: production
               ref: p2
             - name: swift
               ref: swift1

   # Git projects with test scenarios
   cloudmon_plugins:
     apimon:
       type: apimon
       scheduler_image: "quay.io/opentelekomcloud/apimon:change_31_latest"
       executor_image: "quay.io/opentelekomcloud/apimon:change_31_latest"
       epmon_image: "quay.io/opentelekomcloud/apimon:change_31_latest"
       tests_projects:
         - name: apimon
           repo_url: https://github.com/opentelekomcloud-infra/apimon-tests
           repo_ref: master
           scenarios_location: playbooks
           grafana_dashboards_location: dashboards
     lb:
       image: quay.io/opentelekomcloud/cloudmon-plugin-lb
       init_image: quay.io/opentelekomcloud/cloudmon-plugin-lb-init
     smtp:
       image: quay.io/opentelekomcloud/cloudmon-plugin-smtp
       init_image: quay.io/opentelekomcloud/cloudmon-plugin-smtp-init

   matrix:
     # Mapping of environments to test projects
     # Regular apimon project in env ext
     - env: production
       monitoring_zone: internal
       plugins:
         - name: apimon
           schedulers_inventory_group_name: schedulers_int
           executors_inventory_group_name: executors_int
           epmons_inventory_group_name: epmons_int
           tests_project: apimon
           tasks:
             - scenario1_token.yaml

   clouds_credentials:
     p1:
       auth:
         auth_url: fake.com1
         project_name: fake_project
         user_domain_name: fake
         username: fake
         password: fake
     p2:
       auth:
         auth_url: fake.com2
         project_name: fake_project
         user_domain_name: fake
         username: fake
         password: fake
     swift1:
       data:
         auth:
           auth_url: fake.com
           project_name: fake_project
           user_domain_name: fake
           username: fake
           password: fake

CloudMon can be invoked specifying path to the config file and inventory file
(absolute paths)

.. code-block:: console

   cloudmon --config config.yaml --inventory /cloudmon/ansible/inventory_quickstart/

Unless CloudMon release process and invocation interface are clarified it is
possible to use it from the local checkout and install it locally:

- python3 setup.py develop

or

- tox -epy39 --notest && source .tox/py39/bin/activate
