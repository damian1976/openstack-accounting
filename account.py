#!/usr/bin/python3
import sys
import os
import pprint
from novaclient import client
from novaclient.exceptions import Forbidden, NotFound
from keystoneclient import client as ks
from keystoneclient.v3 import client as ks3
from cinderclient.v3 import client as cclient
from glanceclient import client as gclient
from keystoneauth1.identity import v3
from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneauth1 import exceptions as kse
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
import pytz
import re
from novaclient.exceptions \
    import ClientException
#from novaclient.exceptions \
#    import InstanceNotFound
from util.company import Company
from util.project import Project
from util.server import Server
from util.storage import Storage

__author__ = 'Damian Kaliszan'
API_VERSION = '2.21'
#API_VERSION = '2.40'
CINDER_API_VERSION = '3.0'
GLANCE_API_VERSION = '2'
LIMIT = '500'
INSTANCE_AT_VOLUME_STR = 'Attempt to boot from volume - no image supplied'
VOL_PFX = 'diskh'
VOL_TYPE = 'volume_type'
VOL_TYPE_STD = 'Standard'
VOL_TENANT_ID_ATTR = 'os-vol-tenant-attr:tenant_id'

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


# Filters out volume by given period of time.
def filterAndRecalculateStorageByDatetime(storage,
                                          start_time,
                                          end_time,
                                          type):
    start_time = start_time.replace(tzinfo=pytz.UTC)
    end_time = end_time.replace(tzinfo=pytz.UTC)
    diff_default = (end_time - start_time).total_seconds()
    created_at = ""
    status = ""
    terminated_at = ""
    #id = ""
    #print("JESTEM {0}".format(storage))
    if type == 'volumes':
        #i = iter(storage)
        #storage = dict(zip(i, i))
        #storage = {k: v for k, v in (x.split(',') for x in storage)}
        created_at = storage.get("created_at", "")
        id = storage.get("id")
        status = storage.get("id", "")
        terminated_at = storage.get("terminated_at", "")
    elif type == 'images':
        original = storage.get("__original__", "")
        if original:
            created_at = original.get("created_at", "")
            id = original.get("id", "")
            status = original.get("status", "")
    #print("storage={0} - {1}".format(id, created_at))
    if (created_at and status):
        storage_start_time = dup.parse(
            str(created_at)).replace(tzinfo=pytz.UTC)
        if terminated_at and status == 'deleted':
            storage_end_time = dup.parse(
                str(terminated_at)
            ).replace(tzinfo=pytz.UTC)
        else:
            storage_end_time = end_time
        #start_time = start_time.replace(tzinfo=pytz.UTC)
        diff1 = (start_time - storage_end_time).total_seconds()
        diff2 = (end_time - storage_start_time).total_seconds()
        diff3 = (start_time - storage_start_time).total_seconds()
        diff4 = (end_time - storage_end_time).total_seconds()
        #print("ID= {0} - {1} - {2} - {3:f} - {4:f} - {5:f} - {6:f}".format(id, created_at, status, diff1, diff2, diff3, diff4))
        if (diff1 > 0 or diff2 < 0):
            return False
        else:
            #print("Obliczam {0}".format(diff_default))
            if diff3 < 0:
                diff_default += diff3
                if diff4 > 0:
                    diff_default -= diff4
            elif diff3 > 0:
                if diff4 > 0:
                    diff_default -= diff4
            else:
                if diff4 > 0:
                    diff_default -= diff4
            #elif (diff3 >= 0 and diff4 <= 0):
            #print("ID= {0} zwracam {1}, created={2}".format(id, diff_default, created_at))
            return diff_default
    else:
        return False


