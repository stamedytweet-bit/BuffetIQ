# Assumptions

This file records every assumption behind the fictional data and the rules, so that assessors can check where each number comes from and judge it for themselves. The settings themselves live in `config.yaml` (sections `dishes`, `simulation` and `calendar`), and the generator is `src/buffetiq/data_gen.py`. Every figure produced from these assumptions is simulated on fictional data.

## Hotel and service

The prototype uses a fictional 300-room city hotel called Selat House, with breakfast at The Daybreak Room on Level 2 from 06:30 to 10:30 in sixteen 15-minute slots. The names were searched in November 2026 and no hotel or Singapore restaurant with these names was found; earlier ideas such as "Embun" were dropped because they were too close to real venues (for example *embu* at Mandarin Oriental Singapore).

## Simulated year and calendar

The history covers 365 breakfasts from Tuesday 25 November 2025 to Tuesday 24 November 2026, so that the last simulated day is the demo morning shown on the design screens and the 65 test days in Phase 2 (21 September to 24 November 2026) end on it. A further 28 days before the start are simulated only to give the chef rule (below) a history to average, and are then discarded.

Public holidays are the 11 days gazetted by the Ministry of Manpower that fall in the year, using the observed Monday where a holiday falls on a Sunday: Christmas Day 2025, New Year's Day, Chinese New Year (17 and 18 February), Hari Raya Puasa (21 March), Good Friday (3 April), Labour Day, Hari Raya Haji (27 May), Vesak Day (observed 1 June), National Day (observed 10 August) and Deepavali (observed 9 November) ([MOM, public holidays for 2026](https://www.mom.gov.sg/newsroom/press-releases/2025/0616-public-holidays-for-2026)). The two Hari Raya dates were provisional when announced; reporting on 21 March 2026 confirms that Hari Raya Puasa prayers took place that Saturday ([The Star](https://www.thestar.com.my/aseanplus/aseanplus-news/2026/03/21/muslim-community-in-singapore-grateful-for-peace-of-mind-and-heart-during-ramadan-minister)).

