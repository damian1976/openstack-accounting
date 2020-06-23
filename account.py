import sys
import pprint
import pytz
from novaclient import client
from novaclient.exceptions import Forbidden
from keystoneclient import client as ks
from keystoneclient.v3 import client as ks3
from cinderclient.v3 import client as cclient
from glanceclient import client as gclient
from keystoneauth1.identity import v3
from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneauth1 import exceptions as kse
import dateutil.parser as dup
from keystoneclient.exceptions \
    import AuthorizationFailure,\
    Unauthorized,\
    EmptyCatalog
from novaclient.exceptions \
    import ClientException
from util.project import Project
from config import (API_VERSION,
                    CINDER_API_VERSION,
                    GLANCE_API_VERSION,
                    VOL_PFX,
                    VOL_TENANT_ID_ATTR,
                    VOL_TYPE,
                    VOL_TYPE_STD,
                    LIMIT,)

pp = pprint.PrettyPrinter(indent=4)


class OpenstackAccounting(object):
    def __init__(self,
                 username,
                 password,
                 start_time,
                 end_time,
                 company,
                 conf_projects,
                 as_admin):
        self.__username = username
        self.__password = password
        self.__start_time = start_time
        self.__end_time = end_time
        self.__company = company
        self.__conf_projects = conf_projects
        self.__asAdmin = as_admin

    def getUsername(self):
        return self.__username

    def getPassword(self):
        return self.__password

    def getCompany(self):
        return self.__company

    def getAsAdmin(self):
        return self.__asAdmin

    def setConfProjectsId(self, name, value):
        #try:
        self.__conf_projects[name].id = value
        #except (IndexError, AttributeError, KeyError):
        #    pass

    def getConfProjectName(self, name):
        return self.__conf_projects[name]

    # Filters out volume by given period of time.
    def filterAndRecalculateStorageByDatetime(self,
                                              storage,
                                              start_time,
                                              end_time,
                                              type):
        start_time = start_time.replace(tzinfo=pytz.UTC)
        end_time = end_time.replace(tzinfo=pytz.UTC)
        diff_default = (end_time - start_time).total_seconds()
        created_at = ""
        status = ""
        terminated_at = ""
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
    def filterServerByDatetime(self, server, start_time, end_time):
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

    def filterActionsByDatetime(self, actions, start_time=None, end_time=None):
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

    def getStopStartTimeFrames(self, actions, period_end_time):
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

    def getOSServers(self, projects, user_tenants):
        servers = []
        projects_ids = list([x.getId() for x in projects.values()])
        #auth = None
        try:
            print("Fetching servers...")
            if (self.getAsAdmin()):
                auth = v3.Password(auth_url=self.getCompany().getIdentityAPI(),
                                   username=self.getUsername(),
                                   password=self.getPassword(),
                                   user_domain_name='default',
                                   project_domain_name='default',
                                   )
                search_opts_all = {'all_tenants': '1',
                                   #'limit': LIMIT,
                                   }
                search_opts_all_deleted = {'all_tenants': '1',
                                           'status': 'deleted',
                                           #'limit': LIMIT,
                                           }
                servers = self.__listObjects(auth,
                                             search_opts_all,
                                             search_opts_all_deleted,
                                             client,
                                             'servers',
                                             API_VERSION,
                                             LIMIT,
                                             )
                if servers:
                    if (self.getCompany().getFirstProject() != 'all'):
                        servers = [x for x in servers if x.tenant_id
                                   in projects_ids]
                    else:
                        servers = [x for x in servers if x.tenant_id
                                   in user_tenants.values()]
                    for s in servers:
                        try:
                            key = [k for k, v in projects.items()
                                   if v.getId() == s.tenant_id
                                   ]
                            tenant_name = key[0]
                            s._add_details({'tenant_name': tenant_name})
                            s._add_details({'coeff': projects[tenant_name].getCoeff()})
                            s._add_details({'ramh': projects[tenant_name].getRamh()})
                            s._add_details({'vcpuh': projects[tenant_name].getVcpuh()})
                            s._add_details({VOL_PFX:
                                            projects[tenant_name].
                                            getDiskh('standard')
                                            }
                                           )
                        except KeyError:
                            key = "Unknown"
                        except IndexError:
                            s._add_details({'tenant_name': key})
            else:
                search_opts_all = {} #'limit': LIMIT, }
                search_opts_all_deleted = {'status': 'deleted',
                                           #'limit': LIMIT,
                                           }
                if (self.getCompany().getFirstProject() == 'all'):
                    for tenant_name, tenant_id in user_tenants.items():
                        auth = v3.Password(auth_url=self.getCompany().
                                           getIdentityAPI(),
                                           username=self.getUsername(),
                                           password=self.getPassword(),
                                           user_domain_name='default',
                                           project_domain_name='default',
                                           project_id=tenant_id
                                           )
                        srvs = self.__listObjects(auth,
                                                  search_opts_all,
                                                  search_opts_all_deleted,
                                                  client,
                                                  'servers',
                                                  API_VERSION,
                                                  LIMIT,
                                                  )
                        if srvs:
                            if (tenant_id in projects_ids):
                                #print("tenant_id in projects_ids")
                                try:
                                    project = projects[tenant_name]
                                    for s in srvs:
                                        s._add_details(
                                            {'tenant_name': project.name}
                                        )
                                        s._add_details({'coeff': project.getCoeff()})
                                        s._add_details({'ramh': project.getRamh()})
                                        s._add_details({'vcpuh': project.getVcpuh()})
                                        s._add_details({VOL_PFX:
                                                        projects[tenant_name].
                                                        getDiskh('standard')
                                                        }
                                                       )
                                except KeyError:
                                    #print("KEY ERROR")
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
                                    s._add_details({'coeff': self.getCompany().getCoeff()})
                                    s._add_details({'ramh': self.getCompany().getRamh()})
                                    s._add_details({'vcpuh': self.getCompany().getVcpuh()})
                                    s._add_details({VOL_PFX:
                                                    projects[tenant_name].
                                                    getDiskh('standard')
                                                    }
                                                   )
                            if not servers:
                                servers = srvs
                            else:
                                servers += srvs
                else:
                    for name, project in projects.items():
                        auth = v3.Password(auth_url=self.getCompany().
                                           getIdentityAPI(),
                                           username=self.getUsername(),
                                           password=self.getPassword(),
                                           user_domain_name='default',
                                           project_domain_name='default',
                                           project_id=project.getId()
                                           )
                        srvs = self.__listObjects(auth,
                                                  search_opts_all,
                                                  search_opts_all_deleted,
                                                  client,
                                                  'servers',
                                                  API_VERSION
                                                  )
                        if srvs:
                            for s in srvs:
                                s._add_details({'tenant_name': name})
                                s._add_details({'coeff': project.getCoeff()})
                                s._add_details({'ramh': project.getRamh()})
                                s._add_details({'vcpuh': project.getVcpuh()})
                                s._add_details({VOL_PFX:
                                                project.getDiskh('standard')
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
            print("Error for {0} auth: {1}".format(self.getUsername(), auf))
            sys._exit(-2)
        except Unauthorized as unauth:
            print("Error for {0} auth: {1}"
                  .format(self.getUsername(), unauth.message))
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
        print("Total: {0}".format(len(servers)))
        print("Done.")
        return servers

    def getOSUSers(self):
        try:
            os_users = dict()
            ksclient = None
            print("Fetching users...")
            #if admin fetch all OS users
            if (self.getAsAdmin()):
                auth = v3.Password(auth_url=self.getCompany().
                                   getIdentityAPI(),
                                   username=self.getUsername(),
                                   password=self.getPassword(),
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
                os_users.update({self.getUsername(): self.getPassword()})
            #print("Done.")
        except AuthorizationFailure as auf:
            print("getOSUSers: Error for {0} auth: {1}".
                  format(self.getUsername(), auf))
            sys.exit(-7)
        except Unauthorized as unauth:
            print("getOSUSers: Error for {0} auth: {1}"
                  .format(self.getUsername(), unauth.message))
            sys.exit(-8)
        except EmptyCatalog as cc:
            print("getOSUSers: Error when fetching users: {0}"
                  .format(cc.message))
            sys.exit(-9)
        except kse.http.ServiceUnavailable as su:
            print("getOSUSers: Error when fetching users: {0}"
                  .format(su.message))
            sys.exit(-10)
        print("Total: {0}".format(len(os_users)))
        print("Done.")
        return ksclient, os_users

    def __listObjects(self,
                      auth,
                      search_opts_all,
                      search_opts_all_deleted,
                      client,
                      typename,
                      api,
                      limit=None,
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
                search_opts=search_opts_all,
                limit=limit,
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
                    print("__listObjects: Error in '{0}'' deleted: '{1}'".
                          format(typename, ce.message))
                    objects_deleted = []
        #print("len(total)={0}".format(len(user_objects)))
        return user_objects

    def getOSUsersVolumes(self, projects, user_tenants):
        print("getOSUsersVolume, company: {0}, API: {1}".
              format(self.getCompany().getName(), self.getCompany().getVolumeAPI()))
        try:
            user_volumes = []
            projects_ids = list([x.getId() for x in projects.values()])
            #ksclient, os_users = getOSUSers(username, password)
            if (self.getAsAdmin()):
                print("Fetching volumes (admin mode)...")
                try:
                    authcinder = v3.Password(auth_url=self.getCompany().
                                             getVolumeAPI(),
                                             username=self.getUsername(),
                                             password=self.getPassword(),
                                             user_domain_name='default',
                                             project_domain_name='default',
                                             )
                    search_opts_all = {'all_tenants': '1',
                                       #'limit': LIMIT,
                                       }
                    search_opts_all_deleted = {'all_tenants': '1',
                                               'status': 'deleted',
                                               #'limit': LIMIT,
                                               }
                    
                    user_volumes = self.__listObjects(authcinder,
                                                      search_opts_all,
                                                      search_opts_all_deleted,
                                                      cclient,
                                                      'volumes',
                                                      CINDER_API_VERSION,
                                                      LIMIT,
                                                      )
                except kse.connection.ConnectFailure as ccf:
                    print("getOSUsersVolumes: Connection error: {0}"
                      .format(ccf.message))
                    user_volumes = None
                    pass
                if user_volumes:
                    if (self.getCompany().getFirstProject() != 'all'):
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
                                   if v.getId() == getattr(vl, VOL_TENANT_ID_ATTR)
                                   ]
                            project = projects.get(key[0], None)
                            dir(project)
                            tenant_name = project.getName()
                            vol_type_name = getattr(vl, VOL_TYPE)
                            if (vol_type_name is not None):
                                vl._add_details({
                                    VOL_PFX: project.getDiskh(vol_type_name.lower())
                                })
                            else:
                                vl._add_details({
                                    VOL_PFX: project.getDiskh(VOL_TYPE_STD.lower())
                                })
                            #print("TENANT NAME: {0}".format(tenant_name))
                            vl._add_details({'tenant_name': tenant_name})
                        except KeyError:
                            key = "Unknown"
                        except IndexError:
                            vl._add_details({'tenant_name': key})
                            vl._add_details({VOL_PFX: '0.0'})
            else:
                print("Fetching volumes (user mode)...")
                search_opts_all = {}#'limit': LIMIT, }
                search_opts_all_deleted = {'status': 'deleted',
                                           #'limit': LIMIT,
                                           }
                if (self.getCompany().project[0].lower() == 'all'):
                    for tenant_name, tenant_id in user_tenants.items():
                        try: 
                            authcinder = v3.Password(auth_url=self.getCompany().
                                                     getVolumeAPI(),
                                                     username=self.getUsername(),
                                                     password=self.getPassword(),
                                                     user_domain_name='default',
                                                     project_domain_name='default',
                                                     project_id=tenant_id,
                                                     )
                            usr_vls = self.__listObjects(authcinder,
                                                         search_opts_all,
                                                         search_opts_all_deleted,
                                                         cclient,
                                                         'volumes',
                                                         CINDER_API_VERSION,
                                                         LIMIT,
                                                         )
                        except kse.connection.ConnectFailure as ccf:
                            print("getOSUsersVolumes: Connection error: {0}"
                            .format(ccf.message))
                            usr_vls = None
                            pass
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
                                                VOL_PFX: project.getDiskh(
                                                    vol_type_name.lower()
                                                )
                                            })
                                        else:
                                            vl._add_details({
                                                VOL_PFX: project.getDiskh(
                                                    VOL_TYPE_STD.lower()
                                                )
                                            })
                                except KeyError:
                                    for vl in usr_vls:
                                        dir(vl)
                                        vl._add_details({'tenant_name': 'Unknown'})
                                        vl._add_details({
                                            VOL_PFX: project.getDiskh(
                                                VOL_TYPE_STD.lower()
                                            )
                                        })
                            else:
                                for vl in usr_vls:
                                    dir(vl)
                                    vl._add_details({'tenant_name': tenant_name})
                                    vl._add_details({
                                        VOL_PFX: project.getDiskh(
                                            VOL_TYPE_STD.lower()
                                        )
                                    })
                            if not user_volumes:
                                user_volumes = usr_vls
                            else:
                                user_volumes += usr_vls
                else:
                    for name, project in projects.items():
                        authcinder = v3.Password(auth_url=self.getCompany().
                                                 getVolumeAPI(),
                                                 username=self.getUsername(),
                                                 password=self.getPassword(),
                                                 user_domain_name='default',
                                                 project_domain_name='default',
                                                 project_id=project.getId(),
                                                 )
                        usr_vls = self.__listObjects(authcinder,
                                                     search_opts_all,
                                                     search_opts_all_deleted,
                                                     cclient,
                                                     'volumes',
                                                     CINDER_API_VERSION,
                                                     LIMIT,
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
                                        VOL_PFX: project.getDiskh(
                                            vol_type_name.lower()
                                        )
                                    })
                                else:
                                    vl._add_details({
                                        VOL_PFX: project.getDiskh(
                                            VOL_TYPE_STD.lower()
                                        )
                                    })
                            if not user_volumes:
                                user_volumes = usr_vls
                            else:
                                user_volumes += usr_vls
            if not user_volumes:
                raise ValueError
        except ValueError as ve:
            print("getOSUsersVolumes: Volumes not found or "
                  "Error parsing projects for given username: {0}"
                  .format(ve))
            pass
            #sys.exit(-11)
        except kse.http.ServiceUnavailable as su:
            print("getOSUsersVolumes: Error when listing volumes: {0}"
                  .format(su.message))
            pass
            #sys.exit(-12)
        
            #sys.exit(-13)
        print("Total: {0}".format(len(user_volumes)))
        print("Done.")
        #pp.pprint(user_volumes)
        return user_volumes

    def getOSUsersImages(self, projects, user_tenants):
        try:
            user_images = []
            projects_ids = list([x.getId() for x in projects.values()])
            print("Fetching images...")
            if (self.getAsAdmin()):
                authglance = v3.Password(auth_url=self.getCompany().
                                         getVolumeAPI(),
                                         username=self.getUsername(),
                                         password=self.getPassword(),
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
                user_images = self.__listObjects(authglance,
                                                 search_opts_all,
                                                 search_opts_all_deleted,
                                                 gclient,
                                                 'images',
                                                 GLANCE_API_VERSION,
                                                 )
                if user_images:
                    '''
                    print("user_images")
                    for x in user_images:
                        print("ID={0} {1}".format(x.get('owner_id'), x.get('owner')))
                    '''
                    if (self.getCompany().getFirstProject() != 'all'):
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
                    #pp.pprint(user_images)
                    for img in user_images:
                        try:
                            #dir(vl)
                            #print(vl)
                            #print("11")
                            key = [k for k, v in projects.items()
                                   if v.getId() == img.get('owner')
                                   ]
                            project = projects.get(key[0], None)
                            dir(project)
                            tenant_name = project.getName()
                            tenant_id = project.getId()
                            img.__setattr__(VOL_PFX,
                                            project.getDiskh(
                                                VOL_TYPE_STD.lower()
                                            )
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
                print("not user_images")
                search_opts_all = {}#'limit': LIMIT, }
                search_opts_all_deleted = {'status': 'deleted',
                                           #'limit': LIMIT,
                                           }
                if (self.getCompany().getFirstProject() == 'all'):
                    print("First project == 'all'")
                    for tenant_name, tenant_id in user_tenants.items():
                        #print("tenant_name={0} tenant_id={1}".format(tenant_name, tenant_id))
                        authglance = v3.Password(auth_url=self.getCompany().
                                                 getVolumeAPI(),
                                                 username=self.getUsername(),
                                                 password=self.getPassword(),
                                                 user_domain_name='default',
                                                 project_domain_name='default',
                                                 project_id=tenant_id,
                                                 )
                        usr_imgs = self.__listObjects(authglance,
                                                      search_opts_all,
                                                      search_opts_all_deleted,
                                                      gclient,
                                                      'images',
                                                      GLANCE_API_VERSION,
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
                                                        project.getDiskh(
                                                            VOL_TYPE_STD.lower()
                                                        )
                                                        )
                                except KeyError:
                                    for img in usr_imgs:
                                        dir(img)
                                        img.__setattr__('tenant_name', 'Unknown')
                                        img.__setattr__('tenant_id', '-1')
                                        img.__setattr__(VOL_PFX,
                                                        project.getDiskh(
                                                            VOL_TYPE_STD.lower()
                                                        )
                                                        )
                            else:
                                for img in usr_imgs:
                                    dir(img)
                                    img.__setattr__('tenant_name', tenant_name)
                                    img.__setattr__('tenant_id', tenant_id)
                                    img.__setattr__(VOL_PFX,
                                                    project.getDiskh(
                                                        VOL_TYPE_STD.lower()
                                                    )
                                                    )
                                    #vl._add_details({'tenant_name': tenant_name})
                            if not user_images:
                                user_images = usr_imgs
                            else:
                                user_images += usr_imgs
                else:
                    print("First project != 'all'")
                    for name, project in projects.items():
                        authglance = v3.Password(auth_url=self.getCompany().
                                                 getVolumeAPI(),
                                                 username=self.getUsername(),
                                                 password=self.getPassword(),
                                                 user_domain_name='default',
                                                 project_domain_name='default',
                                                 project_id=project.getId()
                                                 )
                        usr_imgs = self.__listObjects(authglance,
                                                      search_opts_all,
                                                      search_opts_all_deleted,
                                                      gclient,
                                                      'images',
                                                      GLANCE_API_VERSION,
                                                      )
                        usr_imgs = [x for x in usr_imgs
                                    if x.get('owner') == project.getId()
                                    and x.get('visibility') != 'public'
                                    ]
                        if usr_imgs:
                            for img in usr_imgs:
                                #print(vl)
                                img.__setattr__('tenant_name', name)
                                img.__setattr__('tenant_id', project.getId())
                                img.__setattr__(VOL_PFX,
                                                project.getDiskh(
                                                    VOL_TYPE_STD.lower()
                                                    )
                                                )
                            if not user_images:
                                user_images = usr_imgs
                            else:
                                user_images += usr_imgs
            if not user_images:
                raise ValueError
        except ValueError as ve:
            print("getOSUsersImages: Images not found or "
                  "Error parsing projects for given username: {0}"
                  .format(ve))
            pass
        except kse.http.ServiceUnavailable as su:
            print("getOSUsersImages: Error when listing volumes: {0}"
                  .format(su.message))
            sys.exit(-15)
        except AttributeError as ae:
            print("getOSUsersImages: Attribute error: {0}"
                  .format(ae))
            sys.exit(-16)
        print("Total: {0}".format(len(user_images)))
        print("Done.")
        #pp.pprint(user_volumes)
        return user_images

    def getOSUsersProjects(self):
        try:
            user_tenants = dict()
            ksclient, os_users = self.getOSUSers()
            # user_tenants contain all users tenants
            print("Fetching users projects...")
            #print(users)
            for uname, uid in os_users.items():
            # Get tenants for given user
                if (self.getAsAdmin()):
                    ksdata = ksclient.projects.list(user=uid)
                else:
                    #opts = loading.get_plugin_loader('password')
                    loader = loading.get_plugin_loader('password')
                    #user tenants
                    auth = loader.\
                        load_from_options(auth_url=self.getCompany().
                                          getComputeAPI(),
                                          username=self.getUsername(),
                                          password=self.getPassword(),
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
            print("getOSUsersProjects: Project {0} unavailable \
                  for given username".
                  format(ke))
            #continue
        except ValueError as ve:
            print("getOSUsersProjects: Error parsing projects\
                  for given username: {1}".format(ve))
            sys.exit(-17)
        except AuthorizationFailure as auf:
            print("getOSUsersProjects: Error for {0} auth: {1}".format(
                self.getUsername(), auf)
            )
            sys.exit(-18)
        except Unauthorized as unauth:
            print("getOSUsersProjects: Error for {0} auth: {1}"
                  .format(self.getUsername(), unauth.message))
            sys.exit(-19)
        except EmptyCatalog as cc:
            print("getOSUsersProjects: Error when listing all users: {0}"
                  .format(cc.message))
            sys.exit(-20)
        except kse.http.ServiceUnavailable as su:
            print("getOSUsersProjects: Error when listing users projects: {0}"
                  .format(su.message))
            sys.exit(-21)
        print("Total: {0}".format(len(user_tenants)))
        print("Done.")
        return user_tenants

    def updateOSUserProjectsWithConfig(self, user_tenants):
        print("updateOSUserProjectsWithConfig")
        projects = dict()
        if (user_tenants):
            print("Updating {0} projects with config data".
                  format(len(user_tenants.items())))
            # Get all tenants for user in case 'all' is set as project name
            # in the config file. otherwise use just a name set
            if (self.getCompany().getFirstProject() == 'all'):
                for tname, tid in user_tenants.items():
                    try:
                        self.setConfProjectsId(tname, tid)
                        projects.update({tname:
                                         self.getConfProjectName(tname)})
                    except (KeyError, AttributeError):
                        p = Project(tname)
                        p.setId(tid)
                        p.setCoeff(self.getCompany().getCoeff())
                        p.setDiskh(self.getCompany().getDiskh())
                        p.setRamh(self.getCompany().getRamh())
                        p.setVcpuh(self.getCompany().getVcpuh())
                        projects.update({tname: p})
            else:
                for tname, tid in user_tenants.items():
                    try:
                        self.setConfProjectsId(tname, tid)
                        projects.update({tname:
                                         self.getConfProjectName(tname)})
                    except (KeyError, AttributeError):
                        pass
        #return projects only we want with updated values from config
        return projects

    def performAccounting(self):
        print("performAccounting")
