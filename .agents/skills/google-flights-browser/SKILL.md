---
name: google-flights-browser
description: Search and compare fares in the Google Flights browser UI. Use for flexible dates, multiple airports, Explore with an open destination, a fixed destination with several possible origins, and exhaustive comparison of a finite set of route and date combinations.
---

# Google Flights browser search

Open [Google Flights](https://www.google.com/travel/flights) in the browser available to this chat. In Codex Cloud, use the task's browser when available and verify that it loads the Google Flights results page. Use the site's visible search controls and results for fares. The workflow requires browser access to Google Flights and uses no flight-data API, API key, or login. If the Cloud browser or site is unavailable, report the concrete blocker and any scenarios already completed.

## Choose the search scope

Preserve fixed requirements for travel direction, passenger count, cabin, currency, dates and local time windows, stops, baggage, and minimum connection or stay durations. Resolve relative dates and verify airport codes in the suggestions.

- **Origin fixed, destination open.** Use [Explore](https://www.google.com/travel/explore) with the origin and an open destination. Set the date or flexible-date window, trip length, region or map area, and filters where available. Map/list prices are discovery leads. Check actual dates and nights for each result, then open the best eligible candidates in the regular flight search.
- **Destination fixed, origin open.** Define a finite origin list from the user's airport list, region, or ground-access range. Use public airport or airline route lists to find candidates when helpful. A nonstop route list covers only nonstop origins. Run each search in the requested direction with the destination fixed. Use the multiple-airport picker for a quick scan. Search origins separately when a grouped result does not establish coverage for each origin. Include verified ground-access cost if the objective is door-to-door price.
- **Endpoints fixed, dates or connections flexible.** Use the date grid or price graph to shortlist dates for a quick search. For exhaustive comparison within the requested bounds, enumerate airports times dates, plus valid return dates and stay lengths for round trips, before collecting fares. Use `scripts/plan_searches.py` from the skill folder for larger finite grids. For multi-city, enter each ordered sequence in the multi-city form. Compare one-ticket and split-ticket itineraries using their own complete fare quotes and connection conditions.

## Verify prices

1. Apply the requested filters and confirm the selected airports, dates, and trip type. In the date picker, confirm that the Done button describes the intended date(s). If clicking it changes the date or keeps the form open, use the date field and apply the verified Done button with keyboard activation when supported.
2. Wait for a new result whose own airport and date labels match the request. The search header can update before the flight list does. Record each planned scenario as found, no match (explicit completed search), failed, or unsearched. If the site reports a transient error, retry once with its Reload control when available. Treat blank calendar cells and loading states as incomplete evidence.
3. Use the Cheapest tab for a price objective and expand available results when useful. Record distinct eligible itineraries, including airport, all local dates and times, duration, stops, flight numbers when shown, and observed price. For round trips and multi-city searches, select each leg to confirm the complete journey total. A calendar, Explore, tab label, or result marked "from" can change when detailed options arrive. Recheck finalists in the Google Flights itinerary/booking-options view and record its link, seller and fare scope. Finish at the displayed booking options.
4. Rank comparable offers according to the user's priorities. For separate tickets, check the actual arrival-to-departure interval in the same time zone, airport changes, baggage recheck, and whether the connection is protected. Compare the sum of quoted tickets and any known extras. Keep unknown charges visible.

Report checked vs planned scenarios, exclusions, query failures, and prices among the verified offers. A complete scenario grid establishes coverage of its queries. A globally cheapest fare claim additionally depends on complete offer coverage and current quotes.

To enumerate one-way journeys from a supplied timetable, use `scripts/enumerate_timetable.py`. Its exact-flight quotes are optional and separate from schedule coverage. See [Planning searches](references/planning.md) for both offline tools and their input formats.
