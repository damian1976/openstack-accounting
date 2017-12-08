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
        self.gbh = 0.0
        self.server = []

    def __repr__(self):
        return self.name

    def saveDB(self, start_time, end_time):
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
            rows = []
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
                row.append(round(server.gb['hours'], 2))
                row.append(round(server.gb['cost'], 2))
                row.append(round(server.ram['hours'], 2))
                row.append(round(server.ram['cost'], 2))
                row.append(round(server.totalCost(), 2))
                rows.append(row)
                print("Append {0}".format(row))
            cursor.executemany('''
                    INSERT INTO accounting VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                ''', rows)
            db.commit()
        except Exception as e:
            # Roll back any change if something goes wrong
            db.rollback()
            raise e
        finally:
            # Close the db connection
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
                             str(round(self.gb['hours'], 2)).
                             replace('.', ','),
                             fieldnames[9]:
                             str(round(self.gb['cost'], 2)).
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
                                    str(round(server.cpu['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[5]: str(round(
                                        server.cpu['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[6]:
                                    str(round(server.ram['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[7]: str(round(
                                        server.ram['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[8]: str(round(
                                        server.gb['hours'], 2)).
                                    replace('.', ','),
                                    fieldnames[9]: str(round(
                                        server.gb['cost'], 2)).
                                    replace('.', ','),
                                    fieldnames[10]: str(round(
                                        server.totalCost(), 2)).
                                    replace('.', ',')})
