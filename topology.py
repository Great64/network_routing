import csv
import math
import random


class Topology:
    def __init__(self, labels=None, matrix=None):
        self.labels = list(labels) if labels else []
        self.matrix = [row[:] for row in matrix] if matrix else []

    @property
    def n(self):
        return len(self.labels)

    def index(self, label):
        return self.labels.index(label)

    @classmethod
    def from_file(cls, path):
        with open(path, newline="") as f:
            reader = csv.reader(f)
            rows = [r for r in reader if r and any(c.strip() for c in r)]
        header = [c.strip() for c in rows[0]]
        if header[0] == "":
            labels = header[1:]
            data_rows = rows[1:]
        else:
            labels = header
            data_rows = rows[1:] if len(rows) > len(labels) else rows
        n = len(labels)
        matrix = [[math.inf] * n for _ in range(n)]
        for i, row in enumerate(data_rows):
            cells = [c.strip() for c in row]
            if len(cells) == n + 1:
                cells = cells[1:]
            for j, cell in enumerate(cells):
                if cell == "" or cell.lower() in ("inf", "infinity", "-", "x"):
                    matrix[i][j] = math.inf
                else:
                    matrix[i][j] = float(cell)
            matrix[i][i] = 0
        for i in range(n):
            for j in range(n):
                if matrix[i][j] != matrix[j][i]:
                    v = min(matrix[i][j], matrix[j][i])
                    matrix[i][j] = matrix[j][i] = v
        return cls(labels, matrix)

    @classmethod
    def random(cls, n, seed=None, min_cost=1, max_cost=20, target_degree=3):
        if n < 2:
            raise ValueError("n must be >= 2")
        rng = random.Random(seed)
        labels = [f"R{i+1}" for i in range(n)]
        matrix = [[math.inf] * n for _ in range(n)]
        for i in range(n):
            matrix[i][i] = 0
        nodes = list(range(n))
        rng.shuffle(nodes)
        for k in range(1, n):
            u = nodes[k]
            v = nodes[rng.randrange(0, k)]
            c = rng.randint(min_cost, max_cost)
            matrix[u][v] = matrix[v][u] = c
        target_edges = max(n - 1, (n * target_degree) // 2)
        current_edges = n - 1
        max_edges = n * (n - 1) // 2
        target_edges = min(target_edges, max_edges - 1) if max_edges > n - 1 else current_edges
        attempts = 0
        while current_edges < target_edges and attempts < target_edges * 20:
            u = rng.randrange(n)
            v = rng.randrange(n)
            attempts += 1
            if u == v or matrix[u][v] != math.inf:
                continue
            c = rng.randint(min_cost, max_cost)
            matrix[u][v] = matrix[v][u] = c
            current_edges += 1
        return cls(labels, matrix)

    def add_link(self, a, b, cost):
        i, j = self.index(a), self.index(b)
        self.matrix[i][j] = self.matrix[j][i] = cost

    def remove_link(self, a, b):
        i, j = self.index(a), self.index(b)
        self.matrix[i][j] = self.matrix[j][i] = math.inf

    def change_cost(self, a, b, cost):
        self.add_link(a, b, cost)

    def remove_router(self, label):
        i = self.index(label)
        self.labels.pop(i)
        self.matrix.pop(i)
        for row in self.matrix:
            row.pop(i)

    def edges(self):
        result = []
        for i in range(self.n):
            for j in range(i + 1, self.n):
                if self.matrix[i][j] != math.inf:
                    result.append((self.labels[i], self.labels[j], self.matrix[i][j]))
        return result

    def neighbors(self, label):
        i = self.index(label)
        out = []
        for j in range(self.n):
            if i != j and self.matrix[i][j] != math.inf:
                out.append((self.labels[j], self.matrix[i][j]))
        return out

    def is_connected(self):
        if self.n == 0:
            return True
        seen = {0}
        stack = [0]
        while stack:
            u = stack.pop()
            for v in range(self.n):
                if v not in seen and self.matrix[u][v] != math.inf:
                    seen.add(v)
                    stack.append(v)
        return len(seen) == self.n

    def describe(self):
        lines = [f"Topology: {self.n} routers, {len(self.edges())} links"]
        lines.append("Edges:")
        for a, b, c in self.edges():
            lines.append(f"  {a} <-> {b}  cost={c}")
        return "\n".join(lines)
