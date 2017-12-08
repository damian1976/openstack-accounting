#!/usr/bin/python3
import os
import pprint
from novaclient import client
from novaclient.exceptions import Forbidden, NotFound
from keystoneclient import client as ks
from keystoneclient.v3 import client as ks3
from keystoneauth1.identity import v3
from keystoneauth1 import loading
from keystoneauth1 import session
import datetime
import calendar
from oslo_utils import timeutils
from dateutil.relativedelta import relativedelta
import dateutil.parser as dup
import argparse
import configparser as Config
from keystoneclient.exceptions \
    import AuthorizationFailure,\
    Unauthorized,\
    EmptyCatalog
#import csv
import pytz
#import accountcsv
from util.company import Company
from util.project import Project
from util.server import Server

__author__ = 'Damian Kaliszan'
API_VERSION = '2.21'
pp = pprint.PrettyPrinter(indent=4)


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


# Filters out servers by given period of time.
def filterServersByDatetime(server, start_time, end_time):
    #pp.pprint(server.__dict__)
    #print(server.__dict__['OS-SRV-USG:launched_at'])
    #return True
    start_time = start_time.replace(tzinfo=pytz.UTC)
    end_time = end_time.replace(tzinfo=pytz.UTC)
    if ((hasattr(server, 'OS-SRV-USG:terminated_at')) and
       #(hasattr(server, 'OS-SRV-USG:launched_at')) and
       (hasattr(server, 'created')) and
       (hasattr(server, 'OS-EXT-STS:vm_state'))):
        server_start_time = dup.parse(
            #str(server.__dict__['OS-SRV-USG:launched_at'])
            str(server.__dict__['created'])
            ).replace(tzinfo=pytz.UTC)
        if (server.__dict__['OS-SRV-USG:terminated_at'] is not None
           and server.__dict__['OS-EXT-STS:vm_state'] == 'deleted'):
            server_end_time = dup.parse(
                str(server.__dict__['OS-SRV-USG:terminated_at'])
                ).replace(tzinfo=pytz.UTC)
        else:
            server_end_time = end_time
        #start_time = start_time.replace(tzinfo=pytz.UTC)
        diff1 = (start_time - server_end_time).total_seconds()
        diff2 = (end_time - server_start_time).total_seconds()
        if (diff1 > 0 or diff2 < 0):
            return False
        else:
            return True
    else:
        return False


def filterActionsByDatetime(actions, start_time=None, end_time=None):
    start_time = start_time.replace(tzinfo=pytz.UTC)
    end_time = end_time.replace(tzinfo=pytz.UTC)
    if actions:
        mydict = {'0': start_time, '1': end_time}
        for key, date in sorted(mydict.items()):
            #actions = list(reversed(actions))
            filtered_actions = actions
            date = date.replace(tzinfo=pytz.UTC)
            #pp.pprint(filtered_actions)
            for i, item in enumerate(filtered_actions):
                start_time = dup.parse(
                    str(item.start_time)
                ).replace(tzinfo=pytz.UTC)
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
    transitions = {'stop': 'start',
                   'shelve': 'unshelve',
                   'delete': ''}
    stop_list = list(transitions.keys())
    start_list = list(transitions.values())
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
        #if successfull the message is empty/is not 'Error'
        if (saction.action in stop_list and
           stop_action is None and not saction.message):
            stop_action = saction
        if (stop_action):
            if (saction.action in start_list and
                transitions[stop_action.action] == saction.action and
               stop_action is not None and not saction.message):
                #print("{0}\t{1}".format(stop_action.start_time,
                #      saction.start_time))
                #print("Odejmuje11")
                #start_time = timeutils.parse_isotime(stop_action.start_time)
                #end_time = timeutils.parse_isotime(saction.start_time)
                start_time = dup.parse(
                    str(stop_action.start_time)
                ).replace(tzinfo=pytz.UTC)
                end_time = dup.parse(
                    str(saction.start_time)
                ).replace(tzinfo=pytz.UTC)
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
                end_time = dup.parse(
                    str(period_end_time)
                ).replace(tzinfo=pytz.UTC)
                start_time = dup.parse(
                    str(stop_action.start_time)
                ).replace(tzinfo=pytz.UTC)
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


