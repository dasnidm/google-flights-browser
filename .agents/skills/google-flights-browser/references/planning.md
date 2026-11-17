# Planning searches

## Enumerate the Google Flights queries

Run the bundled script with Python 3.9+ to produce a JSON list of query combinations before opening them in the site's browser UI. Dates are inclusive. Values are airport codes, with multiple values separated by spaces.

```shell
python scripts/plan_searches.py --origins BER HAM --destinations LHR --depart-dates 2027-01-12 2027-01-14
python scripts/plan_searches.py --origins BER HAM --destinations LHR LGW --depart-from 2027-02-01 --depart-to 2027-02-07 --nights 4 6
```

Add `--return-from YYYY-MM-DD --return-to YYYY-MM-DD` for a fixed return window. The window intersects `--nights MIN MAX` if supplied. With only a return window, include valid same-day returns and check time-of-day feasibility in the results. Repeated codes are deduplicated and identical origin/destination pairs are excluded. Track completion by scenario ID so a failed query cannot disappear from coverage.

For fixed destinations, use a relevant public airport or airline list for potential origins. Verify route direction and season. If the user allows connections, a list of nonstop origins is partial coverage. [BER's published route list](https://ber.berlin-airport.de/en/flying/destinations-from-ber.html) and [Heathrow's timetable](https://www.heathrow.com/flight-timetable) are examples of scoped inputs.

## Keep both endpoints fixed

Start with an ordinary origin-to-destination search for connections on one ticket. If the user names acceptable hubs, enumerate nonstop and each allowed connection airport in advance. Use the Connecting airports filter where the UI exposes the needed control, or check the airport on each visible itinerary. If a hub cannot be independently searched, record that coverage limit. For an intentional overnight or multi-day stopover, search through the multi-city form using the required stay. For separate tickets through a hub, collect the leg quotes for the actual dates, then pair only flights that satisfy the transfer requirements. Compare the final prices of these ticketing options separately.

## Enumerate trips from a timetable

1. Establish source coverage and dates. Prefer published future schedules for the airports and carriers in scope. Historical traffic records can help identify routes. The U.S. BTS T-100 dataset reports carrier traffic and capacity by segment. [BTS](https://transtats.bts.gov/DatabaseInfo.asp?QO_VQ=EED)
2. Model each physical flight as a dated leg with operating carrier and flight number, origin and destination, and timezone-aware scheduled departure and arrival. Deduplicate codeshares for schedule enumeration while preserving marketing-carrier options for fare checks. Sort by departure and enumerate chronologically reachable legs within the user's dates and connection bounds. Check elapsed time, airport/terminal transfers, self-transfer constraints, and actual dates for overnight legs. For a multi-stop trip, respect the user's permitted order and stay at each stop.
3. Price the resulting trips as ticketable journeys. An airline offer depends on seats, fare rules, product, and extras in addition to the schedule. The sum of independent leg fares is the cost of a split-ticket journey only if those exact individual offers are available. Through-ticket prices and availability can differ. [ATPCO](https://info.atpco.net/how-do-airlines-create-offers)
4. Rank the priced journeys and report unpriced schedules separately. Exhaustive schedule coverage requires complete input schedules in scope. An exact lowest bookable price additionally requires valid, comparable prices for every feasible ticketing option in that scope. A Google Flights UI subset can establish the best verified offer seen.

## Run the timetable enumerator

Save a UTF-8 JSON object with `flights` and optional `quotes`. Give each physical dated flight a unique ID. Use local ISO 8601 times with a UTC offset or a UTC timestamp ending in `Z`. This example is synthetic.

```json
{
  "flights": [
    {"id": "A", "origin": "BER", "destination": "AMS", "departure": "2027-02-01T08:00:00+01:00", "arrival": "2027-02-01T09:30:00+01:00"},
    {"id": "B", "origin": "AMS", "destination": "LHR", "departure": "2027-02-01T10:40:00+01:00", "arrival": "2027-02-01T11:00:00Z"}
  ],
  "quotes": [
    {"flight_ids": ["A", "B"], "amount_minor": 12500, "currency": "EUR", "seller": "Example"}
  ]
}
```

```shell
python scripts/enumerate_timetable.py schedule.json --origin BER --destination LHR --depart-after 2027-02-01T00:00:00+01:00 --depart-before 2027-02-01T23:59:59+01:00 --max-legs 2 --min-connection 60 --max-connection 360
```

Use `--via` to restrict intermediate airports and `--arrive-by` for a deadline. Departures and connection limits are inclusive. A connection must be at the same airport and satisfy the supplied time window. Account for carrier, terminal, protection, and baggage rules before treating generated itineraries as bookable. Supply actual quotes for the complete ordered flight IDs, in one currency and for the same passengers, cabin, and included services. `amount_minor` is the currency's minor unit, such as euro cents. Quotes specific to one flight apply to that one-flight itinerary. The script reports unpriced journeys by elapsed time and does not fetch schedules or quotes.