# Filters out server by given period of time.
def filterServerByDatetime(server, start_time, end_time):
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
        mydict = {'0': start_time,
                  '1': end_time,
                  }
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
                start_time = dup.parse(
                    str(stop_action.start_time)
                ).replace(tzinfo=pytz.UTC)
                end_time = dup.parse(
                    str(saction.start_time)
                ).replace(tzinfo=pytz.UTC)
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
            for key, value in company_section.items():
                if (key == 'compute_api_url'):
                    comp.compute_api_url = \
                        company_section['compute_api_url']
                if (key == 'identity_api_url'):
                    comp.identity_api_url = \
                        company_section['identity_api_url']
                if (key == 'volume_api_url'):
                    comp.volume_api_url = \
                        company_section['volume_api_url']
                if (key == 'project'):
                    # get list of all projects to calculate or 'all'
                    tmp_list = company_section['project'].split(",")
                    comp.project = [item.strip() for item in tmp_list]
                    #pp.pprint(comp.project)
            coefficients_section =\
                configSectionMap('Coefficients', config)
            for key, value in coefficients_section.items():
                if (key == 'active_coeff'):
                    comp.coeff['active'] = float(
                        coefficients_section['active_coeff']
                    )
                if (key == 'shelve_coeff'):
                    comp.coeff['shelve'] = float(
                        coefficients_section['shelve_coeff']
                    )
                if (key == 'stop_coeff'):
                    comp.coeff['stop'] = float(
                        coefficients_section['stop_coeff']
                    )
                if (key == 'shelve_cpu_coeff'):
                    comp.coeff['shelve_cpu'] = float(
                        coefficients_section['shelve_cpu_coeff']
                    )
                if (key == 'shelve_ram_coeff'):
                    comp.coeff['shelve_ram'] = float(
                        coefficients_section['shelve_ram_coeff']
                    )
                if (key == 'shelve_disk_coeff'):
                    comp.coeff['shelve_disk'] = float(
                        coefficients_section['shelve_disk_coeff']
                    )
                if (key == 'stop_cpu_coeff'):
                    comp.coeff['stop_cpu'] = float(
                        coefficients_section['stop_cpu_coeff']
                    )
                if (key == 'stop_ram_coeff'):
                    comp.coeff['stop_ram'] = float(
                        coefficients_section['stop_ram_coeff']
                    )
                if (key == 'stop_disk_coeff'):
                    comp.coeff['stop_disk'] = float(
                        coefficients_section['stop_disk_coeff']
                    )
                if (key == 'active_cpu_coeff'):
                    comp.coeff['active_cpu'] = float(
                        coefficients_section['active_cpu_coeff']
                    )
                if (key == 'active_ram_coeff'):
                    comp.coeff['active_ram'] = float(
                        coefficients_section['active_ram_coeff']
                    )
                if (key == 'active_disk_coeff'):
                    comp.coeff['active_disk'] = float(
                        coefficients_section['active_disk_coeff']
                    )
            hours_indicators_section =\
                configSectionMap('HoursIndicators', config)
            for key, value in hours_indicators_section.items():
                if (key == 'vcpuh'):
                    comp.vcpuh = float(hours_indicators_section['vcpuh'])
                if (key == 'ramh'):
                    comp.ramh = float(hours_indicators_section['ramh'])
                if ('diskh' in key):
                    pattern = VOL_PFX + "_(\S+)"
                    m = re.search(pattern, key)
                    name = str(m.group(1))
                    comp.diskh[name] = float(hours_indicators_section[key])
            conf_projects = (x for x in config.sections()
                             if x not in ('Company',
                                          'HoursIndicators',
                                          'Coefficients',
                                          )
                             )
            projects = dict()
            if (comp.project[0].lower() != 'all'):
                for proj in comp.project:
                    project = Project(proj)
                    project.vcpuh = comp.vcpuh
                    project.ramh = comp.ramh
                    project.coeff = comp.coeff
                    project.diskh = comp.diskh
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
                                projects[p['name']].vcpuh = float(p['vcpuh'])
                            if (key == 'ramh'):
                                projects[p['name']].ramh = float(p['ramh'])
                            if ('diskh' in key):
                                pattern = VOL_PFX + "_(\S+)"
                                m = re.search(pattern, key)
                                name = str(m.group(1))
                                projects[p['name']].diskh[name] =\
                                    float(p[name])
                    else:
                        if (comp.project[0].lower() == 'all'):
                            project = Project(p['name'])
                            for key, value in p.items():
                                if (key == 'vcpuh'):
                                    project.vcpuh = float(p['vcpuh'])
                                if (key == 'ramh'):
                                    project.ramh = float(p['ramh'])
                                #if (key == 'diskh'):
                                #    project.diskh = float(p['diskh'])
                                if ('diskh' in key):
                                    pattern = VOL_PFX + "_(\S+)"
                                    m = re.search(pattern, key)
                                    name = str(m.group(1))
                                    project.diskh[name] = float(p[name])
                            project.coeff = comp.coeff
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
    else:
        return None


