import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / ".agents" / "skills" / "google-flights-browser" / "scripts"


def invoke(script, *args):
    environment = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    return subprocess.run(
        [sys.executable, str(SCRIPTS / script), *args],
        capture_output=True, text=True, env=environment, check=False,
    )


def route(flight_id, origin, destination, departure, arrival):
    return dict(id=flight_id, origin=origin, destination=destination,
                departure=departure, arrival=arrival)


class FlightToolsTest(unittest.TestCase):
    def test_browser_grid_covers_all_requested_origin_date_pairs(self):
        result = invoke(
            "plan_searches.py", "--origins", "BER", "HAM", "BER",
            "--destinations", "LHR", "--depart-dates", "2027-01-12", "2027-01-14",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        plan = json.loads(result.stdout)
        self.assertEqual(plan["scenario_count"], 4)
        self.assertEqual(
            {(row["origin"], row["departure_date"]) for row in plan["scenarios"]},
            {(origin, date) for origin in ("BER", "HAM") for date in ("2027-01-12", "2027-01-14")},
        )

    def test_return_window_intersects_stay_length(self):
        result = invoke(
            "plan_searches.py", "--origins", "BER", "--destinations", "BER", "LHR",
            "--depart-from", "2027-02-01", "--depart-to", "2027-02-02",
            "--nights", "4", "6", "--return-from", "2027-02-06", "--return-to", "2027-02-07",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)["scenarios"]
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["destination"] for row in rows}, {"LHR"})
        self.assertEqual({row["return_date"] for row in rows}, {"2027-02-06", "2027-02-07"})

    def test_schedule_filters_invalid_connections_and_ranks_exact_quotes(self):
        flights = [
            route("OUT", "BER", "AMS", "2027-02-01T08:00:00+01:00", "2027-02-01T09:30:00+01:00"),
            route("EARLY", "AMS", "LHR", "2027-02-01T09:25:00+01:00", "2027-02-01T10:20:00Z"),
            route("SHORT", "AMS", "LHR", "2027-02-01T10:29:00+01:00", "2027-02-01T10:50:00Z"),
            route("MIN", "AMS", "LHR", "2027-02-01T09:30:00Z", "2027-02-01T10:55:00Z"),
            route("MAX", "AMS", "LHR", "2027-02-01T11:00:00+01:00", "2027-02-01T11:30:00Z"),
            route("LATE", "AMS", "LHR", "2027-02-01T11:01:00+01:00", "2027-02-01T11:50:00Z"),
            route("DIRECT", "BER", "LHR", "2027-02-01T08:59:00+01:00", "2027-02-01T10:15:00Z"),
        ]
        quotes = [
            {"flight_ids": ["DIRECT"], "amount_minor": 15000, "currency": "EUR"},
            {"flight_ids": ["OUT", "MIN"], "amount_minor": 11000, "currency": "EUR"},
            {"flight_ids": ["OUT", "MIN"], "amount_minor": 12000, "currency": "EUR"},
            {"flight_ids": ["MAX"], "amount_minor": 50, "currency": "EUR"},
        ]
        with tempfile.TemporaryDirectory() as directory:
            schedule = Path(directory) / "schedule.json"
            schedule.write_text(json.dumps({"flights": flights, "quotes": quotes}), encoding="utf-8")
            result = invoke(
                "enumerate_timetable.py", str(schedule), "--origin", "BER", "--destination", "LHR",
                "--depart-after", "2027-02-01T07:00:00Z", "--depart-before", "2027-02-01T08:00:00Z",
                "--min-connection", "60", "--max-connection", "90", "--via", "AMS",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["journey_count"], 3)
        self.assertEqual([row["flight_ids"] for row in report["priced"]], [["OUT", "MIN"], ["DIRECT"]])
        self.assertEqual(report["priced"][0]["quote"]["amount_minor"], 11000)
        self.assertEqual([row["flight_ids"] for row in report["unpriced"]], [["OUT", "MAX"]])


if __name__ == "__main__":
    unittest.main()
