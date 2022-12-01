Role Name
=========

A role which installes the executor role from the apimon project(https://github.com/opentelekomcloud-infra/apimon). 

Requirements
------------

None.

Role Variables
--------------

    # defaults file for executor
    executor_os_group: apimon
    executor_os_user: apimon
    executor_systemd_service_name: apimon_executor.service
    executor_systemd_unit_path: "{{ ('/etc/systemd/system/' + executor_systemd_service_name ) }}"
    executor_config_dir: /etc/apimon
    executor_config:
    executor_image: otcinfra/apimon
    scheduler_image: otcinfra/apimon


Dependencies
------------

None.

Example Playbook
----------------


    - hosts: executor
      roles:
         - { role: opentelekomcloud.apimon.executor }

License
-------

Apache

Author Information
------------------

OpenTelekomCloud