def readConfigFile(filename=None):
    if (filename):
        config = Config.ConfigParser()
        config.read(filename)
        try:
            company_section = configSectionMap('Company', config)
            company_name = company_section['name']
            comp = Company(company_name)
            #company.shelve_coeff = float(company_section['shelve_coeff'])
            #company.stop_coeff = float(company_section['stop_coeff'])
            comp.coeff['active'] = float(
                company_section['active_coeff']
            )
            comp.coeff['shelve'] = float(
                company_section['shelve_coeff']
            )
            comp.coeff['stop'] = float(
                company_section['stop_coeff']
            )
            comp.coeff['shelve_cpu'] = float(
                company_section['shelve_cpu_coeff']
            )
            comp.coeff['shelve_ram'] = float(
                company_section['shelve_ram_coeff']
            )
            comp.coeff['shelve_gb'] = float(
                company_section['shelve_gb_coeff']
            )
            comp.coeff['stop_cpu'] = float(
                company_section['stop_cpu_coeff']
            )
            comp.coeff['stop_ram'] = float(
                company_section['stop_ram_coeff']
            )
            comp.coeff['stop_gb'] = float(
                company_section['stop_gb_coeff']
            )
            comp.coeff['active_cpu'] = float(
                company_section['active_cpu_coeff']
            )
            comp.coeff['active_ram'] = float(
                company_section['active_ram_coeff']
            )
            comp.coeff['active_gb'] = float(
                company_section['active_gb_coeff']
            )
            for key, value in company_section.items():
                if (key == 'compute_api_url'):
                    comp.compute_api_url = \
                        company_section['compute_api_url']
                if (key == 'identity_api_url'):
                    comp.identity_api_url = \
                        company_section['identity_api_url']
                if (key == 'vcpuh'):
                    comp.vcpuh = float(company_section['vcpuh'])
                if (key == 'gbh'):
                    comp.gbh = float(company_section['gbh'])
                if (key == 'ramh'):
                    comp.ramh = float(company_section['ramh'])
            conf_projects = (x for x in config.sections()
                             if x not in 'Company')
            projects = []
            if (not all_users_projects):
                for proj in conf_projects:
                    #projects
                    try:
                        p = configSectionMap(proj, config)
                        project = Project(p['name'])
                        #project.url = comp.compute_api_url
                        project.vcpuh = comp.vcpuh
                        project.gbh = comp.gbh
                        project.ramh = comp.ramh
                        project.coeff = comp.coeff
                        for key, value in p.items():
                            if (key == 'vcpuh'):
                                project.vcpuh = float(p['vcpuh'])
                            if (key == 'gbh'):
                                project.gbh = float(p['gbh'])
                            if (key == 'ramh'):
                                project.ramh = float(p['ramh'])
                        projects.append(project)
                    except KeyError as err:
                        print("Project {0} doesn't have {1} attribute".
                              format(proj, err))
                        continue
            #pp.pprint(comp.__dict__)
            #for p in projects:
            #    pp.pprint(p.__dict__)
            if (not projects):
                project = Project('all')
                project.vcpuh = comp.vcpuh
                project.gbh = comp.gbh
                project.ramh = comp.ramh
                project.coeff = comp.coeff
                projects.append(project)
            return comp, projects
        except KeyError as err:
            print("{0} is not defined for 'Company' section".format(err))
            os._exit(1)
        except Config.NoSectionError as ce:
            print("Config file error: {0}".format(ce))
            os._exit(1)
    else:
        return None


def getOSServers(company, projects, user_tenants, username, password):
    servers = []
    try:
        print("Retrieving servers...")
        if (all_users_projects):
            auth = v3.Password(auth_url=company.identity_api_url,
                               username=username,
                               password=password,
                               user_domain_name='default',
                               project_domain_name='default')
            sess = session.Session(auth=auth)
            nova = client.Client(API_VERSION,
                                 session=sess,
                                 )
            search_opts_all = {'all_tenants': '1'}
            search_opts_all_deleted = {'all_tenants': '1',
                                       'status': 'deleted'
                                       }
            servers_active = nova.servers.list(
                search_opts=search_opts_all
                )
            # in case ListWithMEta error occurs
            if (servers is None):
                servers = list(servers_active)
            else:
                servers += list(servers_active)
            servers_deleted = nova.servers.list(
                search_opts=search_opts_all_deleted
                )
            servers += list(servers_deleted)
            if (servers is not None):
                for s in servers:
                    try:
                        '''
                        for k, v in user_tenants.items():
                            print("BB {0} {1} - {2}".format(k, v, s.tenant_id))
                            if (v == s.tenant_id):
                                print("ALALALALALL")
                                key = k
                        '''
                        key = [k for k, v in user_tenants.items()
                               if v == s.tenant_id
                               ]
                        #print("{0} {1}".format(type(key), key[0]))
                        s._add_details({'tenant_name': key[0]})
                    except KeyError:
                        key = "Unknown"
                    except IndexError:
                        s._add_details({'tenant_name': key})
                    s._add_details({'coeff': projects.coeff})
                    s._add_details({'gbh': projects.gbh})
                    s._add_details({'ramh': projects.ramh})
                    s._add_details({'vcpuh': projects.vcpuh})
        else:
            for project_id, project in projects.items():
                search_opts_all = {}
                search_opts_all_deleted = {'status': 'deleted'}
                auth = v3.Password(auth_url=company.identity_api_url,
                                   username=username,
                                   password=password,
                                   user_domain_name='default',
                                   project_domain_name='default',
                                   project_id=project_id
                                   )
                sess = session.Session(auth=auth)
                nova = client.Client(API_VERSION,
                                     session=sess,
                                     )
                servers_active = nova.servers.list(
                    search_opts=search_opts_all
                    )
                if (servers is None):
                    servers = servers_active
                else:
                    servers += servers_active
                servers_deleted = nova.servers.list(
                    search_opts=search_opts_all_deleted
                    )
                servers += servers_deleted
            if (servers is not None):
                for s in servers:
                    s._add_details({'tenant_name': project.name})
                    s._add_details({'coeff': project.coeff})
                    s._add_details({'gbh': project.gbh})
                    s._add_details({'ramh': project.ramh})
                    s._add_details({'vcpuh': project.vcpuh})
    except Forbidden as fb:
        print("There was a problem: {0}".format(fb))
    except KeyError as ke:
        print("Project {0} unavailable for given username".
              format(ke))
        #continue
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
    except EmptyCatalog as cc:
        print("Error when listing all users: {0}"
              .format(cc.message))
        os._exit(1)
    #pp.pprint(servers)
    print("Done.")
    return servers, nova


