"""Enumerate one-way journeys within a supplied timetable and rank exact quotes."""

import argparse
import json
from bisect import bisect_left, bisect_right
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timedelta

from plan_searches import airport_codes


def timestamp(value):
    if value.endswith("Z"):
        value = value[:-1] + "+00:00"
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError("Timestamps must include Z or a UTC offset.")
    return parsed


@dataclass(frozen=True)
class Flight:
    id: str
    origin: str
    destination: str
    departure: datetime
    arrival: datetime

    @classmethod
    def from_row(cls, row):
        origin, = airport_codes([row["origin"]])
        destination, = airport_codes([row["destination"]])
        departure = timestamp(row["departure"])
        arrival = timestamp(row["arrival"])
        if not isinstance(row["id"], str) or not row["id"].strip():
            raise ValueError("Each flight needs a nonempty string ID.")
        if origin == destination or arrival <= departure:
            raise ValueError(f"Invalid endpoints or timestamps for flight {row['id']}.")
        return cls(row["id"], origin, destination, departure, arrival)


def index_flights(rows):
    routes = defaultdict(list)
    ids = set()
    for row in rows:
        flight = Flight.from_row(row)
        if flight.id in ids:
            raise ValueError(f"Duplicate flight ID: {flight.id}")
        ids.add(flight.id)
        routes[flight.origin].append(flight)
    for flights in routes.values():
        flights.sort(key=lambda flight: (flight.departure, flight.id))
    times = {origin: [flight.departure for flight in flights] for origin, flights in routes.items()}
    return routes, times, ids


def index_quotes(quotes, ids):
    cheapest = {}
    currencies = set()
    for quote in quotes:
        flight_ids = quote["flight_ids"]
        if not isinstance(flight_ids, list) or not all(isinstance(value, str) for value in flight_ids):
            raise ValueError("Quote flight_ids must be a list of strings.")
        key = tuple(flight_ids)
        amount = quote["amount_minor"]
        currency = quote["currency"]
        if not key or any(flight_id not in ids for flight_id in key):
            raise ValueError("Every quote must identify known flights in travel order.")
        if type(amount) is not int or amount < 0:
            raise ValueError("Quote amount_minor must be a nonnegative integer.")
        if (not isinstance(currency, str) or len(currency) != 3
                or not currency.isascii() or not currency.isalpha() or not currency.isupper()):
            raise ValueError("Quote currency must be a three-letter uppercase code.")
        currencies.add(currency)
        if key not in cheapest or amount < cheapest[key]["amount_minor"]:
            cheapest[key] = quote
    if len(currencies) > 1:
        raise ValueError("Supply quotes in one currency so their totals can be compared.")
    return cheapest


def find_journeys(args, routes, times):
    lower = timedelta(minutes=args.min_connection)
    upper = timedelta(minutes=args.max_connection)
    hubs = set(args.via)

    def departing(airport, start, end):
        departures = times.get(airport, [])
        first = bisect_left(departures, start)
        last = bisect_right(departures, end)
        return routes.get(airport, ())[first:last]

    pending = [(first,) for first in departing(args.origin, args.depart_after, args.depart_before)]
    while pending:
        journey = pending.pop()
        last = journey[-1]
        if args.arrive_by is not None and last.arrival > args.arrive_by:
            continue
        if last.destination == args.destination:
            yield journey
        elif len(journey) < args.max_legs and (not hubs or last.destination in hubs):
            matches = departing(last.destination, last.arrival + lower, last.arrival + upper)
            pending.extend(journey + (flight,) for flight in matches)


def rank(args, data):
    args.origin, = airport_codes([args.origin])
    args.destination, = airport_codes([args.destination])
    args.via = airport_codes(args.via or [])
    if args.origin == args.destination or args.depart_after > args.depart_before:
        raise ValueError("Use distinct endpoints and an ordered departure window.")
    if args.max_legs < 1 or not 0 <= args.min_connection <= args.max_connection:
        raise ValueError("Use a positive leg limit and ordered nonnegative connection limits.")

    routes, times, ids = index_flights(data["flights"])
    quotes = index_quotes(data.get("quotes", []), ids)
    priced, unpriced = [], []
    for journey in find_journeys(args, routes, times):
        flight_ids = tuple(flight.id for flight in journey)
        elapsed = journey[-1].arrival - journey[0].departure
        row = {
            "flight_ids": flight_ids,
            "airports": [journey[0].origin] + [flight.destination for flight in journey],
            "departure": journey[0].departure.isoformat(),
            "arrival": journey[-1].arrival.isoformat(),
            "elapsed_seconds": int(elapsed.total_seconds()),
            "stops": len(journey) - 1,
        }
        if quote := quotes.get(flight_ids):
            row["quote"] = quote
            priced.append(row)
        else:
            unpriced.append(row)

    def order(row):
        return (row["elapsed_seconds"], row["stops"], timestamp(row["departure"]), row["flight_ids"])

    priced.sort(key=lambda row: (row["quote"]["amount_minor"], *order(row)))
    unpriced.sort(key=order)
    return {
        "search_bounds": {
            "origin": args.origin,
            "destination": args.destination,
            "depart_after": args.depart_after.isoformat(),
            "depart_before": args.depart_before.isoformat(),
            "arrive_by": args.arrive_by.isoformat() if args.arrive_by is not None else None,
            "max_legs": args.max_legs,
            "min_connection_minutes": args.min_connection,
            "max_connection_minutes": args.max_connection,
            "allowed_intermediate_airports": list(args.via) if args.via else None,
        },
        "journey_count": len(priced) + len(unpriced),
        "priced": priced,
        "unpriced": unpriced,
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=argparse.FileType("r", encoding="utf-8"))
    parser.add_argument("--origin", required=True)
    parser.add_argument("--destination", required=True)
    parser.add_argument("--depart-after", required=True, type=timestamp)
    parser.add_argument("--depart-before", required=True, type=timestamp)
    parser.add_argument("--arrive-by", type=timestamp)
    parser.add_argument("--max-legs", type=int, default=2)
    parser.add_argument("--min-connection", type=int, default=60, help="Minimum connection in minutes.")
    parser.add_argument("--max-connection", type=int, default=360, help="Maximum connection in minutes.")
    parser.add_argument("--via", nargs="+", help="Allowed intermediate airport codes.")
    args = parser.parse_args()
    try:
        with args.input as input_file:
            result = rank(args, json.load(input_file))
    except (KeyError, TypeError, AttributeError, OverflowError, ValueError) as error:
        parser.error(f"Invalid input: {error}")
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
