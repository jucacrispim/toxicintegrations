Toxicintegrations: Toxicbuild integrations with 3rd party services
===================================================================


Install
-------

To install it use pip:

.. code-block:: sh

   $ pip install toxicintegrations --extra-index-url=https://pypi.poraodojuca.dev



Setup & config
--------------

Before executing builds you must create an environment for toxicintegrations.
To do so use:

.. code-block:: sh

   $ toxicintegrations create ~/integrations-env

This is going to create a ``~/integrations-env`` directory with a ``toxicintegrations.conf``
file in it. This file is used to configure toxicintegrations.

Check the configuration instructions for details

.. toctree::
   :maxdepth: 1

   config


Run the server
--------------

When the configuration is done you can run the server with:

.. code-block:: sh

   $ toxicintegrations start ~/integrations-env


For all options for the toxicintegrations command execute

.. code-block:: sh

   $ toxicintegrations --help



CHANGELOG
---------

.. toctree::
   :maxdepth: 1

   CHANGELOG
