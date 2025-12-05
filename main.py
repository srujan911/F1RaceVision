import fastf1
import fastf1.events
from ui.menu import menu_screen
from ui.replay import run_replay


def main():
    print("\n=== F1 RACE VISION (2025 REPLAY MODE) ===\n")

    # Enable FastF1 cache
    # Use a consistent cache path across the application
    fastf1.Cache.enable_cache("f1_cache")

    # --- Step 1: Get available races and show menu ---
    races_by_year = {}
    # Start with the desired year, but be ready to fall back
    year_to_try = 2025
    
    try:
        print(f"[INFO] Fetching event schedule for {year_to_try}...")
        schedule = fastf1.get_event_schedule(year_to_try, include_testing=False)
        races_by_year[year_to_try] = [
            (row['RoundNumber'], row['EventName'])
            for _, row in schedule.iterrows()
            if row['EventFormat'] != 'testing'
        ]
    except Exception as e:
        print(f"[WARNING] Could not fetch {year_to_try} schedule from FastF1: {e}")
        print("[INFO] Attempting to fall back to previous year's schedule...")
        year_to_try = 2024 # Fallback year
        try:
            print(f"[INFO] Fetching event schedule for {year_to_try}...")
            schedule = fastf1.get_event_schedule(year_to_try, include_testing=False)
            races_by_year[year_to_try] = [
                (row['RoundNumber'], row['EventName'])
                for _, row in schedule.iterrows()
                if row['EventFormat'] != 'testing'
            ]
        except Exception as e2:
            print(f"[ERROR] Failed to fetch fallback schedule for {year_to_try}: {e2}")
            print("[ERROR] Please check your internet connection or try again later. Exiting.")
            return

    year, round_number, gp_name = menu_screen(races_by_year, default_year=year_to_try)

    if not (year and round_number):
        print("No race selected. Exiting.")
        return

    # --- Step 2: Get circuit name ---
    try:
        event = fastf1.get_event(year, round_number)
        circuit_name = event['Location']
    except Exception as e:
        print(f"[WARNING] Could not fetch circuit name: {e}")
        circuit_name = ""

    # --- Step 3: Start replay UI ---
    run_replay(year, round_number, gp_name, circuit_name)

    print("\nReplay ended successfully. Thank you for using F1 RaceVision!\n")


if __name__ == "__main__":
    main()
