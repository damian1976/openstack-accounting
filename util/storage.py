from .os_data import AccountData


# 'Server' class
# Contains all server accounting data
class Storage(AccountData):
    def __init__(self,
                 name,
                 id,
                 typename):
        AccountData.__init__(self)
        self.name = name
        if id:
            self.id = id
        else:
            self.id = ''
        self.state = 'in-use'
        self.type = 'Standard'
        self.project_id = ''
        self.project_name = ''
        self.typename = typename

    # Returns String representation for a server object
    def __str__(self):
        str = "{0} name: {1} ({2})\n" \
              "\tHours: {3:.2f}\n" \
              "\tSize: {4:.0f}GB\n" \
              "\tType: {5}\n" \
              "\tDisk GB-Hours: {6:.2f}\n" \
              "\tVolume total cost: {7:.2f}\n"
        return str.format(self.typename,
                          self.name,
                          self.id,
                          self.hrs,
                          self.disk['value'],
                          self.type,
                          self.disk['hours'],
                          self.totalCost())

    def totalCost(self):
        try:
            self.total_cost = self.disk['cost']
        except Exception as e:
            print("Error {0}".format(e))
            return 0.0
        return self.total_cost
'''

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
'''