def getOSServers(company, projects, user_tenants, username, password):
    servers = []
    #nova = None
    projects_ids = list([x.id for x in projects.values()])
    #auth = None
    try:
        print("Fetching servers...")
        if (as_admin):
            auth = v3.Password(auth_url=company.identity_api_url,
                               username=username,
                               password=password,
                               user_domain_name='default',
                               project_domain_name='default',
                               )
            search_opts_all = {'all_tenants': '1',
                               'limit': LIMIT,
                               }
            search_opts_all_deleted = {'all_tenants': '1',
                                       'status': 'deleted',
                                       'limit': LIMIT,
                                       }
            servers = listObjects(auth,
                                  search_opts_all,
                                  search_opts_all_deleted,
                                  client,
                                  'servers',
                                  API_VERSION
                                  )
            if servers:
                if (company.project[0].lower() != 'all'):
                    servers = [x for x in servers if x.tenant_id
                               in projects_ids]
                else:
                    servers = [x for x in servers if x.tenant_id
                               in user_tenants.values()]
                for s in servers:
                    try:
                        key = [k for k, v in projects.items()
                               if v.id == s.tenant_id
                               ]
                        tenant_name = key[0]
                        #print("TENANT NAME: {0}".format(tenant_name))
                        s._add_details({'tenant_name': tenant_name})
                        s._add_details({'coeff': projects[tenant_name].coeff})
                        s._add_details({'ramh': projects[tenant_name].ramh})
                        s._add_details({'vcpuh': projects[tenant_name].vcpuh})
                        s._add_details({VOL_PFX:
                                        projects[tenant_name].
                                        diskh['standard']
                                        }
                                       )
                    except KeyError:
                        key = "Unknown"
                    except IndexError:
                        s._add_details({'tenant_name': key})
        else:
            search_opts_all = {'limit': LIMIT, }
            search_opts_all_deleted = {'status': 'deleted',
                                       'limit': LIMIT,
                                       }
            if (company.project[0].lower() == 'all'):
                for tenant_name, tenant_id in user_tenants.items():
                    #print("JESTEM {0} - {1}".format(tenant_name, tenant_id))
                    auth = v3.Password(auth_url=company.identity_api_url,
                                       username=username,
                                       password=password,
                                       user_domain_name='default',
                                       project_domain_name='default',
                                       project_id=tenant_id
                                       )
                    srvs = listObjects(auth,
                                       search_opts_all,
                                       search_opts_all_deleted,
                                       client,
                                       'servers',
                                       API_VERSION
                                       )
                    #print("SERVERS HELLO LEN={0}".format(len(srvs)))
                    if srvs:
                        if (tenant_id in projects_ids):
                            #print("tenant_id in projects_ids")
                            try:
                                project = projects[tenant_name]
                                for s in srvs:
                                    #print("tenant={0} SRV: {0} - {1} ({2})".format(tenant_name, s.name, s.id, len(servers)))
                                    s._add_details(
                                        {'tenant_name': project.name}
                                    )
                                    s._add_details({'coeff': project.coeff})
                                    s._add_details({'ramh': project.ramh})
                                    s._add_details({'vcpuh': project.vcpuh})
                                    s._add_details({VOL_PFX:
                                                    projects[tenant_name].
                                                    diskh['standard']
                                                    }
                                                   )
                            except KeyError:
                                print("KEY ERROR")
                                for s in srvs:
                                    s._add_details({'tenant_name': 'Unknown'})
                                    s._add_details({'coeff': '0.0'})
                                    s._add_details({'ramh': '0.0'})
                                    s._add_details({'vcpuh': '0.0'})
                                    s._add_details({VOL_PFX: '0.0'})
                        else:
                            #print("tenant_id {0} not in projects_ids ERROR".format(tenant_id))
                            for s in srvs:
                                s._add_details({'tenant_name': tenant_name})
                                s._add_details({'coeff': company.coeff})
                                s._add_details({'ramh': company.ramh})
                                s._add_details({'vcpuh': company.vcpuh})
                                s._add_details({VOL_PFX:
                                                projects[tenant_name].
                                                diskh['standard']
                                                }
                                               )
                        if not servers:
                            servers = srvs
                        else:
                            servers += srvs
            else:
                #print("JESTEM 2 - len={0}".format(len(servers)))
                for name, project in projects.items():
                    #print("pn: {0}".format(name))
                    #print("pid: {0}".format(project.id))
                    auth = v3.Password(auth_url=company.identity_api_url,
                                       username=username,
                                       password=password,
                                       user_domain_name='default',
                                       project_domain_name='default',
                                       project_id=project.id
                                       )
                    srvs = listObjects(auth,
                                       search_opts_all,
                                       search_opts_all_deleted,
                                       client,
                                       'servers',
                                       API_VERSION
                                       )
                    if srvs:
                        for s in srvs:
                            #print("tenant={0} SRV2: {0} - {1} ({2})".format(name, s.name, s.id, len(servers)))
                            s._add_details({'tenant_name': name})
                            s._add_details({'coeff': project.coeff})
                            s._add_details({'ramh': project.ramh})
                            s._add_details({'vcpuh': project.vcpuh})
                            s._add_details({VOL_PFX:
                                            project.diskh['standard']
                                            }
                                           )
                        if not servers:
                            servers = srvs
                        else:
                            servers += srvs
    except Forbidden as fb:
        print("There was a problem: {0}".format(fb))
    except KeyError as ke:
        print("Project {0} unavailable for given username".
              format(ke))
        #continue
    except ValueError as ve:
        print("Error parsing projects for given username: {1}".
              format(ve))
        sys.exit(-1)
    except AuthorizationFailure as auf:
        print("Error for {0} auth: {1}".format(username, auf))
        sys._exit(-2)
    except Unauthorized as unauth:
        print("Error for {0} auth: {1}"
              .format(username, unauth.message))
        sys._exit(-3)
    except EmptyCatalog as cc:
        print("Error when fetching servers: {0}"
              .format(cc.message))
        sys._exit(-4)
    except ClientException as ce:
        print("Error: {0}".format(ce.message))
        sys.exit(-5)
    except kse.http.ServiceUnavailable as su:
        print("Error when fetching servers: {0}"
              .format(su.message))
        sys.exit(-6)
    #pp.pprint(servers)
    print("Done.")
    return servers


