#!/usr/bin/env python
import os
import sys
import argparse
import datetime
import calendar
import re
import pytz
import configparser as Config
from dateutil.relativedelta import relativedelta
import dateutil.parser as dup
from novaclient import client
from keystoneauth1.identity import v3
from keystoneauth1 import session
from novaclient.exceptions import NotFound
import pprint
'''
from .account import (getOSUsersProjects,
                      getOSServers,
                      getOSUsersVolumes,
                      getOSUsersImages,
                      updateOSUserProjectsWithConfig,
                      filterAndRecalculateStorageByDatetime,
                      filterServerByDatetime,
                      getStopStartTimeFrames,
                      filterActionsByDatetime)
                      '''
from util.project import Project
from util.server import Server
from util.storage import Storage
from util.company import Company
from config import (API_VERSION,
                    INSTANCE_AT_VOLUME_STR,
                    VOL_PFX,
                    VOL_TENANT_ID_ATTR,
                    VOL_TYPE,
                    VOL_TYPE_STD)
from account import OpenstackAccounting

pp = pprint.PrettyPrinter(indent=4)
Verbosity = type('Verbosity', (), {'INFO': 1, 'WARNING': 2, 'DEBUG': 5})
DEBUG = False


def parse_args():
    # Instantiate the parser
    parser = argparse.ArgumentParser(description="Provides a simple Openstack "
                                     "resource accounting for given user, "
                                     "tenants and  period of time\n")

    # Required  argument
    parser.add_argument('-f', '--config_file',
                        nargs=1,
                        help='config file')

    #Optional argument
    parser.add_argument('-u', '--username',
                        nargs='?',
                        help='Openstack username. Otherwise OS_USERNAME env'
                        ' variable is used')

    # Optional  argument
    parser.add_argument('-p', '--passwd',
                        nargs='?',
                        help='Openstack password. Otherwise OS_PASSWORD env'
                        ' variable is used')

    # Optional  argument
    parser.add_argument('-s', '--start-time',
                        nargs='?',
                        help='Start date  in YYYY-MM-DD format. If not given'
                        ' the first day of last month is taken')
    # Optional  argument
    parser.add_argument('-e', '--end-time',
                        nargs='?',
                        help='End date in YYYY-MM-DD format. If not given'
                        ' the lst day of last month is taken')

    # Optional  argument
    parser.add_argument('-o', '--export-csv',
                        dest='csv',
                        nargs='?',
                        help='Output CSV file name')

    # Optional  argument
    parser.add_argument('--export-sqlite',
                        dest='sqlite',
                        action='store_true',
                        help="Enables saving results into SQLite database")

    # Optional  argument
    parser.add_argument('--export-mysql',
                        dest='mysql',
                        action='store_true',
                        help="Enables saving results into MySQL database")

    # Optional  argument
    parser.add_argument('--export-mongo',
                        dest='mongo',
                        action='store_true',
                        help="Enables saving results into mongodb. Please set env variable OPAC_MONGO "
                             "in the following format: mongodb://USER:PASSWD@SERVER/DB_NAME")

    # Optional  argument
    parser.add_argument('--details',
                        dest='feature',
                        action='store_true',
                        help="Enables accounting 'by server' feature")

    parser.add_argument('--volumes',
                        dest='volumes',
                        action='store_true',
                        help="Get user volumes")

    parser.add_argument('--images',
                        dest='images',
                        action='store_true',
                        help="Get user images")

    parser.add_argument('--no-details',
                        dest='feature',
                        action='store_false',
                        help="Disables accounting 'by server' "
                        "feature (default)")

    parser.add_argument('--as-admin',
                        dest='as_admin',
                        action='store_true',
                        help="Activates accounting for all users and projects")

    parser.add_argument(
        '-v', '--verbose',
        action='count',
        help="verbose mode (multiple -v's increase verbosity)")

    # Parse args
    args, extra = parser.parse_known_args()
    return args, parser


