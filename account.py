#!/usr/bin/python3
import os
import pprint
from novaclient import client
from novaclient.exceptions import Forbidden
#from novaclient import extension
#from novaclient.v2.contrib import instance_action
#from keystoneclient.v2_0 import client as ks
#from keystoneauth1.identity import v3
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

__author__ = 'Damian Kaliszan'


class AccountData(object):
    def __init__(self):
        self.hrs = 0.0
        self.ram = 0.0
        self.ram_hrs = 0.0
        self.ram_cost = 0.0
        self.vcpus = 0.0
        self.vcpus_hrs = 0.0
        self.vcpu_cost = 0.0
        self.gb = 0.0
        self.gb_hrs = 0.0
        self.gb_cost = 0.0
        self.total_cost = 0.0

    def __repr__(self):
        return "<AccountData>"


class Server(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        self.name = name
        self.id = ''
        self.state = 'active'

    def __str__(self):
        str = "Server name: {0} ({1})\n" \
              "\tHours: {2:.2f}\n" \
              "\tCPU Hours: {3:.2f}\n" \
              "\tCPU Hours cost: {4:.2f}\n" \
              "\tRAM GB-Hours: {5:.2f}\n" \
              "\tRAM GB-Hours cost: {6:.2f}\n" \
              "\tDisk GB-Hours: {7:.2f}\n" \
              "\tDisk GB-Hours cost: {8:.2f}\n" \
              "\tServer total cost: {9:.2f}\n"
        return str.format(self.name,
                          self.id,
                          self.hrs,
                          self.vcpus_hrs,
                          self.vcpu_cost,
                          self.ram_hrs,
                          self.ram_cost,
                          self.gb_hrs,
                          self.gb_cost,
                          self.totalCost())

    def updateHoursAndVolumes(self,
                              stop_timeframes,
                              shelve_timeframes,
                              delete_timeframes,
                              stop_coeff,
                              shelve_coeff):
        if delete_timeframes:
            for hours in delete_timeframes:
                self.hrs -= hours
                self.gb_hrs -= self.gb*hours
                self.vcpus_hrs -= self.vcpus*hours
                self.ram_hrs -= self.ram*hours
            if (self.hrs == 0.0):
                self.vcpus_hrs = self.ram_hrs = self.gb_hrs = 0.0
        if stop_timeframes:
            for hours in stop_timeframes:
                self.hrs -= hours
                self.vcpus_hrs -=\
                    self.vcpus*hours*(1.0 - stop_coeff)
                self.ram_hrs -=\
                    self.ram*hours*(1.0 - stop_coeff)
            if (self.hrs == 0.0):
                self.vcpus_hrs = self.ram_hrs = self.gb_hrs = 0.0
        if shelve_timeframes:
            for hours in shelve_timeframes:
                self.hrs -= hours
                self.vcpus_hrs -=\
                    self.vcpus*hours*(1.0 - shelve_coeff)
                self.ram_hrs -=\
                    self.ram*hours*(1.0 - shelve_coeff)
            if (self.hrs == 0.0):
                self.vcpus_hrs = self.ram_hrs = self.gb_hrs = 0.0

    def totalCost(self):
        try:
            self.total_cost = max(self.vcpu_cost,
                                  self.ram_cost) +\
                self.gb_cost
        except Exception as e:
            print("Error {0}".format(e))
            return 0.0
        return self.total_cost


class Company(object):
    def __init__(self, name):
        AccountData.__init__(self)
        self.name = name
        self.url = ''
        self.shelve_coeff = 0.0
        self.stop_coeff = 0.0
        self.server = []

    def saveCSV(self, filename, start_time, end_time, details=False):
        with open(filename, 'w') as csvfile:
            fieldnames = ['Company name',
                          'Start date',
                          'End date',
                          'Total hours',
                          'CPU-Hours',
                          'CPU-Hours cost',
                          "RAM GB-Hours",
                          "RAM GB-Hours cost",
                          'Disk GB-Hours',
                          'Disk GB-Hours cost',
                          'Total cost']
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
                             str(round(self.vcpus_hrs, 2)).
                             replace('.', ','),
                             fieldnames[5]:
                             str(round(self.vcpu_cost, 2)).
                             replace('.', ','),
                             fieldnames[6]:
                             str(round(self.ram_hrs, 2)).
                             replace('.', ','),
                             fieldnames[7]:
                             str(round(self.ram_cost, 2)).
                             replace('.', ','),
                             fieldnames[8]:
                             str(round(self.gb_hrs, 2)).
                             replace('.', ','),
                             fieldnames[9]:
                             str(round(self.gb_cost, 2)).
                             replace('.', ','),
                             fieldnames[10]:
                             str(round(self.total_cost, 2)).
                             replace('.', ',')})
        if details:
            with open(filename, 'a') as csvfile:
                fieldnames = ['Server name',
                              'Start date',
                              'End date',
                              'Hours',
                              'CPU-Hours',
                              'CPU-Hours cost',
                              'RAM GB-Hours',
                              'RAM GB-Hours cost',
                              'Disk GB-Hours',
                              'Disk GB-Hours cost',
                              'Total cost']
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
                                    str(round(server.vcpus_hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[5]: str(round(
                                        server.vcpu_cost, 2)).
                                    replace('.', ','),
                                    fieldnames[6]:
                                    str(round(server.ram_hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[7]: str(round(
                                        server.ram_cost, 2)).
                                    replace('.', ','),
                                    fieldnames[8]: str(round(
                                        server.gb_hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[9]: str(round(
                                        server.gb_cost, 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        server.totalCost(), 2)).
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
            print("Exception on {0}!".format(option))
            dict1[option] = None
    return dict1


def filterActionsByDateTime(actions, start_time=None, end_time=None):
    if actions:
        mydict = {'0': start_time, '1': end_time}
        for key, date in sorted(mydict.items()):
            #actions = list(reversed(actions))
            filtered_actions = actions
            #pp.pprint(filtered_actions)
            for i, item in enumerate(filtered_actions):
                start_time = dup.parse(str(item.start_time))
                if (key == '0' and date is not None):
                    start_diff = (start_time - date).total_seconds()
                    #print(start_diff)
                    #find first time earlier than start_time
                    if (start_diff < 0.0):
                        filtered_actions[i].start_time = date
                        filtered_actions = filtered_actions[0:i+1]
                        break
                elif (key == '1' and date is not None):
                    end_diff = (start_time - date).total_seconds()
                    if (end_diff > 0.0):
                        filtered_actions = filtered_actions[0:i]
                        break
            actions = list(reversed(filtered_actions))
        return filtered_actions
    return actions


def getStopStartTimeFrames(actions, period_end_time):
    states = {'stop': 'start',
              'shelve': 'unshelve',
              'delete': ''}
    stop_list = list(states.keys())
    start_list = list(states.values())
    stop_action = None
    stop_timeframes = []
    shelve_timeframes = []
    delete_timeframes = []
    for i, saction in enumerate(actions):
        '''
        if (saction.message):
            print("if (saction.message) %s" % saction.action)
        if not saction.message:
            print("if (not saction.message) %s" % saction.action)
        if (saction.message is None):
            print("saction.message is None %s" % saction.action)
        if (saction.message is not None):
            print("saction.message is not None %s" % saction.action)
        print("Message {0}".format(saction.message))
        '''
        #if successfull the message is empty
        if (saction.action in stop_list and
           stop_action is None and not saction.message):
            stop_action = saction
        if (stop_action):
            if (saction.action in start_list and
                states[stop_action.action] == saction.action and
               stop_action is not None and not saction.message):
                #print("{0}\t{1}".format(stop_action.start_time,
                #      saction.start_time))
                #print("Odejmuje11")
                #start_time = timeutils.parse_isotime(stop_action.start_time)
                #end_time = timeutils.parse_isotime(saction.start_time)
                start_time = dup.parse(str(stop_action.start_time))
                end_time = dup.parse(str(saction.start_time))
                #print("Odejmuje")
                tdiff = (end_time - start_time).total_seconds() / 3600.0
                #print(tdiff)
                if (saction.action == 'start'):
                    stop_timeframes.append(tdiff)
                if (saction.action == 'unshelve'):
                    shelve_timeframes.append(tdiff)
                stop_action = None
            #just in case stop action is the last action in the list
            elif (i == len(actions) - 1):
                end_time = dup.parse(str(period_end_time))
                start_time = dup.parse(str(stop_action.start_time))
                #print("Odejmuje22 {0} {1}".format(end_time, start_time))
                #start_time = timeutils.parse_isotime(stop_action.start_time)
                #print("Odejmuje2")
                tdiff = (end_time - start_time).total_seconds() / 3600.0
                #print(tdiff)
                if (stop_action.action == 'delete'):
                    delete_timeframes.append(tdiff)
                if (stop_action.action == 'stop'):
                    stop_timeframes.append(tdiff)
                if (stop_action.action == 'shelve'):
                    shelve_timeframes.append(tdiff)
    return stop_timeframes, shelve_timeframes, delete_timeframes

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
    if ((end_time - start_time).total_seconds() < 0):
        raise parser.error(message)
    if (args.feature):
        details = True
    pp = pprint.PrettyPrinter(indent=4)
    project_id = ''
    tenants = None
    company = None
    company_name = ''
    '''
    utc_zone = tz.gettz('UTC')
    local_zone = tz.tzlocal()
    start_time = start_time.replace(tzinfo=local_zone)
    start_time = start_time.astimezone(utc_zone)
    end_time = end_time.replace(tzinfo=local_zone)
    end_time = end_time.astimezone(utc_zone)
    utc_start_string = start_time.strftime('%Y-%m-%d %H:%M:%S')
    utc_end_string = end_time.strftime('%Y-%m-%d %H:%M:%S')
    start_time = datetime.datetime.strptime(utc_start_string,
                 '%Y-%m-%d %H:%M:%S')
    end_time = datetime.datetime.strptime(utc_end_string, '%Y-%m-%d %H:%M:%S')
    '''
    time_delta = (end_time - start_time).total_seconds() / 3600.0
    #print("DELTA {0}".format(time_delta))
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
            if (key == 'ramh'):
                company.ramh = float(company_section['ramh'])
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
        #projects
        try:
            project = configSectionMap(proj, config)
            url = company.url
            vcpuh = company.vcpuh
            gbh = company.gbh
            ramh = company.ramh
            project_name = project['name']
            for key, value in project.items():
                if (key == 'url'):
                    url = project['url']
                #if (key == 'name'):
                #    project_name = project['name']
                if (key == 'vcpuh'):
                    vcpuh = float(project['vcpuh'])
                if (key == 'gbh'):
                    gbh = float(project['gbh'])
                if (key == 'ramh'):
                    ramh = float(project['ramh'])
        except KeyError as err:
            #print("Project {0} doesn't have {1} attribute".format(proj, err))
            continue
        try:
            #get tenants for given user
            opts = loading.get_plugin_loader('password')
            loader = loading.get_plugin_loader('password')
            auth = loader.load_from_options(auth_url=url,
                                            username=username,
                                            password=password,
                                            project_id=project_id,
                                            )
            sess = session.Session(auth=auth)
            ksclient = ks.Client(session=sess,)
            ksdata = ksclient.tenants.list()
            dir(ksdata)
            tenants = dict((x.name, x.id) for x in ksdata)
            #pp.pprint(tenants)
            if tenants is None:
                raise ValueError
            project_id = tenants[project_name]
            #auth with nova
            VERSION = '2.21'
            auth = loader.load_from_options(auth_url=url,
                                            username=username,
                                            password=password,
                                            project_id=project_id,
                                            )
            sess = session.Session(auth=auth)
            nova = client.Client(VERSION,
                                 session=sess,
                                 )
            servers = nova.servers.list()
            servers_deleted = nova.servers.list(
                search_opts={'status': 'unknown'}
                )
            #pp.pprint(servers_deleted)
            servers = servers + servers_deleted
            #pp.pprint(servers)
            '''
            data = nova.usage.get(tenant_id=project_id,
                                  start=start_time,
                                  end=end_time)
            dir(data)
            '''
        except Forbidden as fb:
            print("There was a problem: {0}".format(fb))
        except KeyError as ke:
            print("Project {0} unavailable for given username".
                  format(ke))
            os._exit(1)
        except ValueError as ve:
            print("Error parsing projects for given username: {1}".
                  format(ve))
            os._exit(1)
        except AuthorizationFailure as auf:
            print("Error for {0} auth: {1}".format(username, auf))
            os._exit(1)
        except Unauthorized as unauth:
            print("Error for {0} auth: {1}"
                  .format(username, unauth.message))
            os._exit(1)
        try:
            print("Number of servers: {0}".format(len(servers)))
            '''
            for server in data.server_usages:
                s_name = server['name']
                s = Server(s_name)
                s.id = server['instance_id']
                s.state = server['state']
                s.gb = float(server['local_gb'])
                s.vcpus = float(server['vcpus'])
                s.ram = float(server['memory_mb']) / 1024.0
            '''
            for server in servers:
                s = Server(server.name)
                s.id = server.id
                s.status = server.status
                flavor = nova.flavors.get(server.flavor['id'])
                if (flavor):
                    #pp.pprint(flavor.__dict__)
                    s.gb = float(flavor.disk)
                    s.vcpus = float(flavor.vcpus)
                    s.ram = float(flavor.ram) / 1024.0
                    actions = nova.instance_action.list(server=s.id)
                    actions = filterActionsByDateTime(
                        actions,
                        start_time=start_time,
                        end_time=end_time)
                    if actions:
                        server_start = dup.parse(
                            str(actions[0].start_time)
                            )
                        server_end = dup.parse(str(end_time))
                        s.hrs = (
                            server_end - server_start
                            ).total_seconds() / 3600.0
                        s.gb_hrs = s.gb*s.hrs
                        s.vcpus_hrs = s.vcpus*s.hrs
                        s.ram_hrs = s.ram*s.hrs
                        #pp.pprint(s.__dict__)
                        (stop_timeframes,
                         shelve_timeframes,
                         delete_timeframes) =\
                            getStopStartTimeFrames(actions,
                                                   period_end_time=
                                                   end_time)
                        #pp.pprint(stop_timeframes)
                        #pp.pprint(shelve_timeframes)
                        #pp.pprint(delete_timeframes)
                        if (stop_timeframes or
                           shelve_timeframes or
                           delete_timeframes):
                            s.updateHoursAndVolumes(
                                stop_timeframes,
                                shelve_timeframes,
                                delete_timeframes,
                                company.stop_coeff,
                                company.shelve_coeff)
                s.gb_cost = s.gb_hrs*gbh
                s.vcpu_cost = s.vcpus_hrs*vcpuh
                s.ram_cost = s.ram_hrs*ramh
                if details:
                    print(s)
                company.server.append(s)
                company.hrs += s.hrs
                company.vcpus_hrs += s.vcpus_hrs
                company.vcpu_cost += s.vcpu_cost
                company.ram_hrs += s.ram_hrs
                company.ram_cost += s.ram_cost
                company.total_cost += s.totalCost()
                company.gb_hrs += s.gb_hrs
                company.gb_cost += s.gb_cost
        except KeyError as ke:
            print("Server doesn't contain {0} attribute".
                  format(ke))
            os._exit(1)
        except Exception as e:
            print("Unexpected error: {0}".format(e))
            os._exit(1)
    print("Aggregation:")
    print("\tTotal Hours: {0:.2f}".format(company.hrs))
    print("\tCPU Hours: {0:.2f}".format(company.vcpus_hrs))
    print("\tCPU Hours cost: {0:.2f}".
          format(company.vcpu_cost))
    print("\tRAM GB-Hours: {0:.2f}".format(company.ram_hrs))
    print("\tRAM GB-Hours cost: {0:.2f}".
          format(company.ram_cost))
    print("\tDisk GB-Hours: {0:.2f}".format(company.gb_hrs))
    print("\tDisk GB-Hours cost: {0:.2f}".format(company.gb_cost))
    print("\tTotal cost: {0:.2f}".format(company.total_cost))
    if save:
        print("Saving to {0}".format(out_file))
        company.saveCSV(out_file, start_time, end_time, details)
