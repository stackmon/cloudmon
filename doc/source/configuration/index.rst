=============
Configuration
=============

Cloudmon accepts yaml file with the configuration. This config is then being split and proper configuration is being used to deploy certain component in certain environment.

In order to improve openess of the configuration (public vs sensitive
information) it is possible to split it into 2 parts: git repository with
publicly accessible elements and a local config with sensitive part.  Content
of the git repository, specified with `--config-repo` parameter, is then taken
as a base and local config is being applied on top to keep possibility to
override fake information with sensitive elements. Merging of lists is being
done based on the `name` attribute of the list item.

.. note:: When using `--config-repo` parameter config file name can only be
   same as in config-dir location.

.. literalinclude:: /../../etc/sample_config.yaml
   :language: yaml
   :caption: Sample configuration


.. automodule:: cloudmon.types
   :members:
