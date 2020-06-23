from .os_data import AccountData
import unicodedata
import re


# 'Server' class
# Contains all Storage (Volume/Image)
# accounting data
class Storage(AccountData):
    def __init__(self,
                 name,
                 id,
                 typename):
        AccountData.__init__(self)
        m_name = unicodedata.normalize('NFD',
                                       re.sub("[\(\[].*?[\)\]]",
                                              "",
                                              name)).\
            encode('ascii', 'ignore')
        self.__name = m_name.decode('UTF-8')
        if id:
            self.__id = id
        else:
            self.__id = ''
        self.__state = 'in-use'
        self.__type = 'Standard'
        self.__projectId = ''
        self.__projectName = ''
        self.__typeName = typename

    def __repr__(self):
        return "<Storage>"

    # Returns String representation for a storage object
    def __str__(self):
        str = "{0} name: {1} ({2})\n" \
              "\tHours: {3:.2f}\n" \
              "\tSize: {4:.0f}GB\n" \
              "\tType: {5}\n" \
              "\tDisk GB-Hours: {6:.2f}\n" \
              "\tVolume total cost: {7:.2f}\n"
        return str.format(self.getTypeName(),
                          self.getName(),
                          self.getId(),
                          self.getHrs(),
                          self.getDisk('value'),
                          self.getType(),
                          self.getDisk('hours'),
                          self.getTotalCost())

    def setId(self, id):
        self.__id = id

    def getId(self):
        return self.__id

    def setName(self, name):
        self.__name = name

    def getName(self):
        return self.__name

    def setState(self, state):
        self.__state = state

    def getState(self):
        return self.__state

    def setType(self, type):
        self.__type = type

    def getType(self):
        return self.__type

    def setProjectId(self, id):
        self.__projectId = id

    def getProjectId(self):
        return self.__projectId

    def setProjectName(self, name):
        self.__projectName = name

    def getProjectName(self):
        return self.__projectName

    def setTypeName(self, name):
        self.__typeName = name

    def getTypeName(self):
        return self.__typeName

    def getTotalCost(self):
        try:
            self.__totalCost = self.getDisk('cost')
        except Exception as e:
            print("Error {0}".format(e))
            return 0.0
        return self.__totalCost
