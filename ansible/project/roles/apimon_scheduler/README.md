Role Name
=========

A role which installes the scheduler role from the apimon project(https://github.com/opentelekomcloud-infra/apimon). 

Requirements
------------

None.

Role Variables
--------------

    # defaults file for scheduler
    scheduler_os_group: apimon
    scheduler_os_user: apimon
    scheduler_systemd_service_name: apimon_scheduler.service
    scheduler_systemd_unit_path: "{{ ('/etc/systemd/system/' + scheduler_systemd_service_name ) }}"
    scheduler_config_dir: /etc/apimon
    scheduler_config:
    scheduler_image: otcinfra/apimon
    executor_image: otcinfra/apimon


Dependencies
------------

None.

Example Playbook
----------------


    - hosts: scheduler
      roles:
         - { role: opentelekomcloud.apimon.scheduler }

License
-------

Apache

Author Information
------------------

OpenTelekomCloud
