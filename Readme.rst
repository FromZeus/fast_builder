============
Fast Builder
============

Description
-----------

This utility is designed for building .deb packages.

How to use
----------

* Put .tar.gz archive or "debian" folder of your packet into "package" dirrectory

* `Configure config.yaml`_

* Run "./build.sh -e example@example.com -s 1 2 3"
    * -e - Here you have to place your e-mail address
    * -s - `Stages of building`_

* If all was configured well and nothing bad happens you could get your successully builded package!

Configure config.yaml
^^^^^^^^^^^^^^^^^^^^^

In the config.yaml file you can see fields with names same as in control file. Priority of this config is higher than control file, so all fields filled here would be rewritten with config's values. Also here are some fields that absent in config file, such as: "Files", "Login", "Password", "Branch", "Buildsystem", "BuildWith", etc. The last three from rules file.

- Files
    You can specify that for every package if you build more than one subpackage. Example: "usr/bin;usr/lib" for main package; "usr/share/icons/; usr/share/package_name/; usr/share/locale/" - for common package. Every single location have to be separated with ";" symbol.
- OnlyIf
    In this section you can list packages with bounds you want to apply them. This bounds will be apply **only if this packages will be there.** This section could be defined in every field where list packages with their bounds.
- Main
    This is an identificator of main package. If it's set then packages from requirements.txt will be added in Depends of this package.
- ControlInternal
    Make utility check "control-internal.json" base for matching with packets that didn't match any package in main base.
- Update
    Update or not update versions of all dependencies.
- UpdateIfBounds
    Update only packages which already have bounds.
- DelBounds
    List of bounds which will be removed. You can use: ["<<", ">>", "<=", ">=", "==", "!="].
- ControlInternal
    Some packages have multiple names. So, if this field is checked then packages which didn't match any package in main base will be checked in additional base.
- BuildExcepts
    List of pacakges which have to be excluded while building.

*Credentials section*

In this section only three fields:

- Login
    Your launchpad e-mail.
- Password
    Your launchpad password.
- Branch
    This property is needed for update package versions with global list of requirements. You can chose in [master, juno, icehouse, kilo].

*Changelog section*

In this section you could specify cap of your changelog file.

- PakageName
    Name of package which builds.
- Version
    Version of package wich builds.
- Revision
    In Main section you could specify revision it self then in Append section you could specify a tail of revision. You could specify only Append part, then parser will take Main part from changelog and append your.
- Tag
    Tag of package wich builds.
- Urgency
    Urgency of package wich builds.

By default all fields take from changelog file.

**An example of config.yaml you can find in the directory.**

Stages of building
^^^^^^^^^^^^^^^^^^
0. Hidden stage is for prepare all files to make and build also for getting names of necessary files and folders. Executed by default.
1. First stage - make with dh_make command.
2. Second stage - run "builder.py -c config.yaml". In this stage python script do all necessary things with control and rules files. You can execute this stage, for example, if only "debian" folder in the "package" directory. **Please, be attentive to package versions. Some versions could not be parsed correctly, this could be reason of loss packages!**
3. Third stage runs "DEB_BUILD_OPTIONS=nocheck dpkg-buildpackage -rfakeroot -us -uc" and cleanup directory.