def getOSUSers(username, password):
    try:
        os_users = dict()
        ksclient = None
        print("Fetching users...")
        #if admin fetch all OS users
        if (as_admin):
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
        #otherwise add only a single user who starts this script
        else:
            os_users.update({username: password})
        #print("Done.")
    except AuthorizationFailure as auf:
        print("getOSUSers: Error for {0} auth: {1}".format(username, auf))
        sys.exit(-7)
    except Unauthorized as unauth:
        print("getOSUSers: Error for {0} auth: {1}"
              .format(username, unauth.message))
        sys.exit(-8)
    except EmptyCatalog as cc:
        print("getOSUSers: Error when fetching users: {0}"
              .format(cc.message))
        sys.exit(-9)
    except kse.http.ServiceUnavailable as su:
        print("getOSUSers: Error when fetching users: {0}"
              .format(su.message))
        sys.exit(-10)
    print("Done.")
    return ksclient, os_users


def listObjects(auth,
                search_opts_all,
                search_opts_all_deleted,
                client,
                typename,
                api
                ):
    user_objects = []
    sess = session.Session(auth)
    obj = client.Client(api,
                        session=sess,
                        )
    search_opts_all.pop('marker', None)
    class_ = getattr(obj, typename)
    list_ = getattr(class_, 'list')
    #print("NOWY TENANT")
    #print("{0}".format(search_opts_all))
    prev_last_id = 0
    last_id = 1
    while prev_last_id != last_id:
        prev_last_id = last_id
        #print("1: {0} - {1} - {2}".format(search_opts_all, prev_last_id, last_id))
        objects_active = list_(
            search_opts=search_opts_all
        )
        objects_active_list = list(objects_active)
        if objects_active_list:
            last_id = objects_active_list[-1].id
            #print("2: {0} - {1} - {2}".format(search_opts_all, prev_last_id, last_id))
            if last_id != prev_last_id:
                user_objects += objects_active_list
            #if (typename == 'images'):
            #    pp.pprint(objects_active_list[-1])
            search_opts_all['marker'] = last_id
        else:
            last_id = prev_last_id
    #print("len(active)={0}".format(len(user_objects)))
    search_opts_all_deleted.pop('marker', None)
    if (typename != 'images'):
        prev_last_id = 0
        last_id = 1
        while prev_last_id != last_id:
            try:
                prev_last_id = last_id
                objects_deleted = list_(
                    search_opts=search_opts_all_deleted
                )
                objects_deleted_list = list(objects_deleted)
                if objects_deleted_list:
                    last_id = objects_deleted_list[-1].id
                    #pp.pprint(servers_deleted_list[-1].__dict__)
                    if last_id != prev_last_id:
                        user_objects += objects_deleted_list
                    search_opts_all_deleted['marker'] = last_id
                    #pp.pprint(search_opts_all_deleted)
                else:
                    last_id = prev_last_id
            except ClientException as ce:
                print("listObjects: Error in {0} deleted: {1}".
                      format(typename, ce.message))
                objects_deleted = []
    #print("len(total)={0}".format(len(user_objects)))
    return user_objects


