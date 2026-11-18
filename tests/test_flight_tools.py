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

    def test_explicit_arrival_offsets_intersect_return_window(self):
        result = invoke(
            "plan_searches.py", "--origins", "BER", "--destinations", "BER", "LHR",
            "--depart-from", "2027-02-01", "--depart-to", "2027-02-02",
            "--nights", "4", "6", "--arrival-offset-days", "0", "0",
            "--return-from", "2027-02-06", "--return-to", "2027-02-07",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        rows = json.loads(result.stdout)["scenarios"]
        self.assertEqual(len(rows), 4)
        self.assertEqual({row["destination"] for row in rows}, {"LHR"})
        self.assertEqual({row["return_date"] for row in rows}, {"2027-02-06", "2027-02-07"})

    def test_overnight_arrival_retains_four_night_return(self):
        query = ("plan_searches.py", "--origins", "BER", "--destinations", "NRT",
                 "--depart-dates", "2027-02-01", "--nights", "4", "4")
        default_result = invoke(*query)
        self.assertEqual(default_result.returncode, 0, default_result.stderr)
        plan = json.loads(default_result.stdout)
        self.assertEqual(plan["stay"]["outbound_arrival_offset_days"], [-1, 2])
        self.assertTrue(plan["stay"]["requires_itinerary_check"])
        self.assertIn("2027-02-06", {row["return_date"] for row in plan["scenarios"]})

        explicit_result = invoke(*query, "--return-from", "2027-02-06", "--return-to", "2027-02-06")
        self.assertEqual(explicit_result.returncode, 0, explicit_result.stderr)
        plan = json.loads(explicit_result.stdout)
        self.assertIsNone(plan["stay"]["outbound_arrival_offset_days"])
        self.assertEqual([row["return_date"] for row in plan["scenarios"]], ["2027-02-06"])

    def test_arrival_offset_can_cover_the_previous_local_date(self):
        result = invoke(
            "plan_searches.py", "--origins", "NRT", "--destinations", "HNL",
            "--depart-dates", "2027-02-01", "--nights", "0", "0",
            "--arrival-offset-days", "-1", "-1",
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)["scenarios"][0]["return_date"], "2027-01-31")

    def test_non_ascii_airport_is_rejected_before_case_conversion(self):
        result = invoke(
            "plan_searches.py", "--origins", "\u00dff", "--destinations", "LHR",
            "--depart-dates", "2027-02-01",
        )
        self.assertEqual(result.returncode, 2)
        self.assertIn("ASCII airport codes", result.stderr)

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
        self.assertEqual(report["search_bounds"], {
            "origin": "BER", "destination": "LHR",
            "depart_after": "2027-02-01T07:00:00+00:00",
            "depart_before": "2027-02-01T08:00:00+00:00", "arrive_by": None,
            "max_legs": 2, "min_connection_minutes": 60, "max_connection_minutes": 90,
            "allowed_intermediate_airports": ["AMS"],
        })
        self.assertEqual([row["flight_ids"] for row in report["priced"]], [["OUT", "MIN"], ["DIRECT"]])
        self.assertEqual(report["priced"][0]["quote"]["amount_minor"], 11000)
        self.assertEqual([row["flight_ids"] for row in report["unpriced"]], [["OUT", "MAX"]])


    def test_empty_timetable_reports_effective_defaults(self):
        with tempfile.TemporaryDirectory() as directory:
            schedule = Path(directory) / "schedule.json"
            schedule.write_text('{"flights": []}', encoding="utf-8")
            result = invoke(
                "enumerate_timetable.py", str(schedule), "--origin", "ber", "--destination", "LHR",
                "--depart-after", "2027-02-01T07:00:00Z", "--depart-before", "2027-02-01T08:00:00Z",
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        report = json.loads(result.stdout)
        self.assertEqual(report["journey_count"], 0)
        self.assertEqual(report["search_bounds"]["origin"], "BER")
        self.assertEqual(report["search_bounds"]["max_legs"], 2)
        self.assertEqual(report["search_bounds"]["min_connection_minutes"], 60)
        self.assertEqual(report["search_bounds"]["max_connection_minutes"], 360)
        self.assertIsNone(report["search_bounds"]["allowed_intermediate_airports"])


if __name__ == "__main__":
    unittest.main()
