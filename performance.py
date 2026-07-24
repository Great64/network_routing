import csv
import math
import random
import time

from algorithms import all_pairs
from simulator import apply_random_change
from topology import Topology


def _avg(values):
    values = [v for v in values if v != math.inf]
    return sum(values) / len(values) if values else 0.0


def measure(size, algo, seed):
    topo = Topology.random(size, seed=seed)
    t0 = time.perf_counter()
    tables = all_pairs(topo, algo)
    elapsed_ms = (time.perf_counter() - t0) * 1000.0

    hops = []
    costs = []
    entry_count = 0
    for src, table in tables.items():
        for dst, entry in table.items():
            entry_count += 1
            if entry["cost"] == math.inf:
                continue
            hops.append(max(0, len(entry["path"]) - 1))
            costs.append(entry["cost"])

    before_avg_cost = _avg(costs)

    rng = random.Random(seed + 1000)
    kind, info = apply_random_change(topo, rng)
    tables_after = all_pairs(topo, algo)
    after_costs = []
    for src, table in tables_after.items():
        for dst, entry in table.items():
            if entry["cost"] != math.inf:
                after_costs.append(entry["cost"])
    after_avg_cost = _avg(after_costs)

    return {
        "size": size,
        "avg_path_hops": round(_avg(hops), 3),
        "avg_routing_cost": round(before_avg_cost, 3),
        "routing_entries": entry_count,
        "compute_time_ms": round(elapsed_ms, 3),
        "change_kind": kind,
        "avg_cost_after_change": round(after_avg_cost, 3),
        "avg_cost_delta": round(after_avg_cost - before_avg_cost, 3),
    }


def run_perf(sizes, algo, out_csv, seed=42):
    results = []
    for size in sizes:
        print(f"Measuring size={size} algo={algo}...")
        results.append(measure(size, algo, seed))

    headers = list(results[0].keys())
    col_w = [max(len(h), max(len(str(r[h])) for r in results)) for h in headers]
    line = "  ".join(h.ljust(col_w[i]) for i, h in enumerate(headers))
    print()
    print(line)
    print("-" * len(line))
    for r in results:
        print("  ".join(str(r[h]).ljust(col_w[i]) for i, h in enumerate(headers)))

    with open(out_csv, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for r in results:
            writer.writerow(r)
    print(f"\nWrote CSV: {out_csv}")

    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
    except ImportError:
        print("matplotlib not installed; skipping plots.")
        return results

    metrics = [
        ("avg_path_hops", "Average path length (hops)"),
        ("avg_routing_cost", "Average routing cost"),
        ("routing_entries", "Routing table entries"),
        ("compute_time_ms", "Routing computation time (ms)"),
        ("avg_cost_delta", "Avg cost delta after change"),
    ]
    xs = [r["size"] for r in results]
    base = out_csv.rsplit(".", 1)[0]
    for key, title in metrics:
        ys = [r[key] for r in results]
        fig, ax = plt.subplots()
        ax.plot(xs, ys, marker="o")
        ax.set_xlabel("Number of routers")
        ax.set_ylabel(title)
        ax.set_title(f"{title} vs network size ({algo})")
        ax.grid(True)
        out = f"{base}_{key}.png"
        fig.savefig(out, dpi=100, bbox_inches="tight")
        plt.close(fig)
        print(f"Wrote plot: {out}")

    return results