def getOSUsersVolumes(company, projects, user_tenants, username, password):
    try:
        user_volumes = []
        projects_ids = list([x.id for x in projects.values()])
        #ksclient, os_users = getOSUSers(username, password)
        print("Fetching volumes...")
        if (as_admin):
            authcinder = v3.Password(auth_url=company.volume_api_url,
                                     username=username,
                                     password=password,
                                     user_domain_name='default',
                                     project_domain_name='default',
                                     )
            search_opts_all = {'all_tenants': '1',
                               'limit': LIMIT,
                               }
            search_opts_all_deleted = {'all_tenants': '1',
                                       'status': 'deleted',
                                       'limit': LIMIT,
                                       }
            user_volumes = listObjects(authcinder,
                                       search_opts_all,
                                       search_opts_all_deleted,
                                       cclient,
                                       'volumes',
                                       CINDER_API_VERSION
                                       )
            if user_volumes:
                if (company.project[0].lower() != 'all'):
                    user_volumes = [x for x in user_volumes
                                    if getattr(x, VOL_TENANT_ID_ATTR)
                                    in projects_ids
                                    ]
                else:
                    user_volumes = [x for x in user_volumes
                                    if getattr(x, VOL_TENANT_ID_ATTR)
                                    in user_tenants.values()
                                    ]
                for vl in user_volumes:
                    try:
                        dir(vl)
                        key = [k for k, v in projects.items()
                               if v.id == getattr(vl, VOL_TENANT_ID_ATTR)
                               ]
                        project = projects.get(key[0], None)
                        dir(project)
                        tenant_name = project.name
                        vol_type_name = getattr(vl, VOL_TYPE)
                        if (vol_type_name is not None):
                            vl._add_details({
                                VOL_PFX: project.diskh[vol_type_name.lower()]
                            })
                        else:
                            vl._add_details({
                                VOL_PFX: project.diskh[VOL_TYPE_STD.lower()]
                            })
                        #print("TENANT NAME: {0}".format(tenant_name))
                        vl._add_details({'tenant_name': tenant_name})
                    except KeyError:
                        key = "Unknown"
                    except IndexError:
                        vl._add_details({'tenant_name': key})
                        vl._add_details({VOL_PFX: '0.0'})
        else:
            search_opts_all = {'limit': LIMIT, }
            search_opts_all_deleted = {'status': 'deleted',
                                       'limit': LIMIT,
                                       }
            if (company.project[0].lower() == 'all'):
                for tenant_name, tenant_id in user_tenants.items():
                    authcinder = v3.Password(auth_url=company.volume_api_url,
                                             username=username,
                                             password=password,
                                             user_domain_name='default',
                                             project_domain_name='default',
                                             project_id=tenant_id,
                                             )
                    usr_vls = listObjects(authcinder,
                                          search_opts_all,
                                          search_opts_all_deleted,
                                          cclient,
                                          'volumes',
                                          CINDER_API_VERSION
                                          )
                    if usr_vls:
                        if (tenant_id in projects_ids):
                            try:
                                project = projects[tenant_name]
                                for vl in usr_vls:
                                    dir(vl)
                                    vl._add_details(
                                        {'tenant_name': project.name}
                                    )
                                    vol_type_name = getattr(vl, VOL_TYPE)
                                    if (vol_type_name is not None):
                                        vl._add_details({
                                            VOL_PFX: project.diskh[
                                                vol_type_name.lower()
                                            ]
                                        })
                                    else:
                                        vl._add_details({
                                            VOL_PFX: project.diskh[
                                                VOL_TYPE_STD.lower()
                                            ]
                                        })
                            except KeyError:
                                for vl in usr_vls:
                                    dir(vl)
                                    vl._add_details({'tenant_name': 'Unknown'})
                                    vl._add_details({
                                        VOL_PFX: project.diskh[
                                            VOL_TYPE_STD.lower()
                                        ]
                                    })
                        else:
                            for vl in usr_vls:
                                dir(vl)
                                vl._add_details({'tenant_name': tenant_name})
                                vl._add_details({
                                    VOL_PFX: project.diskh[
                                        VOL_TYPE_STD.lower()
                                    ]
                                })
                        if not user_volumes:
                            user_volumes = usr_vls
                        else:
                            user_volumes += usr_vls
            else:
                for name, project in projects.items():
                    authcinder = v3.Password(auth_url=company.volume_api_url,
                                             username=username,
                                             password=password,
                                             user_domain_name='default',
                                             project_domain_name='default',
                                             project_id=project.id,
                                             )
                    usr_vls = listObjects(authcinder,
                                          search_opts_all,
                                          search_opts_all_deleted,
                                          cclient,
                                          'volumes',
                                          CINDER_API_VERSION
                                          )
                    if usr_vls:
                        for vl in usr_vls:
                            dir(vl)
                            #print(dir(vl))
                            vl._add_details({'tenant_name': name})
                            vol_type_name = getattr(vl, VOL_TYPE)
                            if (vol_type_name is not None):
                                #print("Dodaje {0}".format(project.diskh[vol_type_name.lower()]))
                                vl._add_details({
                                    VOL_PFX: project.diskh[
                                        vol_type_name.lower()
                                    ]
                                })
                            else:
                                vl._add_details({
                                    VOL_PFX: project.diskh[
                                        VOL_TYPE_STD.lower()
                                    ]
                                })
                        if not user_volumes:
                            user_volumes = usr_vls
                        else:
                            user_volumes += usr_vls
        if not user_volumes:
            raise ValueError
    except ValueError as ve:
        print("getOSUsersVolumes: Error parsing projects for given username: {1}"
              .format(ve))
        sys.exit(-11)
    except kse.http.ServiceUnavailable as su:
        print("getOSUsersVolumes: Error when listing volumes: {0}"
              .format(su.message))
        sys.exit(-12)
    print("Done.")
    #pp.pprint(user_volumes)
    return user_volumes


