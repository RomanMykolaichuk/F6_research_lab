"""Synthetic example; standard library only."""
from itertools import product

alternatives = {"A": (0.90, 8, 4), "B": (0.84, 3, 2), "C": (0.88, 5, 3)}

def normalize(q, t, c):
    return (q, 1 - t / 10, 1 - c / 5)

def rank(weights, max_time=8, max_cost=4):
    assert len(weights) == 3 and all(w >= 0 for w in weights)
    assert abs(sum(weights) - 1) < 1e-9
    return sorted(
        ((name, sum(w*z for w,z in zip(weights, normalize(*values))))
         for name, values in alternatives.items() if values[1] <= max_time and values[2] <= max_cost),
        key=lambda item: (-item[1], item[0]))

if __name__ == "__main__":
    for a,b in product(range(11), repeat=2):
        if a+b <= 10:
            weights = (a/10, b/10, (10-a-b)/10)
            print(weights, rank(weights))
