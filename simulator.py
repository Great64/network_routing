import math
import random
import time

from algorithms import all_pairs, format_table
from packet import Packet
from router import Router


def build_network(topology, algo="dijkstra"):
    tables = all_pairs(topology, algo)
    routers = {label: Router(label) for label in topology.labels}
    for label, router in routers.items():
        router.set_table(tables[label])
        router.network = routers
        router._topology = topology
    return routers, tables


def send_packet(routers, src, dst, pid):
    packet = Packet(pid, src, dst)
    routers[src].originate(packet)
    return packet


def apply_random_change(topology, rng=None):
    rng = rng or random.Random()
    options = []
    if topology.edges():
        options.append("link_failure")
        options.append("cost_change")
    if len(topology.edges()) < topology.n * (topology.n - 1) // 2:
        options.append("add_link")
    if topology.n > 3:
        options.append("router_failure")
    if not options:
        return "no_change", None
    choice = rng.choice(options)
    if choice == "link_failure":
        for _ in range(50):
            a, b, c = rng.choice(topology.edges())
            topology.remove_link(a, b)
            if topology.is_connected():
                return "link_failure", (a, b, c)
            topology.add_link(a, b, c)
        return "no_change", None
    if choice == "cost_change":
        a, b, c = rng.choice(topology.edges())
        new_cost = rng.randint(1, 20)
        topology.change_cost(a, b, new_cost)
        return "cost_change", (a, b, c, new_cost)
    if choice == "add_link":
        n = topology.n
        for _ in range(100):
            i = rng.randrange(n)
            j = rng.randrange(n)
            if i == j or topology.matrix[i][j] != math.inf:
                continue
            a, b = topology.labels[i], topology.labels[j]
            cost = rng.randint(1, 20)
            topology.add_link(a, b, cost)
            return "add_link", (a, b, cost)
        return "no_change", None
    if choice == "router_failure":
        for _ in range(50):
            victim = rng.choice(topology.labels)
            saved_labels = list(topology.labels)
            saved_matrix = [row[:] for row in topology.matrix]
            topology.remove_router(victim)
            if topology.is_connected():
                return "router_failure", (victim,)
            topology.labels = saved_labels
            topology.matrix = saved_matrix
        return "no_change", None
    return "no_change", None


def run_topology_change(topology, algo, src, dst, rng=None, delay_range=(0.5, 2.0)):
    rng = rng or random.Random()
    routers_before, tables_before = build_network(topology, algo)
    before_entry = tables_before.get(src, {}).get(dst)
    if not before_entry:
        print(f"No route info for {src} -> {dst} before change (source missing).")
        before_path, before_cost = [], math.inf
    else:
        before_path = before_entry["path"]
        before_cost = before_entry["cost"]

    wait = rng.uniform(*delay_range)
    print(f"Waiting {wait:.2f}s before topology change...")
    time.sleep(wait)

    kind, info = apply_random_change(topology, rng)
    print(f"Topology change: {kind} {info if info else ''}")

    routers_after, tables_after = build_network(topology, algo)

    if src not in topology.labels or dst not in topology.labels:
        print(f"Note: {src} or {dst} no longer exists. Showing table for a surviving router.")
        surviving = topology.labels[0]
        print(format_table(surviving, tables_after[surviving]))
        return

    print(format_table(src, tables_after[src]))

    after_entry = tables_after[src].get(dst)
    after_path = after_entry["path"] if after_entry else []
    after_cost = after_entry["cost"] if after_entry else math.inf

    arrow = " → "
    print()
    print(f"Path comparison for {src} -> {dst}:")
    print(f"  Before: {arrow.join(before_path) if before_path else '(no path)'}  cost={before_cost}")
    print(f"  After : {arrow.join(after_path) if after_path else '(no path)'}  cost={after_cost}")
