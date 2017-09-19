#!/usr/bin/python3
import os
import pprint
from novaclient import client
from keystoneclient.v2_0 import client as ks
from keystoneauth1 import loading
from keystoneauth1 import session
import datetime
import calendar
from oslo_utils import timeutils
from dateutil.relativedelta import relativedelta
import dateutil.parser as dup
import argparse
import configparser as Config
from keystoneclient.exceptions import AuthorizationFailure, Unauthorized
import csv
#import requests.packages.urllib3
#requests.packages.urllib3.disable_warnings()

__author__ = 'Damian Kaliszan'


class Server(object):
    def __init__(self, name):
        self.name = name
        self.id = ''
        self.hrs = 0.0
        self.hrs_updated = 0.0
        #self.ram = 0.0
        self.vcpus = 0.0
        self.vcpus_updated = 0.0
        self.vcpu_cost = 0.0
        self.vcpu_cost_updated = 0.0
        self.gb = 0.0
        self.gb_updated = 0.0
        self.gb_cost = 0.0
        self.gb_cost_updated = 0.0
        self.state = 'active'

    def __str__(self):
        str = "Server name: {0} ({1})\n" \
              "\tHours: {2:.2f}\n" \
              "\tHours updated: {3:.2f}\n" \
              "\tCPU Hours: {4:.2f}\n" \
              "\tCPU Hours updated: {5:.2f}\n" \
              "\tCPU Hours cost: {6:.2f}\n" \
              "\tCPU Hours cost updated: {7:.2f}\n" \
              "\tDisk GB-Hours: {8:.2f}\n" \
              "\tDisk GB-Hours updated: {9:.2f}\n" \
              "\tDisk GB-Hours cost: {10:.2f}\n" \
              "\tDisk GB-Hours cost updated: {11:.2f}"
        return str.format(self.name,
                          self.id,
                          self.hrs,
                          self.hrs_updated,
                          self.vcpus,
                          self.vcpus_updated,
                          self.vcpu_cost,
                          self.vcpu_cost_updated,
                          self.gb,
                          self.gb_updated,
                          self.gb_cost,
                          self.gb_cost_updated)

    def updateHoursAndVolumes(self,
                              stop_timeframes,
                              shelve_timeframes,
                              stop_coeff,
                              shelve_coeff,
                              local_gb,
                              local_vcpus):
        self.hrs_updated = self.hrs
        self.gb_updated = self.gb
        self.vcpus_updated = self.vcpus
        if (stop_timeframes is not None):
            if (self.hrs_updated > 0):
                for hours in stop_timeframes:
                    self.hrs_updated -= hours*(1.0 - stop_coeff)
                    self.vcpus_updated -=\
                        local_vcpus*hours*(1.0 - stop_coeff)
                    self.gb_updated -=\
                        local_gb*hours*(1.0 - stop_coeff)
        if (shelve_timeframes is not None):
            if (self.hrs_updated > 0):
                for hours in shelve_timeframes:
                    self.hrs_updated -= hours*(1.0 - shelve_coeff)
                    self.vcpus_updated -=\
                        local_vcpus*hours*(1.0 - shelve_coeff)
                    self.gb_updated -=\
                        local_gb*hours*(1.0 - shelve_coeff)


