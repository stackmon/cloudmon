Role Name
=========

A role which installes the epmon role from the apimon project(https://github.com/opentelekomcloud-infra/apimon). 

Requirements
------------

None.

Role Variables
--------------

    # defaults file for epmon
    epmon_os_group: apimon
    epmon_os_user: apimon
    epmon_systemd_service_name: apimon_epmon.service
    epmon_systemd_unit_path: "{{ ('/etc/systemd/system/' + epmon_systemd_service_name ) }}"
    epmon_config_dir: /etc/apimon
    epmon_config:
    epmon_image: otcinfra/apimon
    scheduler_image: otcinfra/apimon


Dependencies
------------

None.

Example Playbook
----------------


    - hosts: epmon
      roles:
         - { role: opentelekomcloud.apimon.epmon }

License
-------

Apache

Author Information
------------------

OpenTelekomCloud
