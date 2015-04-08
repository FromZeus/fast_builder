#
# Regular cron jobs for the python-aioeventlet package
#
0 4	* * *	root	[ -x /usr/bin/python-aioeventlet_maintenance ] && /usr/bin/python-aioeventlet_maintenance
