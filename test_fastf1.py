import fastf1

def main():
    # Enable caching to .fastf1-cache folder
    fastf1.Cache.enable_cache(".fastf1-cache")

    # Example: 2023 Round 1, Race session
    session = fastf1.get_session(2023, 1, 'R')  # 'R' = Race
    session.load()  # Downloads + parses data (first time can take a while)

    print("Event:", session.event['EventName'], session.event['EventDate'])
    print("Session:", session.name)
    print("Drivers in session:", session.drivers)

if __name__ == "__main__":
    main()
