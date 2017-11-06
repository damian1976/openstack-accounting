# openstack-accounting
A simple script calculating disk and cpu usage for openstack virtual server instances defined in config file for given time period.
Sample executions:
1) ./account.py -u USERNAME -p PASSWD -f config.ini --details --start 2017-09-05 --end 2017-09-20
2) ./account.py -u USERNAME -p PASSWD -f config.ini --no-details --start 2017-09-05

