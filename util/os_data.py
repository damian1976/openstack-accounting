class AccountData(object):
    def __init__(self):
        self.hrs = 0.0
        self.ram = {
            'value': 0.0,
            'hours': 0.0,
            'cost': 0.0,
        }
        self.cpu = {
            'value': 0.0,
            'hours': 0.0,
            'cost': 0.0,
        }
        self.disk = {
            'value': 0.0,
            'hours': 0.0,
            'cost': 0.0,
        }
        self.total_cost = 0.0
        self.coeff = {
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
