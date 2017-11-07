# openstack-accounting
A simple script calculating disk and cpu usage for openstack virtual server instances defined in config file for given time period.
Sample executions:
1) ./account.py -u USERNAME -p PASSWD -f config.ini --details --start 2017-09-05 --end 2017-09-20
2) ./account.py -u USERNAME -p PASSWD -f config.ini --no-details --start 2017-09-05

User credentials can also be provided in ENV variables as OS_USERNAME and OS_PASSWD. If so, then sample execution may look like:

./account.py -f config.ini --details --start 2017-09-05 --end 2017-09-20



Install instructions:
    virtualenv /path/to/new/virtualenv -p python3.4
    sudo apt-get install libcurl4-openssl-dev
    export PYTHONPATH=/path/to/virtualenv/lib/python3.4/site-packages/
    source /path/to/new/virtualenv/bin/activate
    pip install --upgrade pip
    copy app folder to virtualenv dir dir
    cd app
    pip install -e .
    ENJOY :)