class Company(object):
    def __init__(self, name):
        self.name = name
        self.url = ''
        self.hrs = 0.0
        self.hrs_updated = 0.0
        #self.ram = 0.0
        self.vcpus = 0.0
        self.vcpus_updated = 0.0
        self.vcpuh = 0.0
        self.vcpu_cost = 0.0
        self.vcpu_cost_updated = 0.0
        self.gb = 0.0
        self.gb_updated = 0.0
        self.gbh = 0.0
        self.gb_cost = 0.0
        self.gb_cost_updated = 0.0
        self.shelve_coeff = 0.0
        self.stop_coeff = 0.0
        self.server = []

    def saveCSV(self, filename, start_time, end_time, details=False):
        with open(filename, 'w') as csvfile:
            fieldnames = ['Company name',
                          'Start date',
                          'End date',
                          'Total hours',
                          'Total hours updated',
                          'CPU Hours',
                          'CPU Hours updated',
                          'CPU Hours cost',
                          'CPU Hours cost updated',
                          'Disk GB-Hours',
                          'Disk GB-Hours updated',
                          'Disk GB-Hours cost',
                          'Disk GB-Hours cost updated']
            writer = csv.DictWriter(csvfile,
                                    fieldnames=fieldnames,
                                    delimiter=';')
            writer.writeheader()
            writer.writerow({fieldnames[0]: self.name,
                             fieldnames[1]: start_time,
                             fieldnames[2]: end_time,
                             fieldnames[3]:
                             str(round(self.hrs, 2)).
                             replace('.', ','),
                             fieldnames[4]:
                             str(round(self.hrs_updated, 2)).
                             replace('.', ','),
                             fieldnames[5]:
                             str(round(self.vcpus, 2)).
                             replace('.', ','),
                             fieldnames[6]:
                             str(round(self.vcpus_updated, 2)).
                             replace('.', ','),
                             fieldnames[7]:
                             str(round(self.vcpu_cost, 2)).
                             replace('.', ','),
                             fieldnames[8]:
                             str(round(self.vcpu_cost_updated, 2)).
                             replace('.', ','),
                             fieldnames[9]:
                             str(round(self.gb, 2)).
                             replace('.', ','),
                             fieldnames[10]:
                             str(round(self.gb_updated, 2)).
                             replace('.', ','),
                             fieldnames[11]:
                             str(round(self.gb_cost, 2)).
                             replace('.', ','),
                             fieldnames[12]:
                             str(round(self.gb_cost_updated, 2)).
                             replace('.', ',')})
        if details:
            with open(filename, 'a') as csvfile:
                fieldnames = ['Server name',
                              'Start date',
                              'End date',
                              'Hours',
                              'Hours updated',
                              'CPU Hours',
                              'CPU Hours updated',
                              'CPU Hours cost',
                              'CPU Hours cost updated',
                              'Disk GB-Hours',
                              'Disk GB-Hours updated',
                              'Disk GB-Hours cost',
                              'Disk GB-Hours cost updated']
                writer = csv.DictWriter(csvfile,
                                        fieldnames=fieldnames,
                                        delimiter=';')
                writer.writerow({})
                writer.writeheader()
                for server in self.server:
                    name = "{0} ({1})".format(server.name, server.id)
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: start_time,
                                    fieldnames[2]: end_time,
                                    fieldnames[3]: str(round(server.hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[4]:
                                    str(round(server.hrs_updated, 2)).
                                    replace('.', ','),
                                    fieldnames[5]: str(round(server.vcpus, 2)).
                                    replace('.', ','),
                                    fieldnames[6]:
                                    str(round(server.vcpus_updated, 2)).
                                    replace('.', ','),
                                    fieldnames[7]: str(round(
                                        server.vcpu_cost, 2)).
                                    replace('.', ','),
                                    fieldnames[8]: str(round(
                                        server.vcpu_cost_updated, 2)).
                                    replace('.', ','),
                                    fieldnames[9]: str(round(
                                        server.gb, 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        server.gb_updated, 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        server.gb_cost, 2)).
                                    replace('.', ','),
                                    fieldnames[12]: str(round(
                                        server.gb_cost_updated, 2)).
                                    replace('.', ',')})


def configSectionMap(section, config=None):
    dict1 = {}
    options = config.options(section)
    for option in options:
        try:
            dict1[option] = config.get(section, option)
            if dict1[option] == -1:
                print("skip: %s" % option)
        except:
            print("exception on %s!" % option)
            dict1[option] = None
    return dict1


def filterAcionsByDateTime(actions, start_time=None, end_time=None):
    #print("{0} - {1}".format(start_time, end_time))
    if actions:
        mydict = {'0': start_time, '1': end_time}
        for key, date in sorted(mydict.items()):
            filtered_actions = []
            for action, next_action in zip(actions, actions[1:]):
                start_time_1 = dup.parse(str(action.start_time))
                start_time_2 = dup.parse(str(next_action.start_time))
                if (key == '0' and date is not None):
                    start_diff_1 = (start_time_1 - date).total_seconds()
                    start_diff_2 = (start_time_2 - date).total_seconds()
                    if (start_diff_1 > 0.0 and start_diff_2 > 0.0):
                        #print("Dodaje 0 {0}".format(action.action))
                        filtered_actions.append(action)
                    elif (start_diff_1 < 0.0 and start_diff_2 > 0.0):
                        action.start_time = start_time
                        filtered_actions.append(action)
                        #print("Dodaje 1 {0}".format(action.action))
                elif (key == '1' and date is not None):
                    end_diff_1 = (start_time_1 - date).total_seconds()
                    end_diff_2 = (start_time_2 - date).total_seconds()
                    if (end_diff_1 < 0.0 and end_diff_2 < 0.0):
                        filtered_actions.append(action)
                    elif (end_diff_1 < 0.0 and end_diff_2 > 0.0):
                        next_action.start_time = end_time
                        filtered_actions.append(action)
                        #print("Dodaje 2 {0}".format(action.action))
                        filtered_actions.append(next_action)
                        #print("Dodaje 3 {0}".format(next_action.action))
                        #return filtered_actions
            actions = filtered_actions
    return actions


