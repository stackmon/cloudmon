==================
Installation guide
==================

At the moment cloudmon is not published to the pypi, so the only
way to use it is to install project from git directly. This will
normally require preparation of the python virtual environment
(cloudmon pulls ansible and ansible-runner as well as some other
components and it is strongly suggested not to mess with system
packages).

.. code-block:: console

   python3 -m venv cloudmon_venv
   source cloudmon_venv/bin/activate
   pip install -r requirements.txt
   cloudmon --config ....


Configuration
=============

When deploying certain stack elements to the K8 cloudmon is expecting `~/.kube/config` file to be present and contain configuration for the contexts referred from the cloudmon configuration.