def getOSUsersProjects(company, username, password):
    try:
        os_users = dict()
        user_tenants = dict()
        print("Retrieving users...")
        if (all_users_projects):
            auth = v3.Password(auth_url=company.identity_api_url,
                               username=username,
                               password=password,
                               user_domain_name='default',
                               project_domain_name='default')
            sess = session.Session(auth=auth)
            ksclient = ks3.Client(session=sess,)
            ksusers = ksclient.users.list()
            for user in ksusers:
                #print("USERS: {0} {1}".format(user.name, user.id))
                os_users.update({user.name: user.id})
        else:
            os_users.update({username: password})
        print("Done.")
        # user_tenants contain all users tenants
        print("Retrieving users projects...")
        #print(users)
        for uname, uid in os_users.items():
        # Get tenants for given user
            if (all_users_projects):
                ksdata = ksclient.projects.list(user=uid)
            else:
                #opts = loading.get_plugin_loader('password')
                loader = loading.get_plugin_loader('password')
                auth = loader.load_from_options(auth_url=company.
                                                compute_api_url,
                                                username=username,
                                                password=password,
                                                )
                sess = session.Session(auth=auth)
                ksclient = ks.Client(session=sess,
                                     version=(2,),
                                     )
                ksdata = ksclient.tenants.list()
            dir(ksdata)
            utenants = dict((x.name, x.id) for x in ksdata)
            user_tenants.update(utenants)
            #pp.pprint(user_tenants)
            if user_tenants is None:
                raise ValueError
    except Forbidden as fb:
        print("There was a problem: {0}".format(fb))
    except KeyError as ke:
        print("Project {0} unavailable for given username".
              format(ke))
        #continue
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
    except EmptyCatalog as cc:
        print("Error when listing all users: {0}"
              .format(cc.message))
        os._exit(1)
    print("Done.")
    return user_tenants


