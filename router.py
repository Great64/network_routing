import math


class Router:
    def __init__(self, label):
        self.label = label
        self.routing_table = {}
        self.network = None
        self._topology = None

    def set_table(self, table):
        self.routing_table = table

    def originate(self, packet):
        packet.path.append(self.label)
        if self.label == packet.destination:
            self._deliver(packet)
            return
        self._forward(packet)

    def receive(self, packet, incoming_cost):
        packet.path.append(self.label)
        packet.hop_count += 1
        packet.total_cost += incoming_cost
        if self.label == packet.destination:
            self._deliver(packet)
            return
        self._forward(packet)

    def _forward(self, packet):
        entry = self.routing_table.get(packet.destination)
        if not entry or entry["next_hop"] is None or entry["cost"] == math.inf:
            print(f"Packet.{packet.id} dropped at {self.label}: no route to {packet.destination}")
            return
        next_hop_label = entry["next_hop"]
        next_router = self.network[next_hop_label]
        link_cost = self._link_cost_to(next_hop_label)
        next_router.receive(packet, link_cost)

    def _link_cost_to(self, other_label):
        topo = self._topology
        i = topo.index(self.label)
        j = topo.index(other_label)
        return topo.matrix[i][j]

    def _deliver(self, packet):
        arrow = " → "
        print(f"Forwarding Path for Packet.{packet.id}: {arrow.join(packet.path)}")
        print(f"Hop Count: {packet.hop_count}")
        print(f"Total Cost: {packet.total_cost}")
