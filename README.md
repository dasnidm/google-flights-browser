# Google Flights Browser

A Codex skill for comparing Google Flights fares through the website. Use a browser that can open Google Flights. Fare research uses the browser interface and needs no separate fare API, account, or key.

## Install

- **Codex Cloud** — Connect this repository to a Cloud environment, or copy the entire `.agents/skills/google-flights-browser/` directory into a repository already used by that environment. Start a task with browser access and invoke `$google-flights-browser`. [Cloud environments](https://learn.chatgpt.com/docs/environments/cloud-environments)
- **Local Codex** — Open this repository as a project, or copy the skill directory to a personal skills location supported by your client. Use the skill in a chat with browser access. [Build skills](https://learn.chatgpt.com/docs/build-skills)

## Example requests

- `$google-flights-browser Find 4–6 night trips from BER to anywhere in February 2027. Compare the three lowest verified totals.`
- `$google-flights-browser Compare BER, HAM, and FRA to LHR on January 12 or 14, 2027. Keep LHR fixed and report which searches returned flights.`
- `$google-flights-browser Find combinations from BER to LIS in the first week of February 2027. Include direct, protected connections, and separate tickets only when the actual layover is at least four hours.`

The skill uses Explore for an open destination. For an open origin, it searches a defined set of origin airports in the requested direction. For fixed endpoints, use a date grid for discovery or enumerate every requested query first. The result includes query coverage and separates provisional prices, detailed quotes, and unpriced candidates.

## Offline planning tools

Both scripts run with Python 3.9+ and the standard library.

- [Plan searches](.agents/skills/google-flights-browser/scripts/plan_searches.py) lists airport/date combinations for the browser, including valid round-trip stay lengths.
- [Enumerate a timetable](.agents/skills/google-flights-browser/scripts/enumerate_timetable.py) lists one-way journeys with fixed endpoints, an optional set of connection airports, and explicit elapsed connection limits. It accepts a supplied schedule and optional quotes for exact flight combinations. It ranks comparable quotes by price and places journeys without quotes in a separate list. [Input format and examples](.agents/skills/google-flights-browser/references/planning.md)

A schedule establishes which journeys fit the modeled conditions. Ticket prices and seat availability depend on the offer, and coverage depends on the supplied timetable and fares. [ATPCO](https://info.atpco.net/how-do-airlines-create-offers)

## Verification

- Local Chrome returned flight results for BER and HAM to LHR on both January 12 and January 14, 2027, and Explore returned destinations from Berlin.
- The offline tools are covered by `python -B -m unittest discover -s tests`.
- Live Google Flights execution in Codex Cloud is pending.
