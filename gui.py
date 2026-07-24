import math
import random

from algorithms import all_pairs, format_table
from packet import Packet
from simulator import apply_random_change, build_network
from topology import Topology


NODE_RADIUS = 22
EDGE_COLOR = "#5a6c7d"
EDGE_HIGHLIGHT = "#1f9e46"
EDGE_ADDED = "#0b7fd6"
EDGE_CHANGED = "#d18a1a"
EDGE_REMOVED = "#b03030"
NODE_COLOR = "#eef2f6"
NODE_OUTLINE = "#233242"
NODE_FAILED = "#b03030"
PACKET_COLOR = "#d94141"
CANVAS_BG = "#ffffff"


def spring_layout(topology, width, height, seed=0, iterations=200):
    n = topology.n
    if n == 0:
        return {}
    rng = random.Random(seed)
    pos = {}
    for i, label in enumerate(topology.labels):
        angle = 2 * math.pi * i / n
        r = min(width, height) * 0.35
        pos[label] = [width / 2 + r * math.cos(angle) + rng.uniform(-5, 5),
                      height / 2 + r * math.sin(angle) + rng.uniform(-5, 5)]
    if n == 1:
        return pos
    area = width * height
    k = math.sqrt(area / n) * 0.6
    t = min(width, height) / 8.0
    cooling = t / iterations
    labels = topology.labels
    for _ in range(iterations):
        disp = {lbl: [0.0, 0.0] for lbl in labels}
        for i in range(n):
            for j in range(n):
                if i == j:
                    continue
                a, b = labels[i], labels[j]
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 0.01
                f = (k * k) / d
                disp[a][0] += (dx / d) * f
                disp[a][1] += (dy / d) * f
        for i in range(n):
            for j in range(i + 1, n):
                if topology.matrix[i][j] == math.inf:
                    continue
                a, b = labels[i], labels[j]
                dx = pos[a][0] - pos[b][0]
                dy = pos[a][1] - pos[b][1]
                d = math.hypot(dx, dy) or 0.01
                f = (d * d) / k
                disp[a][0] -= (dx / d) * f
                disp[a][1] -= (dy / d) * f
                disp[b][0] += (dx / d) * f
                disp[b][1] += (dy / d) * f
        for lbl in labels:
            dx, dy = disp[lbl]
            d = math.hypot(dx, dy) or 0.01
            step = min(d, t)
            pos[lbl][0] += (dx / d) * step
            pos[lbl][1] += (dy / d) * step
            pos[lbl][0] = max(NODE_RADIUS + 10, min(width - NODE_RADIUS - 10, pos[lbl][0]))
            pos[lbl][1] = max(NODE_RADIUS + 10, min(height - NODE_RADIUS - 10, pos[lbl][1]))
        t = max(cooling, t - cooling)
    return {lbl: (pos[lbl][0], pos[lbl][1]) for lbl in labels}


