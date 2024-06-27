Toxicintegrations config
========================

The configuration of toxicintegrations is done using the a configuration file. The configuration
file can be passed using the  ``-c`` flag to the ``toxicintegrations`` command
or settings the environment variable ``TOXICINTEGRATIONS_SETTINGS``.

This file is a python file, so do what ever you want with it.

Config values
-------------

.. note::

   Although the config is done using a config file, the default
   configuration file created by ``toxicintegrations create`` can use
   environment variables instead.


* ``PORT`` - The port for the server to listen. Defaults to `8888`.
  Environment variable: ``INTEGRATIONS_WEB_PORT``

* ``HOLE_HOST`` - Toxicmaster hole server
  Environment variable: ``HOLE_HOST``

* ``HOLE_PORT`` - Toxicmaster hole port
  Environment variable: ``HOLE_PORT``

* ``HOLE_TOKEN`` - Access token for the master.
  Environment variable: ``HOLE_TOKEN``

* ``MASTER_USES_SSL`` - Indicates if the master uses ssl connection
  Environment variable: ``MASTER_USES_SSL``

* ``VALIDADES_CERT_MASTER`` - Validate the master ssl certificate?
  Environment variable: ``VALIDATE_MASTER_CERTS``


* ``ZK_SERVERS`` - A list of zookeeper servers.
  Environment variable: ``ZK_SERVERS``. Servers must be comma separated.

* ``ZK_KWARGS`` - Arguments passed to zookeeper client. Check the
  `aiozk docs <https://aiozk.readthedocs.io/en/latest/api.html#zkclient>`_.

* ``DBHOST`` - Host for the database connection.
  Environment variable: ``SECRETS_DBHOST``.

* ``DBPORT`` - Port for the database connection. Defaults to `27017`.
  Environment variable: ``SECRETS_DBPORT``.

* ``DBNAME`` - The database name. Defaults to `toxicsecrets`.
  Environment variable: ``SECRETS_DBNAME``

* ``DBUSER`` - User name for authenticated access to the database
  Environment variable: ``SECRETS_DBUSER``

* ``DBPASS`` - Password for authenticated access to the database
  Environment variable: ``SECRETS_DBPASS``


* ``AMQP_HOST`` - host for the rabbitmq broker.
  Environment variable: ``AMQPHOST``

* ``AMQP_PORT`` - port for the rabbitmq broker.
  Environment variable: ``AMQPPORT``

* ``AMQP_LOGIN`` - login for the rabbitmq broker.
  Environment variable: ``AMQPLOGIN``

* ``AMQP_VIRTUALHOST`` - virtualhost for the rabbitmq broker.
  Environment variable: ``AMQPVIRTUALHOST``

* ``AMQP_PASSWORD`` - password for the rabbitmq broker.
  Environment variable: ``AMQPPASSWORD``
