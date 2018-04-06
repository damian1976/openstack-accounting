## Openstack-accounting

#### Usage

A simple script calculating disk, ram and cpu usage for openstack virtual server instances defined in config file for given time period.
Sample executions:

    1.  ./account.py -u USERNAME -p PASSWD -f config.ini --details --start-time 2017-09-05 --end-time 2017-09-20
    2.  ./account.py -u USERNAME -p PASSWD -f config.ini --no-details --start-time 2017-09-05 -o output.csv
    3.  ./account.py -u USERNAME -p PASSWD -f config.ini --no-details --start-time 2017-09-05 --export-db
    4.  ./account.py -u USERNAME -p PASSWD -f config.ini --details --start-time 2018-09-05 --end-time 2017-09-30 --as-admin
    5.  ./account.py -u USERNAME -p PASSWD -f config.ini --details --start-time 2018-09-05 --end-time 2017-09-30 --as-admin --volumes --images --details -o output.csv --export-db

User credentials can also be provided in ENV variables as OS_USERNAME and OS_PASSWD. If so, then sample execution may look like:

    ./account.py -f config.ini --details --start-time 2017-09-05 --end-time 2017-09-20

#### Installation steps:
    
    1. virtualenv /path/to/new/virtualenv -p python3.4 (*)
    2. sudo apt-get install libcurl4-openssl-dev
    3. export PYTHONPATH=/path/to/virtualenv/lib/python3.4/site-packages (*)
    4. source /path/to/new/virtualenv/bin/activate
    5. pip install --upgrade pip
    6. clone app into virtualenv dir
    7. cd app
    8. pip install -e .
    ENJOY :)

*)  Please use your own python 3.x version