School holidays follow the Ministry of Education calendars for primary and secondary schools: the 2025 year-end break from 22 November to 31 December ([MOE, 2025 terms](https://www.moe.gov.sg/news/press-releases/20240812-school-terms-and-holidays-for-2025)), and in 2026 the March break (14 to 22 March), the mid-year break (30 May to 28 June), the Youth Day holiday (6 July), Teachers' Day and the September break (4 to 13 September), Children's Day (2 October) and the year-end break from 21 November ([MOE, 2026 terms](https://www.moe.gov.sg/news/press-releases/20250730-school-terms-and-holidays-for-2026)). Junior college dates differ slightly and are ignored, because they matter little to hotel breakfasts.

## Occupancy

Occupancy drives everything else, so it is anchored on published figures. Each month's average equals the Singapore Tourism Board's average hotel occupancy rate for that month, taken from the SingStat table published on data.gov.sg (dataset `d_8e62605f0c1c948702b6ea0fe45242d3`). The values run from 74.9% (May 2026) to 91.3% (July 2026). October and November 2026 were not yet published when the data was generated, so the 2025 values for those months (84.8% and 85.0%) are reused. The STB's full-year figure for 2025 was 82.0%.

Within each month, a city-hotel weekly pattern is added for the night before each breakfast: 5 percentage points lower before a Monday breakfast (Sunday night is the quietest night in a business district), 2 points higher before Tuesday to Friday breakfasts, 1 point lower before Saturday and 1 point higher before Sunday, plus 2 points on public holidays. Day-to-day noise follows an AR(1) process (each day's random shock carries 60% of the previous day's) with a standard deviation of 2.5 points. The pattern is then shifted so that every month still averages exactly the STB figure. The six days of November 2025 in range average 90% because they fall in a high-occupancy week; the month as a whole, including the discarded warm-up days, averages 85.0%.

## Guests

The share of rooms that include breakfast comes from the Hotel Booking Demand dataset (Antonio, de Almeida and Nunes, 2019, *Data in Brief* 22, pp. 41 to 49), which records 79,330 bookings at a city hotel in Portugal. We computed from the dataset that 78.5% of the city hotel's bookings were bed and breakfast (77.1% of those not cancelled). The simulation draws each day's share from a beta distribution with a mean of 78% and a standard deviation of 4 points. The day-to-day spread in the raw dataset is wider (14.6 points), but most of that comes from small daily samples of about 40 arrivals, so a narrower spread was used for a 300-room hotel. The simulated year averages 78.3%.

Rooms are split into business and leisure. The business share is 55% before Tuesday to Friday breakfasts, 45% on Mondays, 20% at weekends and 15% on public holidays, reduced by 15% during school holidays, with a day-to-day standard deviation of 6 points (simulated average 41%). Business rooms hold 1.1 adults on average and leisure rooms 1.9, close to the dataset's 1.83 adults per city hotel booking. Children appear only in leisure rooms, at 0.08 per room on weekdays, 0.15 at weekends, 0.30 on school holiday weekdays and 0.35 on school holiday weekends; the dataset averages 0.107 children per booking. Children make up 5.4% of in-house guests across the year and 10.9% during school holidays.

Group bookings (such as tour parties) are present on 8% of weekdays and 15% of weekends and public holidays, plus 5 points during school holidays, with 16 to 40 guests at two per room. Groups always take breakfast and arrive together, with 70% of each group in two consecutive slots between 06:45 and 08:00. In the dataset, 9.4% of the city hotel's bookings came through the groups segment.

Not every guest with breakfast eats it. The show rate is 88% for business guests, 82% for leisure guests and their children, and 97% for groups, and 10% of guests without breakfast included buy it. These rates are our own estimates; we found no published show rate for Singapore hotel breakfasts, so they are an obvious point to check with a hotel contact.

## Surprises

About one day in fifteen (a probability of 6.67% per day) has a surprise that none of the forecast features can see: an unannounced tour party of 18 to 30 guests arriving between 06:45 and 07:30 (35% of surprises), rain that raises show rates by 8% and pushes leisure arrivals 20 minutes later and wider (30%), an early conference or flights that pull business arrivals 20 minutes earlier (20%), or a quiet morning with show rates 12% lower (15%). The frozen year has 32 surprise days (1 in 11), more than the expected 24 because of random variation, and they were left as drawn rather than redrawn. The `surprise` column records them for evaluation only and must never be used as a model feature.

## Check-ins from the guest page

Each day, a response rate is drawn uniformly between 0% and 40%, and each diner checks in with that probability; another 5% of diners' worth of guests check in but do not come. Check-ins therefore cover 21% of diners on average and range from none to 161 guests, so the models can use them but never depend on them. The `checkin_response_rate` column is for evaluation only, because a hotel only sees the count.

## Arrival times

Arrival times are a mix of two bell-shaped curves (normal distributions), cut at the service hours and split into the sixteen slots. Business guests centre on 07:30 with a standard deviation of 30 minutes. Leisure guests centre on 08:35 on weekdays (45 minutes) and on 09:00 at weekends and on public holidays (40 minutes). Each day's mix follows that day's share of business diners, and each centre moves by a few minutes at random (5 minutes for business, 8 for leisure). Diners are then dealt into slots at random (a multinomial draw), so the arrivals always add up to the day's diners. These shapes are our own estimates, chosen to give the peaks set in the brief: 07:00 to 08:00 on business-heavy weekdays and 08:30 to 09:30 at weekends.

## Food eaten

Portions are anchored on the day-end report design, where 293 guests ate 109.9 kg, or about 0.375 kg each. Published per-guest consumption figures for hotel breakfast buffets are scarce; most studies measure waste instead (see the check below). Each dish has a rate per adult diner taken from the design (for example 0.068 kg of scrambled eggs and 0.40 croissants), adjusted for business guests (such as 10% more eggs and 40% fewer pancakes) and for children, who eat 60% of an adult portion overall but 2.5 times the adult share of pancakes. Each dish's daily amount also varies by a random factor with a standard deviation of about 7% (a lognormal draw), for taste and menu variation. The resulting true demand is kept in the `_demand` columns, which only the simulation knows.

## What the chef prepares

The baseline is a typical chef rule: for each dish, the average amount eaten on the same weekday over the previous four weeks, plus 15%, rounded up to whole batches. The chef sees only what was eaten, which is capped by what was prepared, so a day that ran short pulls later plans down slightly. "Consumed" is the smaller of demand and prepared, and "leftover" is prepared minus consumed. Croissants are recorded in pieces and converted at 60 g each where kilograms are needed.

This rule gives 123.3 kg prepared, 102.8 kg eaten and 20.5 kg left over on an average day (16.6% of what was prepared), costing about S$106 a day at the costs in `config.yaml`. That is 73 g left per diner. As a check, the Dutch Hotel Monitor, run with Wageningen University & Research, measured an average of 62.2 g of food left on the breakfast buffet per guest ([KHN](https://khn.nl/nieuws/minder-voedselverspilling-in-hotels-zo-doe-je-dat)), so the simulated baseline sits in a realistic range without being tuned to it.

The simulated baseline differs from the design screens in two ways that the later phases will report honestly. The design's "usual day" shows 41.2 kg of leftovers and S$214 of waste, about twice the simulated 20.5 kg and S$106, so the day-end report will compare against the simulated figures rather than the design's sample numbers. In addition, demand exceeded the amount prepared on 7% to 15% of days for each dish (24 days for croissants up to 55 for pancakes, which rise sharply during school holidays). In a real kitchen a chef would cook again on those days, so this is a shortfall in the plan, not minutes with an empty tray; Phase 5 measures stock-out minutes properly by replaying each morning slot by slot.

## Dish settings

The eight dishes, their stations, lead times, batch sizes, pan capacities, last-cook times, costs and flags are set in `config.yaml`. The lead times (6 minutes for pancakes on the live station up to 25 minutes for nasi lemak rice) and pan capacities (1.5 kg to 5.0 kg, and 40 croissants) are chosen to match the sample screens. Costs per kilogram range from S$2.50 (rice) to S$12.00 (croissants) and are our own estimates of food cost, not supplier prices.

## Freezing the data

The data was generated once with seed 20261124 and frozen before Phase 2, with its SHA-256 checksum recorded in `docs/EVIDENCE.md` and checked by a test. Later phases may not change the generator or its settings to improve results. If a realism error is found, it will be fixed only with the group's agreement, logged here with its reason, and every result rerun.

## Forecast settings (Phase 2)

The forecast settings live in the `forecast` section of `config.yaml`. The models train on the first 300 days and test on the last 65; the tuning grid tries tree depths of 8, 12 and unlimited with leaves of 1, 3 and 5 days, using five time-ordered folds. The arrival-curve model replaces the simple average profile only if it is at least 5% more accurate on the training days, a bar set before any results were seen. The shopping list buys for the 80th percentile because raw ingredients keep for days, so a small margin costs little against the cost of running out mid-service.

## Recipe card

The shopping list turns finished amounts into raw ingredients using the `recipes` section of `config.yaml`. The quantities are our own kitchen estimates, not supplier specifications: for example 18 eggs, 0.1 litres of milk and 30 g of butter per kilogram of scrambled eggs, 0.4 kg of raw rice and 0.25 litres of coconut milk per kilogram of nasi lemak rice, 1.1 kg of raw sausages per kilogram cooked (about 10% cooking loss) and 1.6 kg of whole fruit per kilogram of cut fruit (about 60% usable after peeling). A hotel would replace these with its own standard recipes.

## Guest flow and check-ins (Phase 3)

The guest page books the same breakfast that the kitchen board shows, so that a booking in the showcase demo changes the board at once. Its heading reads "Breakfast tomorrow" when opened before the service day and "Breakfast this morning" on the day; on the morning itself, half hours that have already ended are not offered. Until the presenter controls arrive in Phase 8, the service clock stands at 06:15 on Tuesday 24 November 2026.

The live forecast for the service is trained only on days before it, so it never sees the morning it predicts. Confirmed guests are added to the check-in count the hotel already had for that morning and the Random Forest is rerun. Each guest who replies "Not this time" lowers the forecast by the share of in-house guests expected to eat breakfast (forecast diners divided by guests in house, 66% on the demo morning). Confirmed guests are placed in their chosen half hour, split evenly between its two 15-minute slots, and everyone else follows the forecast arrival curve. A half hour is Quiet below 40% of the busiest half hour, Moderate from 40% to 75%, and Busy above 75%. When a guest picks a Busy half hour, the nearest Quiet one is suggested, and a later one wins a tie, because earlier times may already have passed or suit fewer guests.

Room numbers must have 3 to 5 digits. They are kept so that "Change my plans" replaces a room's earlier plan, are stored only in `data/guest_checkins.csv` on the laptop (ignored by git), and are deleted when the service date moves on, which stands in for checkout. Dietary needs are kept as halal and vegetarian meal counts, capped at the party size, never as names.

The key-card sleeve insert is 85 x 55 mm, the size of a hotel key card, printed at 300 dots per inch.
