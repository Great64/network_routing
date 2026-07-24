import argparse
import math
import random
import sys
import time

from algorithms import all_pairs, bellman_ford, dijkstra, format_table
from performance import run_perf
from simulator import build_network, run_topology_change, send_packet
from topology import Topology


def load_topology(args):
    if args.topology_file:
        topo = Topology.from_file(args.topology_file)
    elif args.random is not None:
        topo = Topology.random(args.random, seed=args.seed)
    else:
        print("Error: provide --topology-file or --random N", file=sys.stderr)
        sys.exit(2)
    if not topo.is_connected():
        print("Warning: loaded topology is not connected.", file=sys.stderr)
    return topo


def add_source_args(p):
    src = p.add_mutually_exclusive_group(required=False)
    src.add_argument("--topology-file", help="CSV file describing the topology")
    src.add_argument("--random", type=int, help="Generate a random topology with N routers")
    p.add_argument("--seed", type=int, default=None)


def cmd_table(args):
    topo = load_topology(args)
    fn = dijkstra if args.algo == "dijkstra" else bellman_ford
    table = fn(topo, args.router)
    print(topo.describe())
    print()
    print(format_table(args.router, table))


def cmd_forward(args):
    topo = load_topology(args)
    routers, _ = build_network(topo, args.algo)
    print(topo.describe())
    print()
    send_packet(routers, args.src, args.dst, args.pid)


def cmd_change(args):
    topo = load_topology(args)
    print(topo.describe())
    print()
    rng = random.Random(args.seed)
    run_topology_change(topo, args.algo, args.src, args.dst, rng=rng)


def cmd_perf(args):
    sizes = [int(s) for s in args.sizes.split(",")]
    run_perf(sizes, args.algo, args.out, seed=args.seed if args.seed is not None else 42)


def cmd_gui(args):
    topo = load_topology(args)
    try:
        import tkinter  # noqa: F401
    except Exception as e:
        print("Error: Tkinter is not available in this Python install.", file=sys.stderr)
        print("On NixOS, run inside a shell that provides tk, e.g.:", file=sys.stderr)
        print("  nix-shell -p 'python3.withPackages (ps: [])' tk", file=sys.stderr)
        print(f"Underlying import error: {e}", file=sys.stderr)
        sys.exit(1)
    import gui
    gui.launch(topo, algo=args.algo, seed=args.seed)


def cmd_compare(args):
    topo = load_topology(args)
    print(topo.describe())
    print()

    t0 = time.perf_counter()
    tables_d = all_pairs(topo, "dijkstra")
    t_d = (time.perf_counter() - t0) * 1000.0

    t0 = time.perf_counter()
    tables_b = all_pairs(topo, "bellman-ford")
    t_b = (time.perf_counter() - t0) * 1000.0

    equal = True
    mismatches = []
    for src in topo.labels:
        for dst in topo.labels:
            if src == dst:
                continue
            cd = tables_d[src][dst]["cost"]
            cb = tables_b[src][dst]["cost"]
            if cd != cb:
                equal = False
                mismatches.append((src, dst, cd, cb))

    print(f"Dijkstra all-pairs time:      {t_d:.3f} ms")
    print(f"Bellman-Ford all-pairs time:  {t_b:.3f} ms")
    print(f"Routing tables cost-equal:    {equal}")
    if not equal:
        for m in mismatches[:10]:
            print(f"  mismatch {m[0]}->{m[1]}: dijkstra={m[2]} bf={m[3]}")

    sample = topo.labels[0]
    print()
    print("Sample table (Dijkstra):")
    print(format_table(sample, tables_d[sample]))
    print()
    print("Sample table (Bellman-Ford):")
    print(format_table(sample, tables_b[sample]))


def build_parser():
    parser = argparse.ArgumentParser(description="CP372 Routing Simulator")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("table", help="Show routing table for a router")
    add_source_args(p)
    p.add_argument("--algo", choices=["dijkstra", "bellman-ford"], default="dijkstra")
    p.add_argument("--router", required=True)
    p.set_defaults(func=cmd_table)

    p = sub.add_parser("forward", help="Simulate packet forwarding")
    add_source_args(p)
    p.add_argument("--algo", choices=["dijkstra", "bellman-ford"], default="dijkstra")
    p.add_argument("--src", required=True)
    p.add_argument("--dst", required=True)
    p.add_argument("--pid", type=int, default=1)
    p.set_defaults(func=cmd_forward)

    p = sub.add_parser("change", help="Apply a random topology change and compare")
    add_source_args(p)
    p.add_argument("--algo", choices=["dijkstra", "bellman-ford"], default="dijkstra")
    p.add_argument("--src", required=True)
    p.add_argument("--dst", required=True)
    p.set_defaults(func=cmd_change)

    p = sub.add_parser("perf", help="Run performance experiments")
    p.add_argument("--sizes", default="10,20,50,100")
    p.add_argument("--algo", choices=["dijkstra", "bellman-ford"], default="dijkstra")
    p.add_argument("--out", default="results.csv")
    p.add_argument("--seed", type=int, default=None)
    p.set_defaults(func=cmd_perf)

    p = sub.add_parser("compare", help="Compare Dijkstra vs Bellman-Ford")
    add_source_args(p)
    p.set_defaults(func=cmd_compare)

    p = sub.add_parser("gui", help="Launch the Tkinter visualization GUI")
    add_source_args(p)
    p.add_argument("--algo", choices=["dijkstra", "bellman-ford"], default="dijkstra")
    p.set_defaults(func=cmd_gui)

    return parser


def main(argv=None):
    parser = build_parser()
    args = parser.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
