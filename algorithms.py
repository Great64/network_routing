import heapq
import math


def _build_table(labels, dist, prev, source_idx):
    table = {}
    src_label = labels[source_idx]
    for j, dst_label in enumerate(labels):
        if j == source_idx:
            continue
        if dist[j] == math.inf:
            table[dst_label] = {"next_hop": None, "cost": math.inf, "path": []}
            continue
        path = []
        cur = j
        while cur is not None and cur != source_idx:
            path.append(cur)
            cur = prev[cur]
        path.reverse()
        next_hop = labels[path[0]] if path else None
        table[dst_label] = {
            "next_hop": next_hop,
            "cost": dist[j],
            "path": [src_label] + [labels[k] for k in path],
        }
    return table


def dijkstra(topology, source_label):
    n = topology.n
    labels = topology.labels
    matrix = topology.matrix
    s = topology.index(source_label)
    adj = [[(v, matrix[u][v]) for v in range(n)
            if v != u and matrix[u][v] != math.inf] for u in range(n)]
    dist = [math.inf] * n
    prev = [None] * n
    dist[s] = 0
    heap = [(0, s)]
    while heap:
        d, u = heapq.heappop(heap)
        if d > dist[u]:
            continue
        for v, w in adj[u]:
            nd = d + w
            if nd < dist[v]:
                dist[v] = nd
                prev[v] = u
                heapq.heappush(heap, (nd, v))
    return _build_table(labels, dist, prev, s)


def bellman_ford(topology, source_label):
    n = topology.n
    labels = topology.labels
    matrix = topology.matrix
    s = topology.index(source_label)
    dist = [math.inf] * n
    prev = [None] * n
    dist[s] = 0
    edges = []
    for i in range(n):
        for j in range(n):
            if i != j and matrix[i][j] != math.inf:
                edges.append((i, j, matrix[i][j]))
    for _ in range(n - 1):
        changed = False
        for u, v, w in edges:
            if dist[u] + w < dist[v]:
                dist[v] = dist[u] + w
                prev[v] = u
                changed = True
        if not changed:
            break
    return _build_table(labels, dist, prev, s)


def all_pairs(topology, algo="dijkstra"):
    fn = dijkstra if algo == "dijkstra" else bellman_ford
    return {label: fn(topology, label) for label in topology.labels}


def format_table(source_label, table):
    lines = [f"Routing table for {source_label}"]
    lines.append(f"{'Destination':<12}{'Next Hop':<12}{'Cost':<8}")
    lines.append("-" * 32)
    for dst in sorted(table.keys(), key=lambda s: int(s[1:]) if s[1:].isdigit() else s):
        entry = table[dst]
        cost = "inf" if entry["cost"] == math.inf else str(entry["cost"])
        nh = entry["next_hop"] if entry["next_hop"] else "-"
        lines.append(f"{dst:<12}{nh:<12}{cost:<8}")
    return "\n".join(lines)