def getOSUsersImages(company, projects, user_tenants, username, password):
    try:
        user_images = []
        projects_ids = list([x.id for x in projects.values()])
        #pp.pprint(projects_ids)
        print("Fetching images...")
        if (as_admin):
            authglance = v3.Password(auth_url=company.volume_api_url,
                                     username=username,
                                     password=password,
                                     user_domain_name='default',
                                     project_domain_name='default',
                                     )
            search_opts_all = {'all_tenants': '1',
                               'limit': LIMIT,
                               }
            search_opts_all_deleted = {'all_tenants': '1',
                                       'status': 'deleted',
                                       'limit': LIMIT,
                                       }
            user_images = listObjects(authglance,
                                      search_opts_all,
                                      search_opts_all_deleted,
                                      gclient,
                                      'images',
                                      GLANCE_API_VERSION,
                                      )
            if user_images:
                #print("WYPISUJE")
                #for x in user_images:
                #    print("ID={0} {1}".format(x.get('owner_id'), x.get('owner')))
                if (company.project[0].lower() != 'all'):
                    user_images = [x for x in user_images
                                   if x.get('owner') in projects_ids
                                   and x.get('visibility') != 'public'
                                   ]
                else:
                    user_images = [x for x in user_images
                                   if x.get('owner')
                                   in user_tenants.values()
                                   and x.get('visibility') != 'public'
                                   ]
                #print("PO")
                #pp.pprint(user_images)
                #print("PO PO")
                for img in user_images:
                    try:
                        #dir(vl)
                        #print(vl)
                        #print("11")
                        key = [k for k, v in projects.items()
                               if v.id == img.get('owner')
                               ]
                        project = projects.get(key[0], None)
                        dir(project)
                        tenant_name = project.name
                        tenant_id = project.id
                        img.__setattr__(VOL_PFX,
                                        project.diskh[
                                            VOL_TYPE_STD.lower()
                                        ]
                                        )
                        #print("TENANT NAME: {0} {1}".format(tenant_name, tenant_id))
                        img.__setattr__('tenant_name', tenant_name)
                        img.__setattr__('tenant_id', tenant_id)
                    except KeyError:
                        key = "Unknown"
                    except IndexError:
                        img.__setattr__('tenant_name', key)
                        img.__setattr__('tenant_id', '-1')
                        img.__setattr__(VOL_PFX, '0.0')
        else:
            search_opts_all = {'limit': LIMIT, }
            search_opts_all_deleted = {'status': 'deleted',
                                       'limit': LIMIT,
                                       }
            if (company.project[0].lower() == 'all'):
                for tenant_name, tenant_id in user_tenants.items():
                    #print("tenant_name={0} tenant_id={1}".format(tenant_name, tenant_id))
                    authglance = v3.Password(auth_url=company.volume_api_url,
                                             username=username,
                                             password=password,
                                             user_domain_name='default',
                                             project_domain_name='default',
                                             project_id=tenant_id,
                                             )
                    usr_imgs = listObjects(authglance,
                                           search_opts_all,
                                           search_opts_all_deleted,
                                           gclient,
                                           'images',
                                           GLANCE_API_VERSION
                                           )
                    usr_imgs = [x for x in usr_imgs
                                if x.get('owner') == tenant_id
                                and x.get('visibility') != 'public'
                                ]
                    if usr_imgs:
                        if (tenant_id in projects_ids):
                            try:
                                project = projects[tenant_name]
                                for img in usr_imgs:
                                    dir(img)
                                    img.__setattr__('tenant_name',
                                                    project.name
                                                    )
                                    img.__setattr__('tenant_id', tenant_id)
                                    img.__setattr__(VOL_PFX,
                                                    project.diskh[
                                                        VOL_TYPE_STD.lower()
                                                    ]
                                                    )
                            except KeyError:
                                for img in usr_imgs:
                                    dir(img)
                                    img.__setattr__('tenant_name', 'Unknown')
                                    img.__setattr__('tenant_id', '-1')
                                    img.__setattr__(VOL_PFX,
                                                    project.diskh[
                                                        VOL_TYPE_STD.lower()
                                                    ]
                                                    )
                        else:
                            for img in usr_imgs:
                                dir(img)
                                img.__setattr__('tenant_name', tenant_name)
                                img.__setattr__('tenant_id', tenant_id)
                                img.__setattr__(VOL_PFX,
                                                project.diskh[
                                                    VOL_TYPE_STD.lower()
                                                ]
                                                )
                                #vl._add_details({'tenant_name': tenant_name})
                        if not user_images:
                            user_images = usr_imgs
                        else:
                            user_images += usr_imgs
            else:
                for name, project in projects.items():
                    authglance = v3.Password(auth_url=company.volume_api_url,
                                             username=username,
                                             password=password,
                                             user_domain_name='default',
                                             project_domain_name='default',
                                             project_id=project.id
                                             )
                    usr_imgs = listObjects(authglance,
                                           search_opts_all,
                                           search_opts_all_deleted,
                                           gclient,
                                           'images',
                                           GLANCE_API_VERSION
                                           )
                    usr_imgs = [x for x in usr_imgs
                                if x.get('owner') == project.id
                                and x.get('visibility') != 'public'
                                ]
                    if usr_imgs:
                        for img in usr_imgs:
                            #print(vl)
                            img.__setattr__('tenant_name', name)
                            img.__setattr__('tenant_id', project.id)
                            img.__setattr__(VOL_PFX,
                                            project.diskh[
                                                VOL_TYPE_STD.lower()
                                                ]
                                            )
                        if not user_images:
                            user_images = usr_imgs
                        else:
                            user_images += usr_imgs
        if not user_images:
            raise ValueError
    except ValueError as ve:
        print("getOSUsersImages: Error parsing projects for given username: {1}"
              .format(ve))
        sys.exit(-11)
    except kse.http.ServiceUnavailable as su:
        print("getOSUsersImages: Error when listing volumes: {0}"
              .format(su.message))
        sys.exit(-12)
    except AttributeError as ae:
        print("getOSUsersImages: Attribute error: {0}"
              .format(ae))
        sys.exit(-13)
    print("Done.")
    #pp.pprint(user_volumes)
    return user_images


