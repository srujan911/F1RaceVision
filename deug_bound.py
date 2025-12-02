from core.telemetry_loader import load_race_telemetry

year = 2023
round_number = 1

traces = load_race_telemetry(year, round_number)

xs = []
ys = []

for tr in traces.values():
    for x, y in tr.positions:
        xs.append(x)
        ys.append(y)

print("min_x =", min(xs))
print("max_x =", max(xs))
print("min_y =", min(ys))
print("max_y =", max(ys))
