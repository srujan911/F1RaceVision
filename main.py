import os
import xml.etree.ElementTree as ET

from ui.menu import menu_screen
from ui.replay import run_replay


TRACKS_FOLDER = "assets/tracks"


def load_race_metadata():
    """Scan assets/tracks/ and build races_by_year dictionary."""
    races_by_year = {}

    for filename in os.listdir(TRACKS_FOLDER):
        if not filename.endswith(".svg"):
            continue

        path = os.path.join(TRACKS_FOLDER, filename)

        try:
            tree = ET.parse(path)
            root = tree.getroot()

            gp_name = root.findtext(".//gp_name")
            circuit_name = root.findtext(".//circuit_name")
            year = root.findtext(".//year")
            round_number = root.findtext(".//round")

            if not (gp_name and circuit_name and year and round_number):
                continue

            year = int(year)
            round_number = int(round_number)

            if year not in races_by_year:
                races_by_year[year] = []

            races_by_year[year].append(
                (round_number, gp_name, circuit_name, filename)
            )

        except Exception as e:
            print(f"Error reading {filename}: {e}")

    # sort races by round
    for year in races_by_year:
        races_by_year[year].sort(key=lambda x: x[0])

    return races_by_year


if __name__ == "__main__":
    print("Loading race metadata...")
    races_by_year = load_race_metadata()

    if not races_by_year:
        print("No SVG track metadata found in assets/tracks/")
        exit()

    # menu now requires races_by_year
    year, round_number, gp_name, circuit_name, svg_filename = menu_screen(races_by_year)

    if year and round_number:
        run_replay(
            year=year,
            round_number=round_number,
            gp_name=gp_name,
            circuit_name=circuit_name,
            svg_file=svg_filename
        )
