============
Fast Builder
============

Description
-----------

This utility is designed for building .deb packages.

How to use
----------

  * Put .tar.gz archive of your packet into "package" dirrectory
  * `Configure config.yaml`_
  * Run ./build.sh -e example@example.com -s `1`_ `2`_ `3`_
    - -e - Here you have to place your e-mail address
    - -s - `Stages of building`_
  * If all was configured well and nothing bad happens you could get your successully builded package!

Configure config.yaml
^^^^^^^^^^^^^^^^^^^^^

Stages of building
^^^^^^^^^^^^^^^^^^
  0. Hidden stage is for prepare all files to make and build, also for getting names of necessery files and folders
  1. First stage is for
  ^