def getOSUsersProjects(company, username, password):
    try:
        user_tenants = dict()
        ksclient, os_users = getOSUSers(username, password)
        # user_tenants contain all users tenants
        print("Fetching users projects...")
        #print(users)
        for uname, uid in os_users.items():
        # Get tenants for given user
            if (as_admin):
                ksdata = ksclient.projects.list(user=uid)
            else:
                #opts = loading.get_plugin_loader('password')
                loader = loading.get_plugin_loader('password')
                #user tenants
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
        print("getOSUsersProjects: There was a problem: {0}".format(fb))
    except KeyError as ke:
        print("getOSUsersProjects: Project {0} unavailable for given username".
              format(ke))
        #continue
    except ValueError as ve:
        print("getOSUsersProjects: Error parsing projects\
            for given username: {1}".format(ve))
        sys.exit(-14)
    except AuthorizationFailure as auf:
        print("getOSUsersProjects: Error for {0} auth: {1}".format(
            username, auf)
        )
        sys.exit(-15)
    except Unauthorized as unauth:
        print("getOSUsersProjects: Error for {0} auth: {1}"
              .format(username, unauth.message))
        sys.exit(-16)
    except EmptyCatalog as cc:
        print("getOSUsersProjects: Error when listing all users: {0}"
              .format(cc.message))
        sys.exit(-17)
    except kse.http.ServiceUnavailable as su:
        print("getOSUsersProjects: Error when listing users projects: {0}"
              .format(su.message))
        sys.exit(-18)
    print("Done.")
    return user_tenants


