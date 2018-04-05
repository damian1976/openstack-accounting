from .os_data import AccountData


# 'Server' class
# Contains all server accounting data
class Server(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        self.name = name
        self.id = ''
        self.state = 'active'
        self.project_id = ''
        self.project_name = ''

    # Returns String representation for a server object
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
                          self.cpu['hours'],
                          self.cpu['cost'],
                          self.ram['hours'],
                          self.ram['cost'],
                          self.disk['hours'],
                          self.disk['cost'],
                          self.totalCost())

    # Updates server flavors with STOP. SHELVE statuses from config
    def updateHoursAndVolumes(self,
                              stop_timeframes,
                              shelve_timeframes,
                              delete_timeframes,
                              coeff,
                              ):
        if delete_timeframes:
            for hours in delete_timeframes:
                self.hrs -= hours
                self.disk['hours'] -= self.disk['value']*hours
                self.cpu['hours'] -= self.cpu['value']*hours
                self.ram['hours'] -= self.ram['value']*hours
        if stop_timeframes:
            for hours in stop_timeframes:
                self.hrs -= hours*(1.0 - coeff['stop'])
                self.cpu['hours'] -=\
                    self.cpu['value']*hours*(1.0 - coeff['stop_cpu'])
                self.ram['hours'] -=\
                    self.ram['value']*hours*(1.0 - coeff['stop_ram'])
                self.disk['hours'] -=\
                    self.disk['value']*hours*(1.0 - coeff['stop_disk'])
        if shelve_timeframes:
            for hours in shelve_timeframes:
                self.hrs -= hours*(1.0 - coeff['shelve'])
                self.cpu['hours'] -=\
                    self.cpu['value']*hours*(1.0 - coeff['shelve_cpu'])
                self.ram['hours'] -=\
                    self.ram['value']*hours*(1.0 - coeff['shelve_ram'])
                self.disk['hours'] -=\
                    self.disk['value']*hours*(1.0 - coeff['shelve_disk'])
        if (self.hrs == 0.0):
            self.cpu['hours'] = self.ram['hours'] = self.disk['hours'] = 0.0

    # Updates server flavors with ACTIVE status coefficients from config
    def updateMetricHoursWithActiveStatus(self, coeff):
        if (not coeff):
            return
        self.hrs *= coeff['active']
        self.disk['hours'] *= coeff['active_disk']
        self.cpu['hours'] *= coeff['active_cpu']
        self.ram['hours'] *= coeff['active_ram']

    # Returns total cost for a server
    def totalCost(self):
        try:
            self.total_cost = max(
                self.cpu['cost'],
                self.ram['cost']
                ) + self.disk['cost']
        except Exception as e:
            print("Error {0}".format(e))
            return 0.0
        return self.total_cost
