"""Enumerate airport and date scenarios for browser-based flight searches."""

import argparse
import itertools
import json
import re
from datetime import date, timedelta


def airport_codes(values):
    codes = tuple(dict.fromkeys(code.upper() for code in values))
    if invalid := [code for code in codes if not re.fullmatch(r"[A-Z]{3}", code)]:
        raise ValueError(f"Expected three-letter airport codes: {', '.join(invalid)}")
    return codes


def dates_between(start, end):
    for offset in range((end - start).days + 1):
        yield start + timedelta(days=offset)


def planned_dates(args):
    if args.depart_dates is not None:
        if args.depart_to is not None:
            raise ValueError("Use --depart-to only with --depart-from.")
        departures = sorted(set(args.depart_dates))
    else:
        if args.depart_to is None or args.depart_from > args.depart_to:
            raise ValueError("Provide an end date on or after the departure start.")
        departures = dates_between(args.depart_from, args.depart_to)
    if (args.return_from is None) != (args.return_to is None):
        raise ValueError("Provide both ends of the return window.")
    if args.return_from is not None and args.return_from > args.return_to:
        raise ValueError("Return start must be on or before return end.")
    if args.nights and not 0 <= args.nights[0] <= args.nights[1]:
        raise ValueError("Nights must be nonnegative and ordered as MIN MAX.")

    for departure in departures:
        if args.return_from is None and args.nights is None:
            yield departure.isoformat(), None
            continue

        if args.nights:
            first, last = (departure + timedelta(days=nights) for nights in args.nights)
        else:
            first, last = departure, args.return_to

        if args.return_from is not None:
            first = max(first, args.return_from)
            last = min(last, args.return_to)

        for returning in dates_between(first, last):
            yield departure.isoformat(), returning.isoformat()


def plan(args):
    origins = airport_codes(args.origins)
    destinations = airport_codes(args.destinations)
    date_pairs = tuple(planned_dates(args))
    routes = (
        (origin, destination)
        for origin, destination in itertools.product(origins, destinations)
        if origin != destination
    )
    scenarios = []
    for origin, destination in routes:
        for departure, returning in date_pairs:
            scenarios.append({
                "id": len(scenarios) + 1,
                "origin": origin,
                "destination": destination,
                "departure_date": departure,
                "return_date": returning,
            })
    return {"scenario_count": len(scenarios), "scenarios": scenarios}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--origins", nargs="+", required=True)
    parser.add_argument("--destinations", nargs="+", required=True)
    departure = parser.add_mutually_exclusive_group(required=True)
    departure.add_argument("--depart-dates", nargs="+", type=date.fromisoformat)
    departure.add_argument("--depart-from", type=date.fromisoformat)
    parser.add_argument("--depart-to", type=date.fromisoformat)
    parser.add_argument("--return-from", type=date.fromisoformat)
    parser.add_argument("--return-to", type=date.fromisoformat)
    parser.add_argument("--nights", nargs=2, type=int, metavar=("MIN", "MAX"))
    args = parser.parse_args()
    try:
        result = plan(args)
    except (OverflowError, ValueError) as error:
        parser.error(str(error))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