def updateOSUserProjectsWithConfig(user_tenants):
    projects = dict()
    if (user_tenants):
        # Get all tenants for user in case 'all' is set as project name
        # in the config file. otherwise use just a name set
        if (company.project[0].lower() == 'all'):
            for tname, tid in user_tenants.items():
                try:
                    conf_projects[tname].id = tid
                    projects.update({tname: conf_projects[tname]})
                except KeyError:
                    p = Project(tname)
                    p.id = tid
                    p.coeff = company.coeff
                    p.diskh = company.diskh
                    p.ramh = company.ramh
                    p.vcpuh = company.vcpuh
                    projects.update({tname: p})
        else:
            for tname, tid in user_tenants.items():
                try:
                    conf_projects[tname].id = tid
                    projects.update({tname: conf_projects[tname]})
                except KeyError:
                    pass
    #return projects only we want with updated values from config
    return projects

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
    as_admin = False
    volumes = False
    images = False
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
    if (args.output_file):
        out_file = args.output_file
        save = True
    if (args.db):
        saveDB = True
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
    time_delta = (end_time - start_time).total_seconds() / 3600.0
    #if (not company or not conf_projects):
    if (not company or (not conf_projects and company.project[0].lower() != 'all')):
        sys.exit(-21)
    print("Company: '{0}':".format(company.name))
    print("Period: '{0}' - '{1}'".format(start_time, end_time))
    user_tenants = getOSUsersProjects(company, username, password)
    #pp.pprint(user_tenants)
    projects = updateOSUserProjectsWithConfig(user_tenants)
    #pp.pprint(user_tenants)
    #pp.pprint(projects)
    servers = getOSServers(company,
                           projects,
                           user_tenants,
                           username,
                           password
                           )
    #servers = None
    #nova = None
    try:
        if volumes:
            user_volumes = getOSUsersVolumes(company,
                                             projects,
                                             user_tenants,
                                             username,
                                             password
                                             )
            print("Calculating volumes...")
            for vol in user_volumes:
                seconds =\
                    filterAndRecalculateStorageByDatetime(
                        vol.__dict__,
                        start_time=start_time,
                        end_time=end_time,
                        type='volumes',
                    )
                if seconds:
                    #pp.pprint(vol.__dict__)
                    storage = Storage(vol.name, vol.id, 'Volume')
                    storage.status = vol.status
                    storage.project_id = getattr(vol, VOL_TENANT_ID_ATTR)
                    storage.project_name = vol.tenant_name
                    storage.disk['value'] = vol.size
                    storage.type = getattr(vol, VOL_TYPE)
                    storage.hrs = seconds / 3600.0
                    storage.disk['hours'] = storage.disk['value']*storage.hrs
                    storage.disk['cost'] = storage.disk['hours']*vol.diskh
                    if details:
                        print(storage)
                    company.volume.append(storage)
                    company.hrs += storage.hrs
                    company.disk['hours'] += storage.disk['hours']
                    company.disk['cost'] += storage.disk['cost']
                    company.total_cost += storage.totalCost()
        if images:
            user_images = getOSUsersImages(company,
                                           projects,
                                           user_tenants,
                                           username,
                                           password
                                           )
            print("Calculating images...")
            for img in user_images:
                seconds =\
                    filterAndRecalculateStorageByDatetime(
                        img.__dict__,
                        start_time=start_time,
                        end_time=end_time,
                        type='images',
                    )
                if seconds:
                    #pp.pprint(vol.__dict__)
                    #print("JUZ PO")
                    strg = img.__dict__
                    original = strg.get("__original__", "")
                    changes = strg.get("changes", "")
                    if original:
                        #print("IMG={0} - {1}".format(original.get("id"), original.get("owner")))
                        #print("w original")
                        img_name = original.get("name", "")
                        img_id = original.get("id", "")
                        img_size = original.get("size", "0")
                        if not img_size:
                            img_size = 0
                        img_status = original.get("status", "")
                        #print("img_name {0}".format(img_name))
                        #print("img_id {0}".format(img_id))
                        #print("img_size {0}".format(img_size))
                        #print("img_status {0}".format(img_status))
                    if changes:
                        #print("w changes")
                        img_tenant_name = changes.get("tenant_name", "Unknown")
                        img_tenant_id = changes.get("tenant_id", "Unknown")
                        img_diskh = changes.get("diskh", "")
                        #print("img_tenant_name {0}".format(img_tenant_name))
                        #print("img_tenant_id {0}".format(img_tenant_id))
                    #print("Tworze")
                    storage = Storage(img_name, img_id, 'Image')
                    storage.status = img_status
                    storage.project_id = img_tenant_id
                    storage.project_name = img_tenant_name
                    #print("img size {0}".format(img_size))
                    storage.disk['value'] = int(img_size) / (1024**3)
                    #print("mnoze {0:10.2f}".format(v.disk['value']))
                    storage.type = VOL_TYPE_STD
                    storage.hrs = seconds / 3600.0
                    storage.disk['hours'] = storage.disk['value']*storage.hrs
                    #print("mnoze")
                    storage.disk['cost'] = storage.disk['hours']*img_diskh
                    #print("po")
                    if details:
                        print(storage)
                    company.image.append(storage)
                    company.hrs += storage.hrs
                    #print("1")
                    company.disk['hours'] += storage.disk['hours']
                    #print("2")
                    company.disk['cost'] += storage.disk['cost']
                    #print("3")
                    company.total_cost += storage.totalCost()
        print("Calculating servers...")
        #print("len(servers) = {0}".format(len(servers)))
        for server in servers:
            if (filterServerByDatetime(server,
                                       start_time=start_time,
                                       end_time=end_time)):
                s = Server(server.name)
                s.id = server.id
                s.status = server.status
                s.project_id = server.tenant_id
                s.project_name = server.tenant_name
                #pp.pprint(s.project_name)
                '''
                if (as_admin):
                    auth = v3.Password(auth_url=company.identity_api_url,
                                       username=username,
                                       password=password,
                                       user_domain_name='default',
                                       project_domain_name='default',
                                       )
                else:
                '''
                auth = v3.Password(auth_url=company.identity_api_url,
                                   username=username,
                                   password=password,
                                   user_domain_name='default',
                                   project_domain_name='default',
                                   project_id=None
                                   if as_admin else s.project_id,
                                   )
                sess = session.Session(auth=auth)
                nova = client.Client(API_VERSION,
                                     session=sess,
                                     )
                if (hasattr(server, 'flavor')):
                    flavor = nova.flavors.get(server.flavor['id'])
                    if (flavor):
                        #pp.pprint(flavor.__dict__)
                        if (hasattr(server, 'image')):
                            if (server.image == INSTANCE_AT_VOLUME_STR):
                                s.disk['value'] = 0
                            else:
                                s.disk['value'] = float(flavor.disk)
                        else:
                            s.disk['value'] = 0
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
                            s.disk['hours'] = s.disk['value']*s.hrs
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
                #pp.pprint(server.__dict__)
                s.disk['cost'] = s.disk['hours']*getattr(server, VOL_PFX)
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
                company.disk['hours'] += s.disk['hours']
                company.disk['cost'] += s.disk['cost']
                company.total_cost += s.totalCost()
    except NotFound as nf:
        print("Flavour not found. Check if server flavor is set to public")
        sys.exit(-22)
    except KeyError as ke:
        print("Object doesn't contain {0} attribute".
              format(ke))
        sys.exit(-23)
    except Exception as e:
        print("Unexpected error: {0}".format(e))
        sys.exit(-24)
    print("Aggregation:")
    print("\tTotal Hours: {0:.2f}".format(company.hrs))
    print("\tCPU Hours: {0:.2f}".format(company.cpu['hours']))
    print("\tCPU Hours cost: {0:.2f}".
          format(company.cpu['cost']	))
    print("\tRAM GB-Hours: {0:.2f}".format(company.ram['hours']	))
    print("\tRAM GB-Hours cost: {0:.2f}".
          format(company.ram['cost']	))
    print("\tDisk GB-Hours: {0:.2f}".format(company.disk['hours']	))
    print("\tDisk GB-Hours cost: {0:.2f}".format(company.disk['cost']	))
    print("\tTotal cost: {0:.2f}".format(company.total_cost))
    if save:
        print("Saving to file {0}".format(out_file))
        company.saveCSV(out_file, start_time, end_time, details)
    if saveDB:
        print("Saving to database {0} {1}".format(start_time, end_time))
        company.saveDB(start_time, end_time)
