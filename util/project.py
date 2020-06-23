from .os_data import AccountData


# 'Project' class
# Contains all project accounting data
class Project(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        self.__id = ''
        self.__name = name
        self.__ramh = 0.0
        self.__vcpuh = 0.0
        self.__diskh = {
            'standard': '0.0',
        }

    def __repr__(self):
        return "<Project>"

    def __str__(self):
        return self.getId()\
            + "," + self.getName()\
            + "," + str(self.getRamh())\
            + "," + str(self.getVcpuh())\
            + "," + str(self.getDiskh())\
            + "," + str(self.getCoeff())

    def setId(self, myid):
        self.__id = myid

    def getId(self):
        return self.__id

    def setName(self, name):
        self.__name = name

    def getName(self):
        return self.__name

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
