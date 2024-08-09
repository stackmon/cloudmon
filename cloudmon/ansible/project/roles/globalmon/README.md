Role Name
=========

A role which installes the globalmon role from the globalmon project(https://github.com/stackmon/globalmon). 

Requirements
------------

None.

Role Variables
--------------

    # defaults file for globalmon
    globalmon_os_group: globalmon
    globalmon_os_user: globalmon
    globalmon_systemd_service_name: globalmon_globalmon.service
    globalmon_systemd_unit_path: "{{ ('/etc/systemd/system/' + globalmon_systemd_service_name ) }}"
    globalmon_config_dir: /etc/globalmon
    globalmon_config:
    globalmon_image: stackmon/globalmon
    scheduler_image: stackmon/globalmon


Dependencies
------------

None.

Example Playbook
----------------


    - hosts: globalmon
      roles:
         - { role: opentelekomcloud.globalmon.globalmon }

License
-------

Apache

Author Information
------------------

OpenTelekomCloud
