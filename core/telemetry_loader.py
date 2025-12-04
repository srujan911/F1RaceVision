from dataclasses import dataclass
from typing import Dict, List, Tuple

import fastf1
import numpy as np
import pandas as pd


@dataclass
class DriverTrace:
    driver_code: str
    positions: List[Tuple[float, float]]
    times: List[float]
    speeds: List[float]
    gears: List[int]
    drs: List[int]
    tyres: List[str]
    distances: List[float]
    sectors: List[tuple]  # (S1, S2, S3)
    lap_numbers: List[int]
    pit_status: List[str]   # "PIT", "OUT", or ""

  # <-- NEW


def load_race_telemetry(year: int, round_number: int) -> Dict[str, DriverTrace]:
    fastf1.Cache.enable_cache(".fastf1-cache")

    session = fastf1.get_session(year, round_number, 'R')
    session.load()

    telemetry: Dict[str, DriverTrace] = {}

    for drv in session.drivers:
        laps = session.laps.pick_drivers(drv)
        if laps.empty:
            continue

        # Use get_telemetry() to get all data, including distance
        telemetry_data = laps.get_telemetry()

        if telemetry_data.empty:
            continue

        session_times = telemetry_data["SessionTime"]
        t0 = session_times.iloc[0]
        times_sec = (session_times - t0).dt.total_seconds().to_numpy()

        speeds = telemetry_data["Speed"].fillna(0).to_numpy()
        distances = telemetry_data["Distance"].fillna(0).to_numpy()
        gears = telemetry_data["nGear"].fillna(0).astype(int).to_numpy() if "nGear" in telemetry_data else np.zeros(
            len(session_times), dtype=int)
        drs = telemetry_data["DRS"].fillna(0).astype(int).to_numpy() if "DRS" in telemetry_data else np.zeros(len(session_times),
                                                                                                             dtype=int)

      
        # --------------------------------------
        # TYRE COMPOUND PER TELEMETRY SAMPLE
        # --------------------------------------

        # Extract lap start times & compounds
        lap_numbers = laps["LapNumber"].to_list()
        lap_start_times = laps["LapStartTime"].to_list()
        lap_compounds = laps["Compound"].to_list()

        tyre_series = []

        for i in range(len(telemetry_data)):
            t_sample = telemetry_data["SessionTime"].iloc[i]

            # Find the lap whose LapStartTime is <= timestamp and is the latest
            lap_index = None
            for j in range(len(lap_start_times)):
                if lap_start_times[j] <= t_sample:
                    lap_index = j
                else:
                    break

            if lap_index is None:
                tyre_series.append("UNK")
            else:
                tyre_series.append(lap_compounds[lap_index])

        # --------------------------------------
        # LAP NUMBER + SECTOR TIMES PER SAMPLE
        # --------------------------------------

        lap_numbers_list = []
        sectors_list = []

        for i in range(len(telemetry_data)):
            t_sample = telemetry_data["SessionTime"].iloc[i]

            # Find lap for this timestamp
            lap_match = laps[(laps["LapStartTime"] <= t_sample)]
            if lap_match.empty:
                lap_numbers_list.append(0)
                sectors_list.append((0, 0, 0))
                continue

            lap_row = lap_match.iloc[-1]  # latest lap <= timestamp
            lap_numbers_list.append(int(lap_row["LapNumber"]))

            # Extract sector times (FastF1 format)
            s1 = lap_row.get("Sector1Time", pd.Timedelta(0))
            s2 = lap_row.get("Sector2Time", pd.Timedelta(0))
            s3 = lap_row.get("Sector3Time", pd.Timedelta(0))

            # Convert timedeltas to seconds (float)
            s1 = s1.total_seconds() if hasattr(s1, "total_seconds") else 0
            s2 = s2.total_seconds() if hasattr(s2, "total_seconds") else 0
            s3 = s3.total_seconds() if hasattr(s3, "total_seconds") else 0

            sectors_list.append((s1, s2, s3))
        # -------------------------------------------------
        # PIT STATUS PER SAMPLE
        # -------------------------------------------------

        pit_status_list = []
        lap_pit_flags = laps["PitOutTime"].notna() | laps["PitInTime"].notna()

        for i in range(len(telemetry_data)):
            t_sample = telemetry_data["SessionTime"].iloc[i]

            # Find lap for timestamp
            lap_match = laps[laps["LapStartTime"] <= t_sample]
            if lap_match.empty:
                pit_status_list.append("")
                continue

            lap_row = lap_match.iloc[-1]

            # OUT (driver retires)
            if i > 10:
                # fixed condition: if the last 20 positions didn't move much
                recent = telemetry_data.iloc[max(0, i - 20):i]["X"]
                if recent.max() - recent.min() < 1:  # car stationary
                    pit_status_list.append("OUT")
                    continue

            # PIT (lap has pit entry/exit)
            lap_num = int(lap_row["LapNumber"])
            if lap_pit_flags.iloc[lap_num - 1]:
                pit_status_list.append("PIT")
            else:
                pit_status_list.append("")




        xs = telemetry_data["X"].to_numpy()
        ys = telemetry_data["Y"].to_numpy()

        code = session.get_driver(drv)["Abbreviation"]

        telemetry[code] = DriverTrace(
            driver_code=code,
            positions=list(zip(xs, ys)),
            times=list(times_sec),
            speeds=list(speeds),
            gears=list(gears),
            drs=list(drs),
            tyres=tyre_series,
            distances=list(distances),
            sectors=sectors_list,
            lap_numbers=lap_numbers_list,
            pit_status=pit_status_list

        )

    return telemetry
