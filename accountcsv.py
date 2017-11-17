import csv


def saveCSV(company, filename, start_time, end_time, details=False):
    from account import Company
    if (not isinstance(company, Company) and not company):
        raise TypeError
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
        writer.writerow({fieldnames[0]: company.name,
                         fieldnames[1]: start_time,
                         fieldnames[2]: end_time,
                         fieldnames[3]:
                         str(round(company.hrs, 2)).
                         replace('.', ','),
                         fieldnames[4]:
                         str(round(company.cpu['hours'], 2)).
                         replace('.', ','),
                         fieldnames[5]:
                         str(round(company.cpu['cost'], 2)).
                         replace('.', ','),
                         fieldnames[6]:
                         str(round(company.ram['hours'], 2)).
                         replace('.', ','),
                         fieldnames[7]:
                         str(round(company.ram['cost'], 2)).
                         replace('.', ','),
                         fieldnames[8]:
                         str(round(company.gb['hours'], 2)).
                         replace('.', ','),
                         fieldnames[9]:
                         str(round(company.gb['cost'], 2)).
                         replace('.', ','),
                         fieldnames[10]:
                         str(round(company.total_cost, 2)).
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
            for server in company.server:
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
