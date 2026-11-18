# Planning searches

## Enumerate the Google Flights queries

Run the bundled script with Python 3.9+ to produce a JSON list of query combinations before opening them in the site's browser UI. Dates are inclusive. Values are airport codes, with multiple values separated by spaces.

```shell
python scripts/plan_searches.py --origins BER HAM --destinations LHR --depart-dates 2027-01-12 2027-01-14
python scripts/plan_searches.py --origins BER HAM --destinations LHR LGW --depart-from 2027-02-01 --depart-to 2027-02-07 --nights 4 6
```

Add `--return-from YYYY-MM-DD --return-to YYYY-MM-DD` for a fixed return window. With a stay-length constraint, an explicit return window is searched in full until actual outbound arrival dates are known. `--nights MIN MAX` counts from destination-local outbound arrival to destination-local return departure. With no explicit return window, the planner generates candidates using arrival offsets of −1 through +2 calendar days from outbound departure. Set `--arrival-offset-days MIN MAX` to cover the known arrival range, including longer arrivals where relevant. An explicit offset range also narrows an explicit return window. Every generated date remains provisional until the selected itinerary satisfies the stay and chronological order. With only a return window, include valid same-day returns and check time-of-day feasibility in the results. Repeated codes are deduplicated and identical origin/destination pairs are excluded. Track completion by scenario ID so a failed query cannot disappear from coverage.

For fixed destinations, use a relevant public airport or airline list for potential origins. Verify route direction and season. If the user allows connections, a list of nonstop origins is partial coverage. [BER's published route list](https://ber.berlin-airport.de/en/flying/destinations-from-ber.html) and [Heathrow's timetable](https://www.heathrow.com/flight-timetable) are examples of scoped inputs.

## Check official times by flight number

Start with the full flight designator and the local departure date. Use the airline's official flight-status or timetable search, select the matching departure and arrival airport, and use the operating carrier's number for codeshares when available. Record the scheduled local departure and arrival date and time, airport codes, source URL, and any separate estimated or actual time. Keep the next-day arrival date explicit. Check the source's date coverage. If a distant date is missing from a live status page, try the airline's regular timetable or an airport's seasonal timetable for the applicable dates.

- [Lufthansa timetable and flight status](https://www.lufthansa.com/de/en/timetable-and-flight-status)
- [easyJet Flight Tracker](https://www.easyjet.com/en/flight-tracker)
- [Korean Air flight information](https://www.koreanair.com/contents/booking/flight-info?hl=en)
- [Berlin Brandenburg departures and arrivals](https://ber.berlin-airport.de/en/fliegen/abfluege-ankuenfte.html)
- [Munich Airport flight search and seasonal timetable](https://www.munich-airport.com/flugsuche-89523)

## Keep both endpoints fixed

Start with an ordinary origin-to-destination search for connections on one ticket. If the user names acceptable hubs, enumerate nonstop and each allowed connection airport in advance. Use the Connecting airports filter where the UI exposes the needed control, or check the airport on each visible itinerary. If a hub cannot be independently searched, record that coverage limit. For an intentional overnight or multi-day stopover, search through the multi-city form using the required stay. For separate tickets through a hub, collect the leg quotes for the actual dates, then pair only flights that satisfy the transfer requirements. Compare the final prices of these ticketing options separately.

## Obtain multiple scheduled flights

- **Public seasonal timetable.** [Munich Airport's seasonal timetable](https://www.munich-airport.de/saisonflugplan) publishes scheduled flight numbers, both local times, operating-day patterns, airport codes and effective dates. Expand the dates in the requested window using each row's operating days and validity interval. Preserve departure/arrival direction, calendar day changes, and each airport's UTC offset. Scope the output to schedules covered by the source.
- **Public-sector API with a key.** [Korea Airports Corporation](https://www.data.go.kr/data/15158949/openapi.do) documents JSON and XML schedules for its 14 airports. [Incheon Airport publishes a separate flight-data API](https://www.data.go.kr/en/data/15140153/openapi.do).
- **Provider APIs.** [Lufthansa Flight Schedules](https://developer.lufthansa.com/docs/read/api_details/operations/Flight_Schedules) documents route-and-date schedule queries up to 360 days ahead. [Cirium Schedules](https://developer.flightstats.com/products/scheduled_flights) documents queries by flight number, route and airport. The [Aviyair GitHub repository](https://github.com/aviyairapi/Future-Flight-Schedules-API) documents a hosted API with subscription access.
- **Open-source parsing and historical data.** [ssim-parser](https://github.com/zhjch/ssim-parser) converts supplied SSIM files to structured rows. [IATA's schedule data exchange](https://www.iata.org/schedule-data) describes separately licensed feed access. [MrAirspace](https://github.com/MrAirspace/aircraft-flight-schedules) publishes quarterly ADS-B-derived observations. [OpenFlights](https://openflights.org/data) provides airport and route reference data. Use these last two sources for route discovery or historical analysis and verify future schedules with a dated source.

Normalize the chosen source to dated flight rows with stable operating-flight IDs. The Munich timetable was smoke-tested with two published December 2, 2026 rows: LH094 (FRA–MUC) and LH2472 (MUC–LHR). The offline tool found the resulting journey with a 75-minute connection. The example has schedule evidence only.

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

Use `--via` to restrict intermediate airports and `--arrive-by` for a deadline. Departures and connection limits are inclusive. Each result includes `search_bounds` with the effective endpoints, date-time limits, segment limit, connection limits and hub filter, even if no journey is found. A connection must be at the same airport and satisfy the supplied time window. Account for carrier, terminal, protection, and baggage rules before treating generated itineraries as bookable. Supply actual quotes for the complete ordered flight IDs, in one currency and for the same passengers, cabin, and included services. `amount_minor` is the currency's minor unit, such as euro cents. Quotes specific to one flight apply to that one-flight itinerary. The script reports unpriced journeys by elapsed time and does not fetch schedules or quotes.