def updateOSUserProjectsWithConfig(user_tenants):
    projects = dict()
    user_all = None
    try:
        user_all = dict((0, k) for k in
                        list(
                            filter(
                                lambda x: x.name == 'all', conf_projects)
                            )
                        )[0]
    except KeyError:
        '''
        user_all.coeff = company.coeff
        p.gbh = user_all.gbh
        p.ramh = user_all.ramh
        p.vcpuh = user_all.vcpuh
        '''
        user_all = None
    #pp.pprint(user_all)
    if (user_tenants):
        # Get all tenants for user in case 'all' is set as project name
        # in the config file. otherwise use just a name set
        if (user_all):
            for tname, tid in user_tenants.items():
                p = Project(tname)
                p.id = tid
                p.coeff = company.coeff
                p.gbh = user_all.gbh
                p.ramh = user_all.ramh
                p.vcpuh = user_all.vcpuh
                projects.update({tid: p})
        else:
            for proj in conf_projects:
                try:
                    proj.coeff = company.coeff
                    projects.update({user_tenants[proj.name]: proj})
                except:
                    print("Could not find a project {0}".format(proj.name))
                    os._exit(1)
    return projects, user_all

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
    parser.add_argument('-o', '--output-file',
                        nargs='?',
                        help='Output CSV file name')

    # Optional  argument
    parser.add_argument('--export-db',
                        dest='db',
                        action='store_true',
                        help="Enables saving results into SQLite database")

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

    parser.add_argument('--all-users-projects',
                        dest='all_users_projects',
                        action='store_true',
                        help="Activates accounting for all users and projects")

    # Parse args
    args, extra = parser.parse_known_args()
    username = ''
    password = ''
    company = None
    conf_projects = None
    start_time = ''
    end_time = ''
    out_file = ''
    save = False
    saveDB = False
    details = False
    all_users_projects = False
    users_file = ''
    if (args.config_file):
        company, conf_projects = readConfigFile(args.config_file)
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
    if (args.output_file):
        out_file = args.output_file
        save = True
    if (args.db):
        saveDB = True
    if (args.feature):
        details = True
    if (args.all_users_projects):
        all_users_projects = True
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
    time_delta = (end_time - start_time).total_seconds() / 3600.0
    if (not company or not conf_projects):
        os._exit(1)
    print("Company: '{0}':".format(company.name))
    print("Period: '{0}' - '{1}'".format(start_time, end_time))
    user_tenants = getOSUsersProjects(company, username, password)
    #pp.pprint(user_tenants)
    projects, user_all = updateOSUserProjectsWithConfig(user_tenants)
    if (all_users_projects):
        servers, nova = getOSServers(company,
                                     user_all if user_all else company,
                                     user_tenants,
                                     username, password
                                     )
    else:
        servers, nova = getOSServers(company,
                                     projects,
                                     None,
                                     username,
                                     password
                                     )
    try:
        print("Calculating...")
        for server in servers:
            #pp.pprint(server.__dict__)
            if (filterServersByDatetime(server,
                                        start_time=start_time,
                                        end_time=end_time)):
                s = Server(server.name)
                s.id = server.id
                s.status = server.status
                s.project_id = server.tenant_id
                s.project_name = server.tenant_name
                #pp.pprint(s.project_name)
                if (hasattr(server, 'flavor')):
                    flavor = nova.flavors.get(server.flavor['id'])
                    if (flavor):
                        #pp.pprint(flavor.__dict__)
                        s.gb['value'] = float(flavor.disk)
                        s.cpu['value'] = float(flavor.vcpus)
                        s.ram['value'] = float(flavor.ram) / 1024.0
                        actions = nova.instance_action.list(server=s.id)
                        actions = filterActionsByDatetime(
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
                            s.hrs = (
                                server_end - server_start
                                ).total_seconds() / 3600.0
                            s.gb['hours'] = s.gb['value']*s.hrs
                            s.cpu['hours'] = s.cpu['value']*s.hrs
                            s.ram['hours'] = s.ram['value']*s.hrs
                            #pp.pprint(s.__dict__)
                            (stop_timeframes,
                             shelve_timeframes,
                             delete_timeframes) =\
                                getStopStartTimeFrames(actions,
                                                       period_end_time=
                                                       end_time)
                            s.updateHoursAndVolumes(
                                stop_timeframes,
                                shelve_timeframes,
                                delete_timeframes,
                                server.coeff,
                            )
                #pp.pprint(coeff)
                s.updateMetricHoursWithActiveStatus(server.coeff)
                s.gb['cost'] = s.gb['hours']*server.gbh
                s.cpu['cost'] = s.cpu['hours']*server.vcpuh
                s.ram['cost'] = s.ram['hours']*server.ramh
                if details:
                    print(s)
                company.server.append(s)
                company.hrs += s.hrs
                company.cpu['hours'] += s.cpu['hours']
                company.cpu['cost'] += s.cpu['cost']
                company.ram['hours'] += s.ram['hours']
                company.ram['cost'] += s.ram['cost']
                company.gb['hours'] += s.gb['hours']
                company.gb['cost'] += s.gb['cost']
                company.total_cost += s.totalCost()
    except NotFound as nf:
        print("Flavor not found. Check if server flavor is set to public")
        os._exit(1)
    except KeyError as ke:
        print("Server doesn't contain {0} attribute".
              format(ke))
        os._exit(1)
    except Exception as e:
        print("Unexpected error: {0}".format(e))
        os._exit(1)
    print("Aggregation:")
    print("\tTotal Hours: {0:.2f}".format(company.hrs))
    print("\tCPU Hours: {0:.2f}".format(company.cpu['hours']))
    print("\tCPU Hours cost: {0:.2f}".
          format(company.cpu['cost']	))
    print("\tRAM GB-Hours: {0:.2f}".format(company.ram['hours']	))
    print("\tRAM GB-Hours cost: {0:.2f}".
          format(company.ram['cost']	))
    print("\tDisk GB-Hours: {0:.2f}".format(company.gb['hours']	))
    print("\tDisk GB-Hours cost: {0:.2f}".format(company.gb['cost']	))
    print("\tTotal cost: {0:.2f}".format(company.total_cost))
    if save:
        print("Saving to {0}".format(out_file))
        company.saveCSV(out_file, start_time, end_time, details)
    if saveDB:
        print("Saving to database")
        company.saveDB(start_time, end_time)
