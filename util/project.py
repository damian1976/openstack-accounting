from .os_data import AccountData


# 'Project' class
# Contains all project accounting data
class Project(AccountData):
    def __init__(self, name):
        AccountData.__init__(self)
        self.id = id
        self.name = name
        self.ramh = 0.0
        self.vcpuh = 0.0
        self.diskh = {
            'standard': '0.0',
        }

    def __repr__(self):
        return self.id\
            + "," + self.name\
            + "," + str(self.ramh)\
            + "," + str(self.vcpuh)\
            + "," + str(self.diskh)\
            + "," + str(self.coeff)