def getStopStartTimeFrames(actions):
    states = {'stop': 'start',
              'shelve': 'unshelve'}
    stop_list = list(states.keys())
    start_list = list(states.values())
    stop_action = None
    stop_timeframes = []
    shelve_timeframes = []
    for saction in actions:
        #print("{0}\t{1}".format(saction.action, saction.start_time))
        if (saction.action in stop_list and
           stop_action is None):
            stop_action = saction
        if (stop_action):
            if (saction.action in start_list and stop_action and
                states[stop_action.action] == saction.action and
               stop_action is not None):
                #print("{0}\t{1}".format(stop_action.start_time,
                #      saction.start_time))
                start_time = timeutils.parse_isotime(stop_action.start_time)
                end_time = timeutils.parse_isotime(saction.start_time)
                tdiff = (end_time - start_time).total_seconds() / 3600.0
                #print(tdiff)
                if (saction.action == 'start'):
                    stop_timeframes.append(tdiff)
                if (saction.action == 'unshelve'):
                    shelve_timeframes.append(tdiff)
                stop_action = None
    return stop_timeframes, shelve_timeframes

if __name__ == '__main__':
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
    parser.add_argument('-s', '--start_time',
                        nargs='?',
                        help='Start date  in YYYY-MM-DD format. If not given'
                        ' the first day of last month is taken')
    # Optional  argument
    parser.add_argument('-e', '--end_time',
                        nargs='?',
                        help='End date in YYYY-MM-DD format. If not given'
                        ' the lst day of last month is taken')

    # Optional  argument
    parser.add_argument('-o', '--output_file',
                        nargs='?',
                        help='Output CSV file name')

    # Optional  argument
    parser.add_argument('--details',
                        dest='feature',
                        action='store_true',
                        help="Enables accounting 'by server' feature")
    parser.add_argument('--no-details',
                        dest='feature',
                        action='store_false',
                        help="Disables accounting 'by server' "
                        "feature (default)")

    # Parse args
    #args = parser.parse_args()
    args, extra = parser.parse_known_args()
    username = ''
    password = ''
    config = None
    start_time = ''
    end_time = ''
    out_file = ''
    save = False
    details = False
    if (args.config_file):
        config = Config.ConfigParser()
        config.read(args.config_file)
    else:
        message = ('Unable to read config file')
        raise parser.error(message)
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
            os._exit(1)
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
            os._exit(1)
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
            end_time = end_time.replace(hour=23, minute=59, second=59)
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
        end_time = end_time.replace(hour=23, minute=59, second=59)
        if (end_time is ''):
            raise parser.error(message)
    if (args.output_file):
        out_file = args.output_file
        save = True
    message = ('The start time cannot occur after the end time')
    if (end_time < start_time):
        raise parser.error(message)
    if (args.feature):
        details = True
    pp = pprint.PrettyPrinter(indent=4)
    project_id = ''
    tenants = None
    company = None
    company_name = ''
    try:
        company_section = configSectionMap('Company', config)
        company_name = company_section['name']
        company = Company(company_name)
        company.shelve_coeff = float(company_section['shelve_coeff'])
        company.stop_coeff = float(company_section['stop_coeff'])
        for key, value in company_section.items():
            if (key == 'url'):
                company.url = company_section['url']
            if (key == 'vcpuh'):
                company.vcpuh = float(company_section['vcpuh'])
            if (key == 'gbh'):
                company.gbh = float(company_section['gbh'])
    except KeyError as err:
        print("{0} is not defined for 'Company' section".format(err))
        os._exit(1)
    except Config.NoSectionError as ce:
        print("Config file error: {0}".format(ce))
        os._exit(1)
    projects = (x for x in config.sections() if x not in 'Company')
    print("Company: '{0}':".format(company.name))
    print("Period: '{0}' - '{1}'".format(start_time, end_time))
    for proj in projects:
        #print(company)
        #projects
        try:
            project = configSectionMap(proj, config)
            url = company.url
            vcpuh = company.vcpuh
            gbh = company.gbh
            for key, value in project.items():
                if (key == 'url'):
                    url = project['url']
                if (key == 'name'):
                    project_name = project['name']
                if (key == 'vcpuh'):
                    vcpuh = float(project['vcpuh'])
                if (key == 'gbh'):
                    gbh = float(project['gbh'])
        except KeyError as err:
            print("Unexpected error: {0}".format(err))
        try:
            #get tenants for given user
            ksclient = ks.Client(username=username,
                                 password=password,
                                 auth_url=url)
            ksdata = ksclient.tenants.list()
            dir(ksdata)
            tenants = dict((x.name, x.id) for x in ksdata)
            #pp.pprint(tenants)
            if tenants is None:
                raise ValueError
            project_id = tenants[project_name]
            #auth with nova
            version = '2'
            loader = loading.get_plugin_loader('password')
            auth = loader.load_from_options(auth_url=url,
                                            username=username,
                                            password=password,
                                            project_name=project_name)
            sess = session.Session(auth=auth)
            nova = client.Client(version, session=sess)
            data = nova.usage.get(tenant_id=project_id,
                                  start=start_time,
                                  end=end_time)
            #pp.pprint(data.__dict__)
            dir(data)
        except KeyError as ke:
            print("Project {0} unavailable for given username".
                  format(ke))
            os._exit(1)
        except ValueError as ve:
            print("Error parsing projects for given username: {1}".
                  format(ve))
            os._exit(1)
        except AuthorizationFailure as auf:
            print("Error for {0} auth: {1}".format(username, auf.message))
            os._exit(1)
        except Unauthorized as unauth:
            print("Error for {0} auth: {1}"
                  .format(username, unauth.message))
            os._exit(1)
        try:
            if (details):
                for server in data.server_usages:
                    s_name = server['name']
                    s = Server(s_name)
                    s.id = server['instance_id']
                    s.state = server['state']
                    #s.hrs_updated = s.hrs = float(server['hours'])
                    #s.gb_updated = s.gb = float(server['local_gb'])*s.hrs
                    #s.vcpus_updated = s.vcpus = float(server['vcpus'])*s.hrs
                    s.hrs = float(server['hours'])
                    s.gb = float(server['local_gb'])*s.hrs
                    s.vcpus = float(server['vcpus'])*s.hrs
                    s.hrs_updated = s.hrs
                    s.gb_updated = s.gb
                    s.vcpus_updated = s.vcpus
                    #dir(data)
                    if (s.state == 'active'):
                        actions = nova.instance_action.list(server=s.id)
                        if (actions is not None):
                            actions = list(reversed(actions))
                            actions = filterAcionsByDateTime(
                                actions,
                                start_time=start_time,
                                end_time=end_time)
                            stop_timeframes, shelve_timeframes =\
                                getStopStartTimeFrames(actions)
                            #pp.pprint(stop_timeframes)
                            #pp.pprint(shelve_timeframes)
                            if ((stop_timeframes is not None) or
                               (shelve_timeframes is not None)):
                                s.updateHoursAndVolumes(
                                    stop_timeframes,
                                    shelve_timeframes,
                                    company.stop_coeff,
                                    company.shelve_coeff,
                                    float(server['local_gb']),
                                    float(server['vcpus']))
                    s.gb_cost = s.gb*gbh
                    s.gb_cost_updated = s.gb_updated*gbh
                    s.vcpu_cost = s.vcpus*vcpuh
                    s.vcpu_cost_updated = s.vcpus_updated*vcpuh
                    print(s)
                    #pp.pprint(server)
                    company.server.append(s)
                    company.hrs_updated += s.hrs_updated
                    company.gb_updated += s.gb_updated
                    company.vcpus_updated += s.vcpus_updated
                    company.gb_cost_updated += s.gb_cost_updated
                    company.vcpu_cost_updated += s.vcpu_cost_updated
            if hasattr(data, 'server_usages'):
                hrs = float(data.total_hours)
                gb = float(data.total_local_gb_usage)
                ram = float(data.total_memory_mb_usage)
                cpu = float(data.total_vcpus_usage)
            else:
                hrs = gb = ram = cpu = 0.0
            company.hrs += hrs
            company.gb += gb
            company.vcpus += cpu
            company.vcpu_cost += cpu*vcpuh
            company.gb_cost += gb*gbh
            #ram skipped
        except:
            os._exit(1)
    print("Aggregation:")
    print("\tTotal Hours: {0:.2f}".format(company.hrs))
    print("\tTotal Hours Updated: {0:.2f}".format(company.hrs_updated))
    print("\tCPU Hours: {0:.2f}".format(company.vcpus))
    print("\tCPU Hours Updated: {0:.2f}".format(company.vcpus_updated))
    print("\tDisk GB-Hours: {0:.2f}".format(company.gb))
    print("\tDisk GB-Hours Updated: {0:.2f}".format(company.gb_updated))
    print("\tCPU Hours cost: {0:.2f}".format(company.vcpu_cost))
    print("\tCPU Hours cost updated: {0:.2f}".
          format(company.vcpu_cost_updated))
    print("\tDisk GB-Hours cost: {0:.2f}".format(company.gb_cost))
    print("\tDisk GB-Hours cost updated: {0:.2f}".
          format(company.gb_cost_updated))
    if save:
        print("Saving to {0}".format(out_file))
        company.saveCSV(out_file, start_time, end_time, details)
