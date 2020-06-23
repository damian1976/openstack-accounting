class AccountData(object):
    def __init__(self):
        self.__hrs = 0.0
        self.__ram = {
            'value': 0.0,
            'hours': 0.0,
            'cost': 0.0,
        }
        self.__cpu = {
            'value': 0.0,
            'hours': 0.0,
            'cost': 0.0,
        }
        self.__disk = {
            'value': 0.0,
            'hours': 0.0,
            'cost': 0.0,
        }
        self.__totalCost = 0.0
        self.__coeff = {
            "active": 0.0,
            "shelve": 0.0,
            "stop": 0.0,
            "shelve_cpu": 0.0,
            "shelve_ram": 0.0,
            "shelve_disk": 0.0,
            "stop_cpu": 0.0,
            "stop_ram": 0.0,
            "stop_disk": 0.0,
            "active_cpu": 0.0,
            "active_ram": 0.0,
            "active_disk": 0.0,
        }

    def __repr__(self):
        return "<AccountData>"

    def addHrs(self, value):
        self.__hrs += value

    def subHrs(self, value):
        self.__hrs -= value

    def mulHrs(self, value):
        self.__hrs *= value

    def setHrs(self,  value):
        self.__hrs = value

    def getHrs(self):
        return self.__hrs

    def setTotalCost(self, totalCost):
        self.__totalCost = totalCost

    def addTotalCost(self, totalCost):
        self.__totalCost += totalCost

    def getTotalCost(self):
        return self.__totalCost

    def setCoeff(self, value, key=None):
        if key is not None:
            try:
                self.__coeff[key] = value
            except KeyError:
                pass
        else:
            self.__coeff = value

    def getCoeff(self, key=None):
        if key is not None:
            try:
                return self.__coeff[key]
            except KeyError:
                return 0.0
        else:
            return self.__coeff

    def addRAM(self, value, key=None):
        if key is not None:
            try:
                self.__ram[key] += value
            except KeyError:
                pass
        else:
            self.__ram += value

    def subRAM(self, value, key=None):
        if key is not None:
            try:
                self.__ram[key] -= value
            except KeyError:
                pass
        else:
            self.__ram -= value

    def mulRAM(self, value, key=None):
        if key is not None:
            try:
                self.__ram[key] *= value
            except KeyError:
                pass
        else:
            self.__ram *= value

    def setRAM(self, value, key=None):
        if key is not None:
            try:
                self.__ram[key] = value
            except KeyError:
                pass
        else:
            self.__ram = value

    def getRAM(self, key=None):
        if key is not None:
            try:
                return self.__ram[key]
            except KeyError:
                return 0.0
        else:
            return self.__ram

    def addCPU(self, value, key=None):
        if key is not None:
            try:
                self.__cpu[key] += value
            except KeyError:
                pass
        else:
            self.__cpu += value

    def subCPU(self, value, key=None):
        if key is not None:
            try:
                self.__cpu[key] -= value
            except KeyError:
                pass
        else:
            self.__cpu -= value

    def mulCPU(self, value, key=None):
        if key is not None:
            try:
                self.__cpu[key] *= value
            except KeyError:
                pass
        else:
            self.__cpu *= value

    def setCPU(self, value, key=None):
        if key is not None:
            try:
                self.__cpu[key] = value
            except KeyError:
                pass
        else:
            self.__cpu = value

    def getCPU(self, key=None):
        if key is not None:
            try:
                return self.__cpu[key]
            except KeyError:
                return 0.0
        else:
            return self.__cpu

    def addDisk(self, value, key=None):
        if key is not None:
            try:
                self.__disk[key] += value
            except KeyError:
                pass
        else:
            self.__disk += value

    def subDisk(self, value, key=None):
        if key is not None:
            try:
                self.__disk[key] -= value
            except KeyError:
                pass
        else:
            self.__disk -= value

    def mulDisk(self, value, key=None):
        if key is not None:
            try:
                self.__disk[key] *= value
            except KeyError:
                pass
        else:
            self.__disk *= value

    def setDisk(self, value, key=None):
        if key is not None:
            try:
                self.__disk[key] = value
            except KeyError:
                pass
        else:
            self.__disk = value

    def getDisk(self, key=None):
        if key is not None:
            try:
                return self.__disk[key]
            except KeyError:
                return 0.0
        else:
            return self.__disk
