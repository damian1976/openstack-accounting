import sqlite3


def saveDB(company, start_time, end_time):
    from account import Company
    if (not isinstance(company, Company) and not company):
        raise TypeError
    db = sqlite3.connect('mydb')
    cursor = db.cursor()
    cursor.execute('''
        CREATE TABLE if not exists accounting(
            project_id TEXT NOT NULL,
            project_name TEXT,
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
    for server in company.server:
        row = []
        row.append(server.project_id)
        row.append(server.project_name)
        row.append(server.id)
        row.append(server.name)
        row.append(start_time)
        row.append(end_time)
        row.append(round(server.hrs, 2))
        row.append(round(server.cpu['hours'], 2))
        row.append(round(server.cpu['cost'], 2))
        row.append(round(server.gb['hours'], 2))
        row.append(round(server.gb['cost'], 2))
        row.append(round(server.ram['hours'], 2))
        row.append(round(server.ram['cost'], 2))
        row.append(round(server.totalCost(), 2))
        rows.append(row)
    try:
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