class RoutingGUI:
    def __init__(self, topology, algo="dijkstra", seed=None):
        import tkinter as tk
        from tkinter import ttk, scrolledtext
        self.tk = tk
        self.ttk = ttk

        self.topology = topology
        self.algo = algo
        self.rng = random.Random(seed)
        self.failed = set()
        self.positions = {}
        self.node_items = {}
        self.node_text_items = {}
        self.edge_items = {}
        self.edge_label_items = {}
        self.packet_item = None
        self.animating = False

        self.root = tk.Tk()
        self.root.title("CP372 Routing Simulator - GUI")
        self.root.geometry("1200x780")
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.canvas_width = 800
        self.canvas_height = 720

        main = ttk.Frame(self.root, padding=6)
        main.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(main, width=self.canvas_width, height=self.canvas_height,
                                bg=CANVAS_BG, highlightthickness=1, highlightbackground="#888")
        self.canvas.pack(side="left", fill="both", expand=True)

        panel = ttk.Frame(main, padding=6, width=360)
        panel.pack(side="right", fill="y")

        ttk.Label(panel, text="Algorithm").pack(anchor="w")
        self.algo_var = tk.StringVar(value=self.algo)
        for name, val in (("Dijkstra", "dijkstra"), ("Bellman-Ford", "bellman-ford")):
            ttk.Radiobutton(panel, text=name, variable=self.algo_var,
                            value=val, command=self._on_algo_change).pack(anchor="w")

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=6)

        ttk.Label(panel, text="Source").pack(anchor="w")
        self.src_var = tk.StringVar()
        self.src_combo = ttk.Combobox(panel, textvariable=self.src_var, state="readonly")
        self.src_combo.pack(fill="x")

        ttk.Label(panel, text="Destination").pack(anchor="w")
        self.dst_var = tk.StringVar()
        self.dst_combo = ttk.Combobox(panel, textvariable=self.dst_var, state="readonly")
        self.dst_combo.pack(fill="x")

        ttk.Button(panel, text="Send Packet", command=self._on_send).pack(fill="x", pady=4)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=6)

        ttk.Label(panel, text="Routing table for").pack(anchor="w")
        self.rt_var = tk.StringVar()
        self.rt_combo = ttk.Combobox(panel, textvariable=self.rt_var, state="readonly")
        self.rt_combo.pack(fill="x")
        ttk.Button(panel, text="Show Routing Table",
                   command=self._on_show_table).pack(fill="x", pady=4)

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=6)

        ttk.Button(panel, text="Random Topology Change",
                   command=self._on_random_change).pack(fill="x", pady=4)

        ttk.Label(panel, text="Animation speed (ms/hop)").pack(anchor="w")
        self.speed_var = tk.IntVar(value=700)
        ttk.Scale(panel, from_=100, to=2000, orient="horizontal",
                  variable=self.speed_var).pack(fill="x")

        ttk.Separator(panel, orient="horizontal").pack(fill="x", pady=6)

        ttk.Label(panel, text="Hop / Cost").pack(anchor="w")
        self.readout_var = tk.StringVar(value="Hop: 0   Cost: 0")
        ttk.Label(panel, textvariable=self.readout_var,
                  font=("TkDefaultFont", 10, "bold")).pack(anchor="w")

        ttk.Label(panel, text="Log").pack(anchor="w", pady=(6, 0))
        self.log = scrolledtext.ScrolledText(panel, width=42, height=18,
                                             font=("TkFixedFont", 9))
        self.log.pack(fill="both", expand=True)

        self._recompute()
        self.root.after(60, self._initial_layout)

    def _initial_layout(self):
        self.canvas_width = max(400, self.canvas.winfo_width())
        self.canvas_height = max(400, self.canvas.winfo_height())
        self.positions = spring_layout(self.topology, self.canvas_width,
                                       self.canvas_height, seed=42)
        self._redraw_all()

    def _recompute(self):
        self.algo = self.algo_var.get()
        self.routers, self.tables = build_network(self.topology, self.algo)
        labels = list(self.topology.labels)
        self.src_combo["values"] = labels
        self.dst_combo["values"] = labels
        self.rt_combo["values"] = labels
        if labels:
            if self.src_var.get() not in labels:
                self.src_var.set(labels[0])
            if self.dst_var.get() not in labels:
                self.dst_var.set(labels[-1])
            if self.rt_var.get() not in labels:
                self.rt_var.set(labels[0])

    def _log(self, msg):
        self.log.insert("end", msg + "\n")
        self.log.see("end")

    def _redraw_all(self):
        self.canvas.delete("all")
        self.edge_items.clear()
        self.edge_label_items.clear()
        self.node_items.clear()
        self.node_text_items.clear()
        n = self.topology.n
        for i in range(n):
            for j in range(i + 1, n):
                if self.topology.matrix[i][j] == math.inf:
                    continue
                a = self.topology.labels[i]
                b = self.topology.labels[j]
                self._draw_edge(a, b, self.topology.matrix[i][j], EDGE_COLOR)
        for lbl in self.topology.labels:
            self._draw_node(lbl)

    def _draw_edge(self, a, b, cost, color, dash=None, width=2):
        if a not in self.positions or b not in self.positions:
            return
        x1, y1 = self.positions[a]
        x2, y2 = self.positions[b]
        line = self.canvas.create_line(x1, y1, x2, y2, fill=color,
                                       width=width, dash=dash)
        mx, my = (x1 + x2) / 2, (y1 + y2) / 2
        bg = self.canvas.create_rectangle(mx - 12, my - 8, mx + 12, my + 8,
                                          fill=CANVAS_BG, outline="")
        text = self.canvas.create_text(mx, my, text=str(int(cost) if cost == int(cost) else cost),
                                       font=("TkDefaultFont", 8), fill="#333")
        key = tuple(sorted((a, b)))
        self.edge_items[key] = line
        self.edge_label_items[key] = (bg, text)

    def _draw_node(self, label):
        if label not in self.positions:
            return
        x, y = self.positions[label]
        fill = NODE_FAILED if label in self.failed else NODE_COLOR
        oval = self.canvas.create_oval(x - NODE_RADIUS, y - NODE_RADIUS,
                                       x + NODE_RADIUS, y + NODE_RADIUS,
                                       fill=fill, outline=NODE_OUTLINE, width=2)
        text = self.canvas.create_text(x, y, text=label,
                                       font=("TkDefaultFont", 10, "bold"))
        self.node_items[label] = oval
        self.node_text_items[label] = text

    def _on_algo_change(self):
        self._recompute()
        self._log(f"Algorithm switched to {self.algo}; routing tables recomputed.")

    def _on_show_table(self):
        r = self.rt_var.get()
        if not r or r not in self.tables:
            return
        self._log("")
        self._log(format_table(r, self.tables[r]))

    def _on_send(self):
        if self.animating:
            return
        src = self.src_var.get()
        dst = self.dst_var.get()
        if not src or not dst or src == dst:
            self._log("Select distinct src and dst.")
            return
        entry = self.tables.get(src, {}).get(dst)
        if not entry or not entry["path"] or entry["cost"] == math.inf:
            self._log(f"No route from {src} to {dst}.")
            return
        path = entry["path"]
        self._log("")
        self._log(f"Sending packet {src} -> {dst} via {' -> '.join(path)}")
        self._animate_packet(path)

    def _animate_packet(self, path):
        self.animating = True
        self._reset_edge_highlights()
        packet = Packet(1, path[0], path[-1])
        packet.path.append(path[0])
        self.readout_var.set(f"Hop: 0   Cost: 0")
        x0, y0 = self.positions[path[0]]
        self.packet_item = self.canvas.create_oval(x0 - 7, y0 - 7, x0 + 7, y0 + 7,
                                                   fill=PACKET_COLOR, outline="")
        self._hop_index = 0
        self._packet_state = packet
        self._path = path
        self._step_hop()

    def _step_hop(self):
        if self._hop_index >= len(self._path) - 1:
            self._finish_animation()
            return
        a = self._path[self._hop_index]
        b = self._path[self._hop_index + 1]
        i = self.topology.index(a)
        j = self.topology.index(b)
        cost = self.topology.matrix[i][j]
        self._current_hop_cost = cost
        x1, y1 = self.positions[a]
        x2, y2 = self.positions[b]
        steps = 20
        delay = max(20, self.speed_var.get() // steps)
        self._animate_segment(x1, y1, x2, y2, steps, 0, delay, a, b, cost)

    def _animate_segment(self, x1, y1, x2, y2, steps, i, delay, a, b, cost):
        if not self.packet_item:
            return
        t = i / steps
        x = x1 + (x2 - x1) * t
        y = y1 + (y2 - y1) * t
        self.canvas.coords(self.packet_item, x - 7, y - 7, x + 7, y + 7)
        if i >= steps:
            key = tuple(sorted((a, b)))
            if key in self.edge_items:
                self.canvas.itemconfig(self.edge_items[key], fill=EDGE_HIGHLIGHT, width=3)
            self._packet_state.path.append(b) if self._packet_state.path[-1] != b else None
            self._packet_state.hop_count += 1
            self._packet_state.total_cost += cost
            self.readout_var.set(
                f"Hop: {self._packet_state.hop_count}   Cost: {self._packet_state.total_cost}"
            )
            self._log(f"  hop {self._packet_state.hop_count}: {a} -> {b} (cost {cost})")
            self._hop_index += 1
            self.root.after(delay, self._step_hop)
            return
        self.root.after(delay, lambda: self._animate_segment(
            x1, y1, x2, y2, steps, i + 1, delay, a, b, cost))

    def _finish_animation(self):
        if self.packet_item:
            self.canvas.delete(self.packet_item)
            self.packet_item = None
        p = self._packet_state
        arrow = " -> "
        self._log(f"Forwarding Path for Packet.{p.id}: {arrow.join(p.path)}")
        self._log(f"Hop Count: {p.hop_count}")
        self._log(f"Total Cost: {p.total_cost}")
        self.animating = False

    def _reset_edge_highlights(self):
        for key, item in self.edge_items.items():
            self.canvas.itemconfig(item, fill=EDGE_COLOR, width=2, dash="")

    def _on_random_change(self):
        if self.animating:
            return
        src = self.src_var.get()
        dst = self.dst_var.get()
        before_entry = self.tables.get(src, {}).get(dst) if src and dst else None
        before_path = before_entry["path"] if before_entry else []
        before_cost = before_entry["cost"] if before_entry else math.inf

        pre_edges = {tuple(sorted((a, b))): c for a, b, c in self.topology.edges()}
        pre_labels = set(self.topology.labels)

        kind, info = apply_random_change(self.topology, self.rng)
        self._log("")
        self._log(f"Topology change: {kind} {info if info else ''}")

        if kind == "router_failure" and info:
            victim = info[0]
            self.failed.add(victim)

        self._recompute()
        self._flash_change(kind, info, pre_edges, pre_labels)

        if src in self.topology.labels and dst in self.topology.labels and src != dst:
            after_entry = self.tables.get(src, {}).get(dst)
            after_path = after_entry["path"] if after_entry else []
            after_cost = after_entry["cost"] if after_entry else math.inf
            arrow = " -> "
            self._log(f"Path comparison for {src} -> {dst}:")
            self._log(f"  Before: {arrow.join(before_path) if before_path else '(no path)'} cost={before_cost}")
            self._log(f"  After : {arrow.join(after_path) if after_path else '(no path)'} cost={after_cost}")
        else:
            self._log(f"Note: {src} or {dst} no longer selectable.")

    def _flash_change(self, kind, info, pre_edges, pre_labels):
        self._redraw_all()
        if kind == "add_link" and info:
            a, b, _ = info
            key = tuple(sorted((a, b)))
            if key in self.edge_items:
                self.canvas.itemconfig(self.edge_items[key], fill=EDGE_ADDED, width=4)
                self.root.after(1200, lambda k=key: self._normalize_edge(k))
        elif kind == "cost_change" and info:
            a, b, _, _ = info
            key = tuple(sorted((a, b)))
            if key in self.edge_items:
                self.canvas.itemconfig(self.edge_items[key], fill=EDGE_CHANGED, width=4)
                self.root.after(1200, lambda k=key: self._normalize_edge(k))
        elif kind == "link_failure" and info:
            a, b, c = info
            if a in self.positions and b in self.positions:
                x1, y1 = self.positions[a]
                x2, y2 = self.positions[b]
                ghost = self.canvas.create_line(x1, y1, x2, y2, fill=EDGE_REMOVED,
                                                width=2, dash=(4, 3))
                self.root.after(1000, lambda g=ghost: self.canvas.delete(g))

    def _normalize_edge(self, key):
        if key in self.edge_items:
            self.canvas.itemconfig(self.edge_items[key], fill=EDGE_COLOR, width=2)

    def _on_close(self):
        self.animating = False
        try:
            self.root.destroy()
        except Exception:
            pass

    def run(self):
        self.root.mainloop()


def launch(topology, algo="dijkstra", seed=None):
    gui = RoutingGUI(topology, algo=algo, seed=seed)
    gui.run()
