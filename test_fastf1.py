import fastf1

fastf1.Cache.enable_cache("f1_cache")

# Load the session you used in your replay (change round if needed)
session = fastf1.get_session(2025, 1, "R")
session.load(laps=True, telemetry=True)

# pick any driver that exists
drivers = session.drivers
print("Drivers:", drivers)

drv = drivers[0]   # pick first driver
print("Testing driver:", drv)

lap = session.laps.pick_drivers([drv]).iloc[0]

# --- PRINT CAR DATA COLUMNS ---
car = lap.get_car_data()
print("\n=== car_data columns ===")
print(list(car.columns))

# --- PRINT POSITION DATA COLUMNS ---
pos = lap.get_pos_data()
print("\n=== pos_data columns ===")
print(list(pos.columns))

# Show first few rows too
print("\ncar_data head:\n", car.head())
print("\npos_data head:\n", pos.head())
