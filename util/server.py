from .os_data import AccountData
import unicodedata
import re


# 'Server' class
# Contains all server accounting data
class Server(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        m_name = unicodedata.normalize('NFD',
                                       re.sub("[\(\[].*?[\)\]]",
                                              "",
                                              name)).\
            encode('ascii', 'ignore')
        self.__name = m_name.decode('UTF-8')
        #self.__name = name
        self.__id = ''
        self.__state = 'active'
        self.__projectId = ''
        self.__projectName = ''

    def setName(self, name):
        self.__name = name

    def getName(self):
        return self.__name

    def setId(self, id):
        self.__id = id

    def getId(self):
        return self.__id

    def setState(self, state):
        self.__state = state

    def getState(self):
        return self.__state

    def setProjectId(self, id):
        self.__projectId = id

    def getProjectId(self):
        return self.__projectId

    def setProjectName(self, name):
        self.__projectName = name

    def getProjectName(self):
        return self.__projectName

    def __repr__(self):
        return "<Server>"

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
        return str.format(self.getName(),
                          self.getId(),
                          self.getHrs(),
                          self.getCPU('hours'),
                          self.getCPU('cost'),
                          self.getRAM('hours'),
                          self.getRAM('cost'),
                          self.getDisk('hours'),
                          self.getDisk('cost'),
                          self.getTotalCost())

    # Updates server flavors with STOP. SHELVE statuses from config
    def updateHoursAndVolumes(self,
                              stop_timeframes,
                              shelve_timeframes,
                              delete_timeframes,
                              coeff,
                              ):
        if delete_timeframes:
            for hours in delete_timeframes:
                self.subHrs(hours)
                self.subDisk(self.getDisk('value')*hours, 'hours')
                self.subCPU(self.getCPU('value')*hours, 'hours')
                self.subRAM(self.getRAM('value')*hours, 'hours')
        if stop_timeframes and coeff:
            try:
                for hours in stop_timeframes:
                    self.subHrs(hours*(1.0 - coeff['stop']))
                    self.subCPU(self.getCPU('value')*hours*(1.0 - coeff['stop_cpu']), 'hours')
                    self.subRAM(self.getRAM('value')*hours*(1.0 - coeff['stop_ram']), 'hours')
                    self.subDisk(self.getDisk('value')*hours*(1.0 - coeff['stop_disk']), 'hours')
            except KeyError:
              pass
        if shelve_timeframes and coeff:
            try:
                for hours in shelve_timeframes:
                    self.subHrs(hours*(1.0 - coeff['shelve']))
                    self.subCPU(self.getCPU('value')*hours*(1.0 - coeff['shelve_cpu']), 'hours')
                    self.subRAM(self.getRAM('value')*hours*(1.0 - coeff['shelve_ram']), 'hours')
                    self.subDisk(self.getDisk('value')*hours*(1.0 - coeff['shelve_disk']), 'hours')
            except KeyError:
                pass
        if (self.getHrs() == 0.0):
            self.setCPU(0.0, 'hours')
            self.setRAM(0.0, 'hours')
            self.setDisk(0.0, 'hours')

    # Updates server flavors with ACTIVE status coefficients from config
    def updateMetricHoursWithActiveStatus(self, coeff):
        if (not coeff):
            return
        self.mulHrs(coeff['active'])
        self.mulDisk(coeff['active_disk'], 'hours')
        self.mulCPU(coeff['active_cpu'], 'hours')
        self.mulRAM(coeff['active_ram'], 'hours')

    # Returns total cost for a server
    def getTotalCost(self):
        try:
            self.__totalCost = (max(
                self.getCPU('cost'),
                self.getRAM('cost')
                ) + self.getDisk('cost'))
        except Exception as e:
            print("Error {0}".format(e))
            return 0.0
        return self.__totalCost
