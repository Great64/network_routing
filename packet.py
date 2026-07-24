class Packet:
    def __init__(self, id, source, destination):
        self.id = id
        self.source = source
        self.destination = destination
        self.path = []
        self.hop_count = 0
        self.total_cost = 0
