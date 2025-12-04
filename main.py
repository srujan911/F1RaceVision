import fastf1
import fastf1.events
from ui.menu import menu_screen
from ui.replay import run_replay


def main():
    print("\n=== F1 RACE VISION (2025 REPLAY MODE) ===\n")

    # Enable FastF1 cache
    fastf1.Cache.enable_cache(".fastf1-cache")

    # --- Step 1: Get available races and show menu ---
    try:
        schedule = fastf1.get_event_schedule(2025, include_testing=False)
        races_by_year = {
            2025: [
                (row['RoundNumber'], row['EventName'])
                for _, row in schedule.iterrows()
                if row['EventFormat'] != 'testing'
            ]
        }
    except Exception as e:
        print(f"[ERROR] Could not fetch race schedule from FastF1: {e}")
        return

    year, round_number, gp_name = menu_screen(races_by_year, default_year=2025)

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