def configSectionMap(section, config=None):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("Exception on {0}!".format(option))
            dict1[option] = None
    return dict1


def readConfigFile(filename=None):
    if (not filename):
        return None
    config = Config.ConfigParser()
    config.read(filename)
    try:
        company_section = configSectionMap('Company', config)
        company_name = company_section['name']
        comp = Company(company_name)
        for key, value in company_section.items():
            if (key == 'compute_api_url'):
                comp.setComputeAPI(company_section['compute_api_url'])
            if (key == 'identity_api_url'):
                comp.setIdentityAPI(company_section['identity_api_url'])
            if (key == 'volume_api_url'):
                comp.setVolumeAPI(company_section['volume_api_url'])
            if (key == 'project'):
                # get list of all projects to calculate or 'all'
                tmp_list = company_section['project'].split(",")
                comp.setProjectList([item.strip() for item in tmp_list])
                #pp.pprint(comp.project)
        coefficients_section =\
            configSectionMap('Coefficients', config)
        for key, value in coefficients_section.items():
            if (key == 'active_coeff'):
                comp.setCoeff(float(
                    coefficients_section['active_coeff']),
                    'active',
                )
            if (key == 'shelve_coeff'):
                comp.setCoeff(float(
                    coefficients_section['shelve_coeff']),
                    'shelve'
                )
            if (key == 'stop_coeff'):
                comp.setCoeff(float(
                    coefficients_section['stop_coeff']),
                    'stop'
                )
            if (key == 'shelve_cpu_coeff'):
                comp.setCoeff(float(
                    coefficients_section['shelve_cpu_coeff']),
                    'shelve_cpu'
                )
            if (key == 'shelve_ram_coeff'):
                comp.setCoeff(float(
                    coefficients_section['shelve_ram_coeff']),
                    'shelve_ram'
                )
            if (key == 'shelve_disk_coeff'):
                comp.setCoeff(float(
                    coefficients_section['shelve_disk_coeff']),
                    'shelve_disk'
                )
            if (key == 'stop_cpu_coeff'):
                comp.setCoeff(float(
                    coefficients_section['stop_cpu_coeff']),
                    'stop_cpu'
                )
            if (key == 'stop_ram_coeff'):
                comp.setCoeff(float(
                    coefficients_section['stop_ram_coeff']),
                    'stop_ram'
                )
            if (key == 'stop_disk_coeff'):
                comp.setCoeff(float(
                    coefficients_section['stop_disk_coeff']),
                    'stop_disk'
                )
            if (key == 'active_cpu_coeff'):
                comp.setCoeff(float(
                    coefficients_section['active_cpu_coeff']),
                    'active_cpu'
                )
            if (key == 'active_ram_coeff'):
                comp.setCoeff(float(
                    coefficients_section['active_ram_coeff']),
                    'active_ram'
                )
            if (key == 'active_disk_coeff'):
                comp.setCoeff(float(
                    coefficients_section['active_disk_coeff']),
                    'active_disk'
                )
        hours_indicators_section =\
            configSectionMap('HoursIndicators', config)
        for key, value in hours_indicators_section.items():
            if (key == 'vcpuh'):
                comp.setVcpuh(float(hours_indicators_section['vcpuh']))
            if (key == 'ramh'):
                comp.setRamh(float(hours_indicators_section['ramh']))
            if ('diskh' in key):
                pattern = VOL_PFX + "_(\S+)"
                m = re.search(pattern, key)
                name = str(m.group(1))
                comp.setDiskh(float(hours_indicators_section[key]), name)
        conf_projects = (x for x in config.sections()
                         if x not in ('Company',
                                      'HoursIndicators',
                                      'Coefficients',
                                      )
                         )
        projects = dict()
        if (comp.getFirstProject() != 'all'):
            for proj in comp.getProjectList():
                project = Project(proj)
                project.setVcpuh(comp.getVcpuh())
                project.setRamh(comp.getRamh())
                project.setCoeff(comp.getCoeff())
                project.setDiskh(comp.getDiskh())
                projects[proj] = project
        for proj in conf_projects:
            # prepare list of all individually calculated projects
            try:
                p = configSectionMap(proj, config)
                #if (p['name'] in comp.project or
                #   comp.project[0].lower() == 'all'):
                # if element from conf projects belongs to company.project
                # names list then update company.project with coefficients
                if (p['name'] in list(projects.keys())):
                    for key, value in p.items():
                        if (key == 'vcpuh'):
                            projects[p['name']].setVcpuh(float(p['vcpuh']))
                        if (key == 'ramh'):
                            projects[p['name']].setRamh(float(p['ramh']))
                        if ('diskh' in key):
                            pattern = VOL_PFX + "_(\S+)"
                            m = re.search(pattern, key)
                            name = str(m.group(1))
                            projects[p['name']].setDiskh(float(p[name]), name)
                else:
                    if (comp.getFirstProject() == 'all'):
                        project = Project(p['name'])
                        for key, value in p.items():
                            if (key == 'vcpuh'):
                                project.setVcpuh(float(p['vcpuh']))
                            if (key == 'ramh'):
                                project.setRamh(float(p['ramh']))
                            #if (key == 'diskh'):
                            #    project.diskh = float(p['diskh'])
                            if ('diskh' in key):
                                pattern = VOL_PFX + "_(\S+)"
                                m = re.search(pattern, key)
                                name = str(m.group(1))
                                project.setDiskh(float(p[name]), name)
                        project.setCoeff(comp.getCoeff())
                        projects[p['name']] = project
            except KeyError as err:
                print("Project {0} doesn't have {1} attribute".
                      format(proj, err))
                pass
        #pp.pprint(comp.__dict__)
        #for p in projects:
        #    pp.pprint(p.__dict__)
        '''
        if (not projects):
            project = Project('all')
            project.vcpuh = comp.vcpuh
            project.diskh = comp.diskh
            project.ramh = comp.ramh
            project.coeff = comp.coeff
            projects.append(project)
        '''
        return comp, projects
    except KeyError as err:
        print("{0} is not defined for 'Company' section".format(err))
        sys.exit(-1)
    except Config.NoSectionError as ce:
        print("Config file error: {0}".format(ce))
        sys.exit(-1)


