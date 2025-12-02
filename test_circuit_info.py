import fastf1
fastf1.Cache.enable_cache(".fastf1-cache")

session = fastf1.get_session(2023, 1, 'R')
session.load()

laps = session.laps
print("COLUMNS:")
print(laps.columns.tolist())

print("\nFIRST 3 ROWS:")
print(laps.head(3))
