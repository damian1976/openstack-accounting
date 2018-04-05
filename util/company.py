import sqlite3
import csv
from .os_data import AccountData


# 'Company' class
# Contains all company accounting data
class Company(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        self.name = name
        self.compute_api_url = ''
        self.identity_api_url = ''
        self.ramh = 0.0
        self.vcpuh = 0.0
        self.diskh = {
            'standard': 0,
        }
        # stores project names to be computed or 'all'
        self.project = []
        # stores server objects to be computed
        self.server = []
        self.volume = []
        self.image = []

    def __repr__(self):
        return self.name

    def saveDB_old(self, start_time, end_time):
        try:
            db = sqlite3.connect('mydb')
            cursor = db.cursor()
            cursor.execute('''
                CREATE TABLE if not exists accounting(
                    project_id TEXT NOT NULL,
                    project_name TEXT NOT NULL,
                    server_id TEXT NOT NULL,
                    server_name TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    hours REAL NOT NULL,
                    cpu_hours REAL NOT NULL,
                    cpu_cost REAL NOT NULL,
                    gb_hours REAL NOT NULL,
                    gb_cost REAL NOT NULL,
                    ram_hours REAL NOT NULL,
                    ram_cost REAL NOT NULL,
                    total_cost REAL NOT NULL,
                    PRIMARY KEY (project_id, server_id, start_date, end_date))
            ''')
            #rows = []
            for server in self.server:
                row = []
                row.append(str(server.project_id))
                row.append(str(server.project_name))
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
                row.append(round(server.totalCost(), 2))
                #rows.append(row)
                print("Append {0}".format(row))
                try:
                    cursor.execute('''
                        INSERT INTO accounting
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', row)
                    db.commit()
                except sqlite3.IntegrityError as ie:
                    print("Error inserting data twice: {0}".format(ie))
                    db.rollback()
                    continue
        except Exception as e:
            # Roll back any change if something goes wrong
            db.rollback()
            print("Error: {0}".forma(e.message))
        finally:
            # Close the db connection
            cursor.close()
            db.close()

    def saveDB(self, start_time, end_time):
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
                        VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
                        ''', row)
                    db.commit()
                except sqlite3.IntegrityError as ie:
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
                             str(round(self.cpu['hours'], 2)).
                             replace('.', ','),
                             fieldnames[5]:
                             str(round(self.cpu['cost'], 2)).
                             replace('.', ','),
                             fieldnames[6]:
                             str(round(self.ram['hours'], 2)).
                             replace('.', ','),
                             fieldnames[7]:
                             str(round(self.ram['cost'], 2)).
                             replace('.', ','),
                             fieldnames[8]:
                             str(round(self.disk['hours'], 2)).
                             replace('.', ','),
                             fieldnames[9]:
                             str(round(self.disk['cost'], 2)).
                             replace('.', ','),
                             fieldnames[10]:
                             str(round(self.total_cost, 2)).
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
                              'Total cost']
                writer = csv.DictWriter(csvfile,
                                        fieldnames=fieldnames,
                                        delimiter=';')
                writer.writerow({})
                writer.writeheader()
                for server in self.server:
                    name = "{0} ({1})".format(server.name, server.id)
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: "server",
                                    fieldnames[2]: start_time,
                                    fieldnames[3]: end_time,
                                    fieldnames[4]: str(round(server.hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[5]:
                                    str(round(server.cpu['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[6]: str(round(
                                        server.cpu['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[7]:
                                    str(round(server.ram['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[8]: str(round(
                                        server.ram['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[9]: str(round(
                                        server.disk['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        server.disk['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        server.totalCost(), 2)).
                                    replace('.', ',')})
                for volume in self.volume:
                    name = "{0} ({1})".format(volume.name, volume.id)
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: "volume",
                                    fieldnames[2]: start_time,
                                    fieldnames[3]: end_time,
                                    fieldnames[4]: str(round(volume.hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[5]: "0",
                                    fieldnames[6]: "0",
                                    fieldnames[7]: "0",
                                    fieldnames[8]: "0",
                                    fieldnames[9]: str(round(
                                        volume.disk['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        volume.disk['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        volume.totalCost(), 2)).
                                    replace('.', ',')})
                for image in self.image:
                    name = "{0} ({1})".format(image.name, image.id)
                    writer.writerow({fieldnames[0]: name,
                                    fieldnames[1]: "image",
                                    fieldnames[2]: start_time,
                                    fieldnames[3]: end_time,
                                    fieldnames[4]: str(round(image.hrs, 2)).
                                    replace('.', ','),
                                    fieldnames[5]: "0",
                                    fieldnames[6]: "0",
                                    fieldnames[7]: "0",
                                    fieldnames[8]: "0",
                                    fieldnames[9]: str(round(
                                        image.disk['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        image.disk['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[11]: str(round(
                                        image.totalCost(), 2)).
                                    replace('.', ',')})