def main():
    args, parser = parse_args()
    username = ''
    password = ''
    company = None
    conf_projects = None
    start_time = ''
    end_time = ''
    out_file = ''
    save = False
    mongo = False
    sqlite = False
    mysql = False
    details = False
    as_admin = False
    volumes = False
    images = False
    if args.verbose:
        def verbose_print(*a, **k):
            if k.pop('level', 0) <= args.verbose:
                pprint(*a, **k)
    else:
        verbose_print = lambda *a, **k: None

    global __verbose_print
    __verbose_print = verbose_print
    __verbose_print(args, level=Verbosity.DEBUG)
    if (args.config_file):
        company, conf_projects = readConfigFile(args.config_file)
    else:
        message = ('Unable to read config file')
        #raise parser.error(message)
    if (args.username):
        username = args.username
    else:
        message = ('Unable to get user name')
        try:
            username = os.environ['OS_USERNAME']
            if (username is ''):
                raise parser.error(message)
        except KeyError:
            print("Unable to get user name with OS_USERNAME env variable")
            sys.exit(-19)
    if (args.passwd):
        password = args.passwd
    else:
        message = ('Unable to get user password')
        try:
            password = os.environ['OS_PASSWORD']
            if (password is ''):
                raise parser.error(message)
        except KeyError:
            print("Unable to get user pasword with OS_PASSWORD env variable")
            sys.exit(-20)
    if (args.start_time):
        #validate date
        message = ('Unable to validate start date')
        try:
            start_date = dup.parse(args.start_time)
            start_time = datetime.datetime.strptime(
                start_date.strftime('%Y%m%d'), '%Y%m%d')
        except:
            raise parser.error(message)
    else:
        message = ('Unable to validate start date')
        start_date = datetime.date.today() + relativedelta(months=-1)
        start_date = start_date.replace(day=1)
        start_date = start_date.replace(microsecond=0)
        start_time = datetime.datetime.strptime(
            start_date.strftime('%Y%m%d'), '%Y%m%d')
        if (start_time is ''):
            raise parser.error(message)
    if (args.end_time):
        try:
            message = ('Unable to validate end date')
            #validate date
            end_date = dup.parse(args.end_time)
            # hour to be set as 23:59 ?
            end_time = datetime.datetime.strptime(
                end_date.strftime('%Y%m%d'), '%Y%m%d')
            end_time = end_time.replace(hour=23,
                                        minute=59,
                                        second=59,
                                        microsecond=999999
                                        )
        except:
            raise parser.error(message)
    else:
        message = ('Unable to validate end date')
        #end_time = datetime.datetime.now()
        end_date = datetime.date.today() + relativedelta(months=-1)
        end_month = end_date.month
        end_year = end_date.year
        days = calendar.monthrange(end_year, end_month)[1]
        end_date = end_date.replace(day=days)
        # hour to be set as 23:59 ?
        end_time = datetime.datetime.strptime(
            end_date.strftime('%Y%m%d'), '%Y%m%d')
        end_time = end_time.replace(hour=23,
                                    minute=59,
                                    second=59,
                                    microsecond=999999)
        if (end_time is ''):
            raise parser.error(message)

    if (args.csv):
        out_file = args.csv
        save = True
    if (args.mysql):
        mysql = True
    if (args.sqlite):
        sqlite = True
    if (args.mongo):
        message = ('Unable to get mongo connection string. Please set OPAC_MONGO env variable')
        try:
            mongo_server = os.environ['OPAC_MONGO']
            if (mongo_server is ''):
                raise parser.error(message)
        except KeyError:
            print("Unable to get user name with OPAC_MONGO env variable")
            sys.exit(-19)
        mongo = True
    if (args.feature):
        details = True
    if (args.as_admin):
        as_admin = True
    if (args.volumes):
        volumes = True
    if (args.images):
        images = True
    '''
    try:
        users_file = args.all_users_projects[0]
    except ValueError:
        message = ('Users file name was not provided')
        raise parser.error(message)
    '''
    message = ('The start time cannot occur after the end time')
    if ((end_time - start_time).total_seconds() < 0):
        raise parser.error(message)
    #time_delta = (end_time - start_time).total_seconds() / 3600.0
    #if (not company or not conf_projects):
    if (not company or
       (not conf_projects and company.getFirstProject() != 'all')):
        sys.exit(-21)
    print("Company: '{0}':".format(company.getName()))
    print("Period: '{0}' - '{1}'".format(start_time, end_time))
    opac = OpenstackAccounting(username,
                               password,
                               start_time,
                               end_time,
                               company,
                               conf_projects,
                               as_admin)
    #pp.pprint(conf_projects)   
    opac.performAccounting()
    user_tenants = opac.getOSUsersProjects()
    projects = opac.updateOSUserProjectsWithConfig(user_tenants)
    servers = opac.getOSServers(projects,
                                user_tenants)

    try:
        if volumes:
            user_volumes = opac.getOSUsersVolumes(projects,
                                                  user_tenants)
            print("Calculating volumes...")
            for vol in user_volumes:
                seconds =\
                    opac.filterAndRecalculateStorageByDatetime(
                        vol.__dict__,
                        start_time=start_time,
                        end_time=end_time,
                        type='volumes',
                    )
                if seconds:
                    #pp.pprint(vol.__dict__)
                    storage = Storage(vol.name, vol.id, 'Volume')
                    storage.setState(vol.status)
                    storage.setProjectId(getattr(vol, VOL_TENANT_ID_ATTR))
                    storage.setProjectName(vol.tenant_name)
                    storage.setDisk(vol.size, 'value')
                    storage.setType(getattr(vol, VOL_TYPE))
                    storage.setHrs(seconds / 3600.0)
                    storage.setDisk(storage.getDisk('value')*storage.getHrs(), 'hours')
                    storage.setDisk(storage.getDisk('hours')*vol.diskh, 'cost')
                    if details:
                        print(storage)
                    company.addToVolumeList(storage)
                    company.addHrs(storage.getHrs())
                    company.addDisk(storage.getDisk('hours'), 'hours')
                    company.addDisk(storage.getDisk('cost'), 'cost')
                    company.addTotalCost(storage.getTotalCost())
        if images:
            user_images = opac.getOSUsersImages(projects,
                                                user_tenants)
            print("Calculating images...")
            for img in user_images:
                seconds =\
                    opac.filterAndRecalculateStorageByDatetime(
                        img.__dict__,
                        start_time=start_time,
                        end_time=end_time,
                        type='images',
                    )
                if seconds:
                    strg = img.__dict__
                    original = strg.get("__original__", "")
                    changes = strg.get("changes", "")
                    if original:
                        img_name = original.get("name", "")
                        img_id = original.get("id", "")
                        img_size = original.get("size", "0")
                        if not img_size:
                            img_size = 0
                        img_status = original.get("status", "")
                    if changes:
                        img_tenant_name = changes.get("tenant_name", "Unknown")
                        img_tenant_id = changes.get("tenant_id", "Unknown")
                        img_diskh = changes.get("diskh", "")
                    storage = Storage(img_name, img_id, 'Image')
                    storage.setState(img_status)
                    storage.setProjectId(img_tenant_id)
                    storage.setProjectName(img_tenant_name)
                    storage.setDisk(int(img_size) / (1024**3), 'value')
                    storage.setType(VOL_TYPE_STD)
                    storage.setHrs(seconds / 3600.0)
                    storage.setDisk(storage.getDisk('value')*storage.getHrs(),
                                    'hours')
                    storage.setDisk(storage.getDisk('hours')*img_diskh, 'cost')
                    if details:
                        print(storage)
                    company.addToImageList(storage)
                    company.addHrs(storage.getHrs())
                    company.addDisk(storage.getDisk('hours'), 'hours')
                    company.addDisk(storage.getDisk('cost'), 'cost')
                    company.addTotalCost(storage.getTotalCost())
        print("Calculating servers...")
        for server in servers:
            if (opac.filterServerByDatetime(server,
                                            start_time=start_time,
                                            end_time=end_time)):
                try:
                    s = Server(server.name)
                    s.setId(server.id)
                    s.setState(server.status)
                    s.setProjectId(server.tenant_id)
                    s.setProjectName(server.tenant_name)
                    auth = v3.Password(auth_url=company.getIdentityAPI(),
                                       username=opac.getUsername(),
                                       password=opac.getPassword(),
                                       user_domain_name='default',
                                       project_domain_name='default',
                                       project_id=None
                                       if opac.getAsAdmin()
                                       else s.getProjectId(),
                                       )
                    sess = session.Session(auth=auth)
                    nova = client.Client(API_VERSION,
                                         session=sess,
                                         )
                    if (hasattr(server, 'flavor')):
                        flavor = nova.flavors.get(server.flavor['id'])
                        if (flavor):
                            if (hasattr(server, 'image')):
                                if (server.image == INSTANCE_AT_VOLUME_STR):
                                    s.setDisk(0, 'value')
                                else:
                                    s.setDisk(float(flavor.disk), 'value')
                            else:
                                s.setDisk(0, 'value')
                            s.setCPU(float(flavor.vcpus), 'value')
                            s.setRAM(float(flavor.ram) / 1024.0, 'value')
                            actions = nova.instance_action.list(
                                server=s.getId())
                            actions = opac.filterActionsByDatetime(
                                actions,
                                start_time=start_time,
                                end_time=end_time)
                            if actions:
                                server_start = dup.parse(
                                    str(actions[0].start_time)
                                    ).replace(tzinfo=pytz.UTC)
                                server_end = dup.parse(
                                    str(end_time)
                                ).replace(tzinfo=pytz.UTC)
                                s.setHrs((
                                    server_end - server_start
                                    ).total_seconds() / 3600.0)
                                s.setDisk(
                                    s.getDisk('value')*s.getHrs(),
                                    'hours')
                                s.setCPU(s.getCPU('value')*s.getHrs(), 'hours')
                                s.setRAM(s.getRAM('value')*s.getHrs(), 'hours')
                                (stop_timeframes,
                                 shelve_timeframes,
                                 delete_timeframes) =\
                                    opac.getStopStartTimeFrames(
                                        actions,
                                        period_end_time=end_time
                                        )
                                s.updateHoursAndVolumes(
                                    stop_timeframes,
                                    shelve_timeframes,
                                    delete_timeframes,
                                    server.coeff,
                                )
                    s.updateMetricHoursWithActiveStatus(server.coeff)
                    s.setDisk(s.getDisk('hours')*getattr(server, VOL_PFX),
                              'cost')
                    s.setCPU(s.getCPU('hours')*server.vcpuh, 'cost')
                    s.setRAM(s.getRAM('hours')*server.ramh, 'cost')
                    if details:
                        print(s)
                    company.addToServerList(s)
                    company.addHrs(s.getHrs())
                    company.addCPU(s.getCPU('hours'), 'hours')
                    company.addCPU(s.getCPU('cost'), 'cost')
                    company.addRAM(s.getRAM('hours'), 'hours')
                    company.addRAM(s.getRAM('cost'), 'cost')
                    company.addDisk(s.getDisk('hours'), 'hours')
                    company.addDisk(s.getDisk('cost'), 'cost')
                    company.addTotalCost(s.getTotalCost())
                except NotFound:
                    print("Flavour not found. Check if server flavor \
                          is set to public")
                    pass
    #except NotFound:
    #    print("Flavour not found. Check if server flavor is set to public")
    #    pass
    except KeyError as ke:
        print("Object doesn't contain {0} attribute".
              format(ke))
        sys.exit(-23)
    except Exception as e:
        print("Unexpected error: {0}".format(e))
        sys.exit(-24)
    print("Aggregation:")
    print("\tTotal Hours: {0:.2f}".format(company.getHrs()))
    print("\tCPU Hours: {0:.2f}".format(company.getCPU('hours')))
    print("\tCPU Hours cost: {0:.2f}".format(company.getCPU('cost')))
    print("\tRAM GB-Hours: {0:.2f}".format(company.getRAM('hours')	))
    print("\tRAM GB-Hours cost: {0:.2f}".
          format(company.getRAM('cost')	))
    print("\tDisk GB-Hours: {0:.2f}".format(company.getDisk('hours')))
    print("\tDisk GB-Hours cost: {0:.2f}".format(company.getDisk('cost')))
    print("\tTotal cost: {0:.2f}".format(company.getTotalCost()))
    if save:
        print("Saving to file {0}".format(out_file))
        company.saveCSV(out_file, start_time, end_time, details)
    if mysql:
        print("Saving to MySQL db {0} {1}".format(start_time, end_time))
        company.saveMySQL(start_time, end_time)
    if sqlite:
        print("Saving to SQLite db {0} {1}".format(start_time, end_time))
        company.saveSQLite(start_time, end_time)
    if mongo:
        print("Saving to MongoDB: {0}".format(mongo_server))
        company.saveMongo(start_time, end_time, mongo_server, details)
