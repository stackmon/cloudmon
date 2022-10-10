Install and configure firewalld

**Role Variables**

.. zuul:rolevar:: firewalld_services_enable
   :default: [ssh]

   A list of services to allow on the host

.. zuul:rolevar:: firewalld_services_disable
   :default: []

   A list of services to forbid on the host

.. zuul:rolevar:: firewalld_ports_enable
   :default: []

   A list of ports to allow on the host

.. zuul:rolevar:: firewalld_ports_disable
   :default: []

   A list of ports to forbid on the host
