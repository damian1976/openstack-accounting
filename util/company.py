import sqlite3
import csv
import pymysql
from pymongo import (MongoClient, errors)
from .os_data import AccountData


# 'Company' class
# Contains all company accounting data
class Company(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        self.__name = name
        self.__compute_api_url = ''
        self.__identity_api_url = ''
        self.__volume_api_url = ''
        self.__ramh = 0.0
        self.__vcpuh = 0.0
        self.__diskh = {
            'standard': 0,
        }
        # stores project names to be computed or 'all'
        self.__project = []
        # stores server objects to be computed
        self.__server = []
        self.__volume = []
        self.__image = []

    #def __repr__(self):
    #    return self.__name

    def getServerList(self):
        return self.__server

    def addToServerList(self, s):
        self.__server.append(s)

    def getVolumeList(self):
        return self.__volume

    def addToVolumeList(self, v):
        self.__volume.append(v)

    def getImageList(self):
        return self.__image

    def addToImageList(self, i):
        self.__image.append(i)

    def setProjectList(self, project):
        self.__project = project

    def getProjectList(self):
        return self.__project

    def getFirstProject(self):
        try:
            return self.__project[0].lower()
        except IndexError:
            return ''

    def setName(self, name):
        self.__name = name

    def getName(self):
        return self.__name

    def setComputeAPI(self, api):
        self.__compute_api_url = api

    def getComputeAPI(self):
        return self.__compute_api_url

    def setIdentityAPI(self, api):
        self.__identity_api_url = api

    def getIdentityAPI(self):
        return self.__identity_api_url

    def setVolumeAPI(self, api):
        self.__volume_api_url = api

    def getVolumeAPI(self):
        return self.__volume_api_url

    def setRamh(self, ramh):
        self.__ramh = ramh

    def getRamh(self):
        return self.__ramh

    def setVcpuh(self, vcpuh):
        self.__vcpuh = vcpuh

    def getVcpuh(self):
        return self.__vcpuh

    def setDiskh(self, value, key=None):
        if key is not None:
            try:
                self.__diskh[key] = value
            except KeyError:
                pass
        else:
            self.__diskh = value

    def getDiskh(self, key=None):
        if key is not None:
            try:
                return self.__diskh[key]
            except KeyError:
                return 0.0
        else:
            return self.__diskh

    def saveSQLite(self, start_time, end_time):
        try:
            db = sqlite3.connect('mydb')
            cursor = db.cursor()
            cursor.execute('''
                CREATE TABLE if not exists accounting(
                    project_id TEXT NOT NULL,
                    object_type TEXT NOT NULL,
                    object_id TEXT NOT NULL,
                    object_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    hours REAL NOT NULL,
                    cpu_hours REAL NOT NULL,
                    cpu_cost REAL NOT NULL,
                    gb_hours REAL NOT NULL,
                    gb_cost REAL NOT NULL,
                    ram_hours REAL NOT NULL,
                    ram_cost REAL NOT NULL,
                    PRIMARY KEY (project_id,
                                 object_id,
                                 start_date,
                                 end_date))
            ''')
            for server in self.getServerList():
                row = []
                row.append(str(server.getProjectId()))
                row.append("server")
                row.append(str(server.getId()))
                row.append(str(server.getName()))
                row.append(str(start_time))
                row.append(str(end_time))
                row.append(round(server.getHrs(), 2))
                row.append(round(server.getCPU('hours'), 2))
                row.append(round(server.getCPU('cost'), 2))
                row.append(round(server.getDisk('hours'), 2))
                row.append(round(server.getDisk('cost'), 2))
                row.append(round(server.getRAM('hours'), 2))
                row.append(round(server.getRAM('cost'), 2))
                #rows.append(row)
                print("Append {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', row)
                    db.commit()
                except sqlite3.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
            for volume in self.getVolumeList():
                row = []
                row.append(str(volume.getProjectId()))
                row.append("volume")
                row.append(str(volume.getId()))
                row.append(str(volume.getName()))
                row.append(str(start_time))
                row.append(str(end_time))
                row.append(round(volume.getHrs(), 2))
                row.append("0.0")
                row.append("0.0")
                row.append(round(volume.getDisk('hours'), 2))
                row.append(round(volume.getDisk('cost'), 2))
                row.append("0.0")
                row.append("0.0")
                print("appending {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', row)
                    db.commit()
                except sqlite3.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
            for image in self.image:
                row = []
                row.append(str(image.getProjectId()))
                row.append("image")
                row.append(str(image.getId()))
                row.append(str(image.getName()))
                row.append(str(start_time))
                row.append(str(end_time))
                row.append(round(image.getHrs(), 2))
                row.append("0.0")
                row.append("0.0")
                row.append(round(image.getDisk('hours'), 2))
                row.append(round(image.getDisk('cost'), 2))
                row.append("0.0")
                row.append("0.0")
                print("Append {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', row)
                    db.commit()
                except sqlite3.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
        except Exception as e:
            # Roll back any change if something goes wrong
            db.rollback()
            print("Error: {0}".format(e))
        finally:
            # Close the db connection
            cursor.close()
            db.close()

    #Deprecated
    def saveMySQL(self, start_time, end_time):
        try:
            db = pymysql.connect(host='localhost', user='metrix', password='psnc8*Metrix', db='metrix', cursorclass=pymysql.cursors.DictCursor)
            cursor = db.cursor()
            cursor.execute('''
                CREATE TABLE if not exists accounting(
                    project_id varchar(255) NOT NULL,
                    object_type varchar(255) NOT NULL,
                    object_id varchar(255) NOT NULL,
                    object_name varchar(255) NOT NULL,
                    start_date varchar(255) NOT NULL,
                    end_date varchar(255) NOT NULL,
                    hours REAL NOT NULL,
                    cpu_hours REAL NOT NULL,
                    cpu_cost REAL NOT NULL,
                    gb_hours REAL NOT NULL,
                    gb_cost REAL NOT NULL,
                    ram_hours REAL NOT NULL,
                    ram_cost REAL NOT NULL,
                    PRIMARY KEY (project_id(127), object_id(127), start_date(25), end_date(25)))
            ''')
            for server in self.server:
                row = []
                row.append(str(server.project_id))
                row.append("server")
                row.append(str(server.id))
                row.append(str(server.name))
                row.append(str(start_time))
                row.append(str(end_time))
                row.append(round(server.hrs, 2))
                row.append(round(server.cpu['hours'], 2))
                row.append(round(server.cpu['cost'], 2))
                row.append(round(server.disk['hours'], 2))
                row.append(round(server.disk['cost'], 2))
                row.append(round(server.ram['hours'], 2))
                row.append(round(server.ram['cost'], 2))
                print("Append {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ''', row)
                    db.commit()
                except pymysql.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
            for volume in self.volume:
                row = []
                row.append(str(volume.project_id))
                row.append("volume")
                row.append(str(volume.id))
                row.append(str(volume.name))
                row.append(str(start_time))
                row.append(str(end_time))
                row.append(round(volume.hrs, 2))
                row.append("0.0")
                row.append("0.0")
                row.append(round(volume.disk['hours'], 2))
                row.append(round(volume.disk['cost'], 2))
                row.append("0.0")
                row.append("0.0")
                print("appending {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ''', row)
                    db.commit()
                except pymysql.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
            for image in self.image:
                row = []
                row.append(str(image.project_id))
                row.append("image")
                row.append(str(image.id))
                row.append(str(image.name))
                row.append(str(start_time))
                row.append(str(end_time))
                row.append(round(image.hrs, 2))
                row.append("0.0")
                row.append("0.0")
                row.append(round(image.disk['hours'], 2))
                row.append(round(image.disk['cost'], 2))
                row.append("0.0")
                row.append("0.0")
                print("Append {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                        ''', row)
                    db.commit()
                #except sqlite3.IntegrityError as ie:
                except pymysql.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
        except Exception as e:
            # Roll back any change if something goes wrong
            db.rollback()
            print("Error: {0}".format(e))
        finally:
            # Close the db connection
            cursor.close()
            db.close()

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
                          'Total cost',
                          ]
            writer = csv.DictWriter(csvfile,
                                    fieldnames=fieldnames,
                                    delimiter=';')
            writer.writeheader()
            writer.writerow({fieldnames[0]: self.getName(),
                             fieldnames[1]: start_time,
                             fieldnames[2]: end_time,
                             fieldnames[3]:
                             str(round(self.getHrs(), 2)).
                             replace('.', ','),
                             fieldnames[4]:
                             str(round(self.getCPU('hours'), 2)).
                             replace('.', ','),
                             fieldnames[5]:
                             str(round(self.getCPU('cost'), 2)).
                             replace('.', ','),
                             fieldnames[6]:
                             str(round(self.getRAM('hours'), 2)).
                             replace('.', ','),
                             fieldnames[7]:
                             str(round(self.getRAM('cost'), 2)).
                             replace('.', ','),
                             fieldnames[8]:
                             str(round(self.getDisk('hours'), 2)).
                             replace('.', ','),
                             fieldnames[9]:
                             str(round(self.getDisk('cost'), 2)).
                             replace('.', ','),
                             fieldnames[10]:
                             str(round(self.getTotalCost(), 2)).
                             replace('.', ',')})
        if details:
            with open(filename, 'a') as csvfile:
                fieldnames = ['Object name',
                              'Object type',
                              'Start date',
                              'End date',
                              'Hours',
                              'CPU-Hours',
                              'CPU-Hours cost',
                              'RAM GB-Hours',
                              'RAM GB-Hours cost',
                              'Disk GB-Hours',
                              'Disk GB-Hours cost',
                              'Total cost',
                              ]
                writer = csv.DictWriter(csvfile,
                                        fieldnames=fieldnames,
                                        delimiter=';')
                writer.writerow({})
                writer.writeheader()
                for server in self.getServerList():
                    name = "{0} ({1})".format(server.getName(), server.getId())
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: "server",
                                    fieldnames[2]: start_time,
                                    fieldnames[3]: end_time,
                                    fieldnames[4]: str(round(
                                                       server.getHrs(),
                                                       2)).
                                    replace('.', ','),
                                    fieldnames[5]:
                                    str(round(server.getCPU('hours'), 2)).
                                    replace('.', ','),
                                    fieldnames[6]: str(round(
                                        server.getCPU('cost'), 2)).
                                    replace('.', ','),
                                    fieldnames[7]:
                                    str(round(server.getRAM('hours'), 2)).
                                    replace('.', ','),
                                    fieldnames[8]: str(round(
                                        server.getRAM('cost'), 2)).
                                    replace('.', ','),
                                    fieldnames[9]: str(round(
                                        server.getDisk('hours'), 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        server.getDisk('cost'), 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        server.getTotalCost(), 2)).
                                    replace('.', ',')})
                for volume in self.getVolumeList():
                    name = "{0} ({1})".format(volume.getName(), volume.getId())
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: "volume",
                                    fieldnames[2]: start_time,
                                    fieldnames[3]: end_time,
                                    fieldnames[4]: str(round(
                                                       volume.getHrs(),
                                                       2)).
                                    replace('.', ','),
                                    fieldnames[5]: "0",
                                    fieldnames[6]: "0",
                                    fieldnames[7]: "0",
                                    fieldnames[8]: "0",
                                    fieldnames[9]: str(round(
                                        volume.getDisk('hours'), 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        volume.getDisk('cost'), 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        volume.getTotalCost(), 2)).
                                    replace('.', ',')})
                for image in self.getImageList():
                    name = "{0} ({1})".format(image.getName(), image.getId())
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: "image",
                                    fieldnames[2]: start_time,
                                    fieldnames[3]: end_time,
                                    fieldnames[4]: str(round(
                                                       image.getHrs(),
                                                       2)).
                                    replace('.', ','),
                                    fieldnames[5]: "0",
                                    fieldnames[6]: "0",
                                    fieldnames[7]: "0",
                                    fieldnames[8]: "0",
                                    fieldnames[9]: str(round(
                                        image.getDisk('hours'), 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        image.getDisk('cost'), 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        image.getTotalCost(), 2)).
                                    replace('.', ',')})

    def saveMongo(self, start_time, end_time, connString, details=False):
        if (connString is None):
            return
        try:
            con = MongoClient(connString)
        except errors.ConnectionFailure as e:
            print("Could not connect to Mongo server: %s".format(e))
            return
        try:
            db = con.metrix
            c = db.accounting
        except:
            print("Could not connect to Mongo db")
            return
        fieldnames = ['Company name',
                      'Company id',
                      'Start date',
                      'End date',
                      'Total hours',
                      'CPU-Hours',
                      'CPU-Hours cost',
                      "RAM GB-Hours",
                      "RAM GB-Hours cost",
                      'Disk GB-Hours',
                      'Disk GB-Hours cost',
                      'Total cost',
                      ]
        try:
            company__name = self.getName().split('(')[0].strip()
        except:
            company__name = self.getName()
        try:
            company__id = self.getName().split('(')[1].strip(')')
        except:
            company__id = '0'

        c.insert_one({fieldnames[0]: company__name,
                      fieldnames[1]: company__id,
                      fieldnames[2]: start_time,
                      fieldnames[3]: end_time,
                      fieldnames[4]: str(round(self.getHrs(), 2)),
                      fieldnames[5]: str(round(self.getCPU('hours'), 2)),
                      fieldnames[6]: str(round(self.getCPU('cost'), 2)),
                      fieldnames[7]: str(round(self.getRAM('hours'), 2)),
                      fieldnames[8]: str(round(self.getRAM('cost'), 2)),
                      fieldnames[9]: str(round(self.getDisk('hours'), 2)),
                      fieldnames[10]: str(round(self.getDisk('cost'), 2)),
                      fieldnames[11]: str(round(self.getTotalCost(), 2))})
        if details:
            fieldnames = ['Object name',
                          'Object id',
                          'Object type',
                          'Start date',
                          'End date',
                          'Hours',
                          'CPU-Hours',
                          'CPU-Hours cost',
                          'RAM GB-Hours',
                          'RAM GB-Hours cost',
                          'Disk GB-Hours',
                          'Disk GB-Hours cost',
                          'Total cost',
                          'Project id',
                          'Project name']
            for server in self.getServerList():
                #name = "{0} ({1})".format(server.name, server.id)
                c.insert_one({fieldnames[0]: server.getName(),
                              fieldnames[1]: server.getId(),
                              fieldnames[2]: "server",
                              fieldnames[3]: start_time,
                              fieldnames[4]: end_time,
                              fieldnames[5]: str(round(server.getHrs(), 2)),
                              fieldnames[6]: str(round(
                                                 server.getCPU('hours'),
                                                 2)),
                              fieldnames[7]: str(round(
                                                 server.getCPU('cost'),
                                                 2)),
                              fieldnames[8]: str(round(
                                                 server.getRAM('hours'),
                                                 2)),
                              fieldnames[9]: str(round(
                                                 server.getRAM('cost'),
                                                 2)),
                              fieldnames[10]: str(round(
                                                  server.getDisk('hours'),
                                                  2)),
                              fieldnames[11]: str(round(
                                                  server.getDisk('cost'),
                                                  2)),
                              fieldnames[12]: str(round(
                                                  server.getTotalCost(),
                                                  2)),
                              fieldnames[13]: server.getProjectId(),
                              fieldnames[14]: server.getProjectName()})

            for volume in self.getVolumeList():
                #name = "{0} ({1})".format(volume.name, volume.id)
                c.insert_one({fieldnames[0]: volume.getName(),
                              fieldnames[1]: volume.getId(),
                              fieldnames[2]: "volume",
                              fieldnames[3]: start_time,
                              fieldnames[4]: end_time,
                              fieldnames[5]: str(round(
                                                 volume.getHrs(),
                                                 2)),
                              fieldnames[10]: str(round(
                                                  volume.getDisk('hours'),
                                                  2)),
                              fieldnames[11]: str(round(
                                                  volume.getDisk('cost'),
                                                  2)),
                              fieldnames[12]: str(round(
                                                  volume.getTotalCost(),
                                                  2)),
                              fieldnames[13]: volume.getProjectId(),
                              fieldnames[14]: volume.getProjectName()})
            for image in self.getImageList():
                #name = "{0} ({1})".format(image.name, image.id)
                c.insert_one({fieldnames[0]: image.getName(),
                              fieldnames[1]: image.getId(),
                              fieldnames[2]: "image",
                              fieldnames[3]: start_time,
                              fieldnames[4]: end_time,
                              fieldnames[5]: str(round(
                                                 image.getHrs(),
                                                 2)),
                              fieldnames[10]: str(round(
                                                  image.getDisk('hours'),
                                                  2)),
                              fieldnames[11]: str(round(
                                                  image.getDisk('cost'),
                                                  2)),
                              fieldnames[12]: str(round(
                                                  image.getTotalCost(),
                                                  2)),
                              fieldnames[13]: image.getProjectId(),
                              fieldnames[14]: image.getProjectName()})
