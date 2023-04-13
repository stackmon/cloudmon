===========
Users guide
===========

cloudmon can be a single tool to use when operating the whole
monitoring stack. It implements cli commands for every component
as well as single command to provision all components.

In a real live it may be preferred to manage certain components
of the stack separately by other means (i.e. database). Cloudmon
is not enforcing management of most of the components and thus
allows getting them out of the management process. There are,
however, certain limitations or assumptions that cloudmon just
need:

- currently only Graphite TSDB is supported. This is not a
  strict architecture decision and any alternatives can be
  implemented (main thing to remember is that monitoring emits
  metrics and they need to reach TSDB as well as it must be also
  possible to query metrics out of DB.)

- cloudmon "wants" to be able to create databases, at least it
  definitely needs to have credentials to those databases to
  further provision components needing database.

- when cloudmon installs DB it uses postgres database and it uses Patroni for implementing High Availability. In that case it is expected that SSL certificates are managed externally (cloudmon will not try to implement SSL cert management)

Provisioning
============

Installation and configuration of the software in the context of
cloudmon is called provisioning. Certain components are having
extra "configure" step that allows to only do configration (in
example only manage datasources and dashboards in Grafana
without trying to install it).

Provisioning can be triggered by a single invocation of the
`cloudmon provision` to manage all steps in a one shot. Or
alternatively every component can be managed individually (i.e.
`cloudmon graphite provision`, `cloudmon postgres provision`).
In every case a path to the configuration file and ansible
inventory must be provided to the command.

Starting
========

Various components of the StackMon support starting and stopping
(i.e. to stop/start testing of certain environment). This is
normally supported by invoking `cloudmon apimon start` or
similar.

Stopping
========

A command in a form `cloudmon apimon stop` is supported for
several components.
