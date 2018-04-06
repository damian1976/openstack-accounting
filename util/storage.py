from .os_data import AccountData


# 'Server' class
# Contains all Storage (Volume/Image)
# accounting data
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

    # Returns String representation for a storage object
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
