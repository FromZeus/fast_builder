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
* Run ./build.sh -e example@example.com -s 1 2 3
    * -e - Here you have to place your e-mail address
    * -s - `Stages of building`_
* If all was configured well and nothing bad happens you could get your successully builded package!

Configure config.yaml
^^^^^^^^^^^^^^^^^^^^^

In the config.yaml file you can see fields with names same as in control file. Priority of this config is higher than control file, so all fields filled here would be rewritten with config's values. Also here are some fields that absent in config file, such as: "Files", "Login", "Password", "Branch", "Buildsystem", "BuildWith". The last three from rules file.

* Files
    You can specify that for every package if here is more than one package. Example: "usr/bin;usr/lib" for main package; "usr/share/icons/; usr/share/package_name/; usr/share/locale/" - for common package. Every single location have to be separated with ";" symbol.
* Login
    Your launchpad e-mail.
* Password
    Your launchpad password.
* Branch
    This property is needed for update package versions with global list of requirements. You can chose in [master, juno, icehouse].

Stages of building
^^^^^^^^^^^^^^^^^^
  0. Hidden stage is for prepare all files to make and build also for getting names of necessary files and folders
  1. First stage - make with dh_make command
  2. Second stage - run "builder.py -c config.yaml". In this stage python script do all necessary things with control and rules files
  3. Third stage runs "DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -rfakeroot -us -uc" and cleanup directory
