# Evidence

This file collects every metric, chart and test result in one place for the showcase slides. Each phase adds its section, and every result here is simulated on fictional data.

## Phase 0: setup and static screens

Phase 0 has no models, so its evidence is the test suite and the screen comparison. The test suite (`python -m pytest -q`) checks the configuration, the colour tokens from CLAUDE.md, text contrast of at least 4.5:1 for every text and background pair in both modes, the absence of em dashes in on-screen copy, the "Fictional data" labels, accessible names for symbol-only buttons, that all five pages build, and that no API key is committed.

## Phase 1: synthetic data

This section shows that the fictional hotel's year of breakfasts behaves as intended, before any model sees it. The data covers 365 breakfasts at a fictional 300-room Singapore city hotel from 25 November 2025 to 24 November 2026. It is simulated on fictional data, with every assumption and its source in `docs/ASSUMPTIONS.md`.

The data was frozen on 21 November 2026, before Phase 2 began. The file `data/synthetic_breakfast.csv` (365 rows, 65 columns, generated with seed 20261124) has the SHA-256 checksum `86846b20aca06899e35f41c1546282924d0ccd92a01cb5f8f375dc1df7497022`, and `tests/test_data_gen.py` fails if it changes.

The year averages 282 diners a day (265 on weekdays and 319 at weekends and on public holidays, from 200 to 412), with 83% occupancy, 78.3% of rooms including breakfast and check-ins from 21% of diners. There are 37 group days and 32 surprise days (14 rain, 13 early tour groups, 4 early events and 1 quiet morning).

Weekday arrivals peak in the 07:30 slot (11.1% of the morning), with 39% of diners arriving between 07:00 and 08:00. Weekend and public holiday arrivals peak in the 09:00 slot (12.9%), with 48% arriving between 08:30 and 09:30.

![Weekday and weekend arrival curves](charts/phase1_arrival_curves.png)

Under the baseline chef rule (same-weekday average over four weeks plus 15%), an average day has these amounts per dish, with croissants converted at 60 g each:

| Dish | Prepared (kg) | Eaten (kg) | Left (kg) | Left (% of prepared) | Days demand exceeded the plan | Cost of leftovers (S$ a day) |
| --- | --- | --- | --- | --- | --- | --- |
| Scrambled eggs | 22.3 | 19.0 | 3.3 | 14.8 | 47 | 16.52 |
| Chicken sausages | 15.9 | 13.3 | 2.6 | 16.3 | 27 | 19.37 |
| Hash browns | 11.6 | 9.6 | 1.9 | 16.7 | 32 | 7.69 |
| Pancakes | 7.3 | 6.1 | 1.1 | 15.7 | 55 | 5.12 |
| Mee goreng | 16.4 | 13.6 | 2.8 | 17.1 | 33 | 9.79 |
| Nasi lemak rice | 19.1 | 16.0 | 3.1 | 16.3 | 40 | 7.75 |
| Croissants | 8.5 | 6.8 | 1.7 | 20.4 | 24 | 20.79 |
| Cut fruit | 22.4 | 18.5 | 4.0 | 17.6 | 28 | 19.00 |
| **Total** | **123.3** | **102.8** | **20.5** | **16.6** | | **106** |

That is 73 g of leftovers per diner, close to the 62.2 g per guest measured by the Dutch Hotel Monitor, and about S$38,700 a year. It is about half the "usual day" on the day-end report design (41.2 kg, S$214), so later phases will compare BuffetIQ with these simulated figures rather than the design's sample numbers.

The sanity tests in `tests/test_data_gen.py` (17 tests) check that there are no negative numbers, that arrivals add up to diners every day, that leftover equals prepared minus consumed, that prepared amounts are whole batches, that monthly occupancy is within 1 point of the STB figures, that the weekday and weekend peaks fall in the required windows, that children raise pancake demand, that surprises occur on 3% to 11% of days and that check-in response never exceeds 40%. All 96 tests in the project pass.

## Phase 2: demand forecast for the night before

This section shows whether the night-before forecast is better than what a kitchen does today. The forecast predicts how many guests will eat, when they will arrive in each 15-minute slot, and how much of each dish they will need, using only what the hotel knows the evening before. It is compared with the usual planning shortcut, the average of the same weekday over the previous four weeks. Every result is simulated on fictional data, and the numbers come from `python -m buffetiq.forecast` (run from `src`), also available as `notebooks/02_evaluate_forecast.ipynb`, with the raw output in `docs/phase2_results.json`.

The models are trained on the first 300 days (25 November 2025 to 20 September 2026) and tested once on the last 65 (21 September to 24 November 2026), so they never see the future. Every choice of settings and method was made on the training days alone, through time-ordered cross-validation (each fold is predicted by a model trained only on earlier days). Error is reported as MAE (mean absolute error, the average miss), RMSE (root mean squared error, which punishes large misses more) and MAPE (mean absolute percentage error).

### Diners

A Random Forest (an average of 300 decision trees) uses the day of week, the weekend, public holiday and school holiday flags, occupancy, adults and children in house, breakfast-inclusive rooms, the business guest share, the group booking flag and guest-page check-ins. Its best settings from the training days were trees grown to a maximum depth of 12 with leaves of one day.

| Method | MAE (diners) | RMSE (diners) | MAPE |
| --- | --- | --- | --- |
| Random Forest | 9.1 | 11.8 | 3.2% |
| Same weekday, last 4 weeks | 20.3 | 27.0 | 7.2% |

The forecast more than halves the baseline's error, missing by 9 diners on an average test day of 280. The largest misses are on 21 and 22 November, the first weekend of the school holidays, when 383 and 351 guests came against forecasts of 348 and 339, though the baseline missed those days by 74 and 42.

![Forecast against actual diners on the 65 test days](charts/phase2_diners_test.png)

Permutation importance measures how much worse the forecast gets when one feature's values are shuffled across the test days. Adults in house matters most (shuffling it adds 15.0 diners to the average miss), followed by breakfast-inclusive rooms (6.9), the business guest share (1.8) and children in house (1.7). Check-ins add only 0.4, as intended, because they cover between 0% and 40% of guests. Day of week and the holiday flags score close to zero, not because they do not matter but because their effect already shows up in the guest counts and the business share. This also reflects a limit of synthetic data: diners were generated from these same counts, so real hotel data would contain more unexplained variation and a larger error.

![Feature importance for the diner forecast](charts/phase2_feature_importance.png)

### Arrival curve

Two ways of predicting each slot's share of the morning were compared: a Random Forest per slot (using day type, holidays, business share, group flag and the share of children), and a simple average profile for weekdays and for weekends and public holidays. On the training days, through cross-validation, the model's average error per slot was 1.40 percentage points against 1.41 for the profile, less than the 5% improvement set in advance as the bar for choosing the more complex method, so the average profile is used. The test days agree: the model would have been 1.33 points against 1.39, a 4.5% gain, still inside that bar. The profile is easier to explain and cannot overfit, and most of the day-to-day variation in arrivals is random rather than predictable from the features. Turned into diners per slot, the forecast misses by 4.0 diners per slot against 4.5 for the same-weekday baseline.

### Dishes

Each dish's amount is a predicted rate per diner multiplied by predicted diners. The rate either comes from a small linear regression on the business share, the share of children in house and the weekend flag, or is a fixed average; the regression was kept for a dish only if it beat the fixed rate on the training days, which it did for five dishes. Days when a dish ran out (everything prepared was eaten) were left out when fitting rates, because what was eaten on those days understates appetite. The test days are scored against the simulation's true demand, which the models never see.

| Dish | Unit | MAE | MAPE | Baseline MAE | Baseline MAPE | Rate method |
| --- | --- | --- | --- | --- | --- | --- |
| Scrambled eggs | kg | 0.99 | 5.1% | 1.48 | 7.7% | Guest mix |
| Chicken sausages | kg | 0.76 | 5.7% | 1.01 | 7.7% | Fixed |
| Hash browns | kg | 0.61 | 6.2% | 0.88 | 8.9% | Fixed |
| Pancakes | kg | 0.47 | 7.3% | 0.66 | 10.7% | Guest mix |
| Mee goreng | kg | 0.88 | 6.3% | 1.27 | 9.3% | Guest mix |
| Nasi lemak rice | kg | 1.14 | 7.0% | 1.87 | 11.5% | Guest mix |
| Croissants | pieces | 7.7 | 7.0% | 10.8 | 9.7% | Guest mix |
| Cut fruit | kg | 1.34 | 7.0% | 1.65 | 8.7% | Fixed |

The forecast beats the baseline for every dish, cutting the average miss by between 19% (cut fruit) and 39% (nasi lemak rice). The RMSE figures, in `docs/phase2_results.json`, show the same ranking. The guest-mix rate helps most for pancakes (0.47 kg against 0.53 kg with a fixed rate), because children raise pancake demand.

### Shopping list

The shopping list buys for the 80th percentile, a morning busier than four in five forecasts, and turns finished amounts into raw ingredients with the recipe card in `config.yaml`. The margin above the central forecast is set from the training days' out-of-fold predictions: how far actual amounts ran above the forecast on four days in five (4% to 8% depending on the dish). On the test days, the margin covered true demand on 68% (pancakes) to 86% (eggs and hash browns) of days, about 77% on average across dishes, and actual diners on 92% of days. Pancakes fall short because school holiday demand in the last week of the test period was higher than anything in the training year's margin. The first attempt used the spread of the forest's trees, which covered only 65% to 74% of days for dishes because it ignores day-to-day appetite. We changed the method after seeing that test coverage, so the test days have been looked at twice for this one setting; the figures above should be read with that in mind.

For the demo morning, Tuesday 24 November 2026, the forecast is 306 diners (291 actually came) and the shopping list includes 415 eggs, 16.7 kg of chicken sausages, 11.7 kg of frozen hash browns, 7.3 kg of rice, 128 croissants and 34.5 kg of whole fruit.

### Verdict

The forecast beats the baseline on the test days for diners, arrivals per slot and all eight dishes. Its accuracy is flattered by synthetic data generated from the same guest counts it uses, so Phase 5 will test what matters more, whether it reduces leftovers and stock-outs when the morning is replayed slot by slot.

## Phase 3: guest flow and live check-ins

This section shows that what a guest tells us on their phone reaches the kitchen board quickly and changes the forecast by a justified amount. The guest page has the three designed steps (breakfast plan, choose a time, confirmed), plus a thank-you screen for guests who reply "Not this time". Every result is simulated on fictional data.

An automated browser test (Playwright, with a 390 x 844 phone screen and the board at 1920 x 1080) booked two guests for room 1410, chose 08:00, accepted the "Switch to 09:30" suggestion and confirmed. The board's forecast outlines changed 2.9 seconds after the tap, within the 5-second refresh. A second phone then replied "Not this time" for two guests, and "Expected today" fell from 299 to 298 at the next refresh.

On the demo morning (Tuesday 24 November 2026) the forecast is 300 diners before any live check-ins. The crowd view marks 07:00 to 08:30 as Busy, 09:00 as Moderate, and 06:30, 09:30 and 10:00 as Quiet, so choosing 08:00 suggests 09:30. The design screen shows 09:00 as Busy; in the simulated data the Tuesday rush ends earlier, and we have not changed the data to match the screen.

A confirmation feeds the Random Forest through its check-in count, so it moves "Expected today" only as much as the evidence supports. A guest who confirms was already likely to eat breakfast (66% of in-house guests do on the demo morning), so one party of two usually changes the forecast by less than one diner. The visible change is in the arrival curve, where confirmed guests are placed in their chosen half hour. Twenty confirmed parties of two raise the forecast by much less than 40, which the tests check, because adding them on top would double count guests the forecast already expected. Each declined guest lowers the forecast by 0.66, the chance they would have come.

Because one party barely moves the total, a first test on a real phone looked as if nothing had happened, so each booking now also appears in the board's Alerts panel, newest first, such as "2 guests booked for 09:30" with the new expected total (and no room number). In the browser test the alert appeared 0.7 seconds after the guest tapped Confirm. The same test also found that a reply could be recorded as "Not this time" when the choice had not loaded; now only an explicit "Not this time" counts as a decline.

The 23 tests in `tests/test_guest_flow.py` check the Quiet, Moderate and Busy thresholds, that the crowd view adds two 15-minute slots per half hour, that slot forecasts add up to the expected total, that confirmed guests land in their half hour, that declines lower the forecast, that "Change my plans" replaces the room's earlier plan, that meal counts are capped at the party size, that room numbers must have 3 to 5 digits, that plans survive a restart and are deleted after checkout, that the file is ignored by git, that half hours which have ended cannot be chosen on the morning itself, that the QR link works on the local network and through a share link, and that booking alerts never show room numbers. All 129 tests in the project pass.

## Phase 4: camera tray check

This section will report how accurately the camera model judges tray levels from photos it has never seen. The test accuracy and confusion matrix are written to `docs/phase4_camera_results.json` and `docs/charts/phase4_confusion_matrix.png` by `notebooks/01_train_camera_model.ipynb` once the group's photos are in (at least 50 per level; see `docs/PHOTO_CHECKLIST.md`). **Status: waiting for photos, so no accuracy is reported yet.**

The photos are split 70% for training, 15% for validation (used only to pick the best training round) and 15% for testing, with each level's share kept in every part, so the test photos are never seen in training. Ultralytics' own automatic split (80% training, 20% validation) was not used, because it would leave no untouched test photos.

Before the photos exist, the pipeline was checked end to end with a throwaway model trained on 240 computer-drawn tray images. Its accuracy is not reported, because drawn trays say nothing about real ones. With it, an automated browser test on a 390 x 844 phone screen confirmed that "Check tray" opens the phone camera, a photo of a low tray returns "Low" with a confidence pill and "About 0.4 kg left of 2.5 kg", the kitchen board's egg card changes to Low within 5 seconds, "Wrong level? Fix it" saves the photo into the corrected level's folder, the manual buttons work on another station, and "Record leftovers" writes to the service log without changing the board.

One weakness showed up: a plain grey image, which is not a tray at all, was classified as Empty with 85% confidence. A confidence threshold only catches photos the model finds ambiguous, not photos of something else entirely, so runners still need to look at the result. We will check whether the model trained on real photos behaves the same way.

The 16 tests in `tests/test_camera.py` check the amount formula (pan capacity times 0, 0.15, 0.5 or 0.9), the wording against the design, that results below 60% confidence are not sent, that a missing model falls back to the manual buttons, that sure, manual and leftover results reach the board or the history correctly, that the log holds no guest data, that corrections are saved in the right folder, that the split keeps every level in each part with no overlap, and that the photo check flags shortfalls and copies.

## Phase 5: nowcast, refill engine and kitchen board

This section tests BuffetIQ's central claim: that guiding the kitchen during service, rather than only planning the night before, cuts leftover food without leaving trays empty. Every result is simulated on fictional data, from `python -m buffetiq.simulate` (run from `src`), with the raw output in `docs/phase5_results.json`.

### How the replay works

Each of the 65 test mornings (21 September to 24 November 2026) is replayed in 5-minute steps from 06:30 to 10:30, with guests arriving as they did in the synthetic data and eating each dish in proportion to their arrivals, up to that day's true demand. Every policy opens with one full pan of each dish. Food left on the buffet, held in reserve or still cooking at 10:30 counts as surplus, and a stock-out minute is a minute in which a dish's tray was empty while guests wanted it.

1. **Baseline chef rule.** The chef cooks the day's planned amount from the data (the same-weekday four-week average plus 15%) through the morning, following the usual arrival curve for that day type, and cooks one more batch whenever a tray is empty with nothing cooking.
2. **Forecast only.** The same, but the planned amount is the night-before forecast plus the 10% buffer, spread along the forecast arrival curve.
3. **Full BuffetIQ.** The nowcast and refill engine from `src/buffetiq/nowcast.py`, the same code that drives the live kitchen board. It sees only the arrivals the host logs and a camera reading of each tray every 15 minutes, given as Empty, Low, Half or Full and right 85% of the time (otherwise one level off), until the group's photos give a measured accuracy. Its calls are assumed to be followed, and hot dishes switch to cook-to-order when fewer than 12 guests per 15 minutes are expected for the rest of service.

### Results

| Policy | Surplus at close (kg a day) | Change | Cost of surplus (S$ a day) | Change | Stock-out minutes (a day, all dishes) | Change |
| --- | --- | --- | --- | --- | --- | --- |
| Baseline chef rule | 21.9 | | 119.6 | | 12.9 | |
| Forecast only | 17.0 | -22% | 95.5 | -20% | 8.9 | -4.0 |
| **Full BuffetIQ** | **17.6** | **-20%** | **93.6** | **-22%** | **5.7** | **-7.2** |
| BuffetIQ without cook-to-order | 18.3 | -17% | 96.4 | -19% | 10.1 | -2.8 |

![Surplus and stock-out minutes by policy](charts/phase5_policies.png)

Full BuffetIQ cuts surplus by 4.3 kg a day (20%) and the food cost of that surplus by S$26 a day (22%, about S$9,500 a year for this fictional hotel) compared with the baseline chef rule, and at the same time cuts the minutes a dish stands empty by 56%, from 12.9 to 5.7 a day. It therefore meets the bar set for this phase: less surplus without more stock-out minutes.

Three findings are less flattering and are reported as they came out:

1. **Forecast only leaves slightly less food than full BuffetIQ** (17.0 kg against 17.6 kg a day), because BuffetIQ's calls cook to cover expected demand until a batch is ready plus 45 minutes, keeping a reserve. Forecast only pays for its lower surplus with 56% more empty minutes (8.9 against 5.7). The live engine trades about 0.6 kg a day of food for about 3 fewer empty minutes.
2. **Eggs and croissants do not improve on stock-outs.** BuffetIQ leaves as many eggs as the baseline (3.8 kg a day) and its croissant stock-out minutes are slightly higher (0.3 against 0.1 a day). BuffetIQ also has more days with a brief empty tray for several dishes (for example 12 against 5 days for chicken sausages), although the minutes on those days are much shorter.
3. **The cook-to-order switch never triggered in the first replay because of a bug.** Expected arrivals in later slots were divided by the share of the morning left after each slot instead of after the current time, so the last 15 minutes looked as busy as 234 guests. The bug was fixed (a regression test now guards it) and the results above are from the corrected replay. With the switch working, it saves 0.7 kg a day and 4.4 stock-out minutes, so most of the gain comes from forecasting and refills.

| Dish | Surplus, baseline (kg) | Surplus, BuffetIQ (kg) | Stock-out min, baseline | Stock-out min, BuffetIQ | Cost, baseline (S$) | Cost, BuffetIQ (S$) |
| --- | --- | --- | --- | --- | --- | --- |
| Scrambled eggs | 3.77 | 3.78 | 1.1 | 0.3 | 18.87 | 18.90 |
| Chicken sausages | 2.69 | 2.14 | 1.0 | 0.5 | 20.21 | 16.07 |
| Hash browns | 1.89 | 1.33 | 2.5 | 1.2 | 7.55 | 5.32 |
| Pancakes | 1.23 | 0.66 | 1.5 | 0.8 | 5.52 | 2.95 |
| Mee goreng | 2.75 | 2.12 | 1.5 | 0.7 | 9.63 | 7.42 |
| Nasi lemak rice | 2.99 | 2.64 | 4.0 | 1.2 | 7.47 | 6.61 |
| Croissants | 2.60 | 1.75 | 0.1 | 0.3 | 31.22 | 20.99 |
| Cut fruit | 3.99 | 3.21 | 1.3 | 0.7 | 19.14 | 15.39 |

In the last hour, BuffetIQ flagged an average of 11.2 kg a day as likely surplus for a Treatsure offer. These flags are not subtracted from the surplus above, because the replay cannot know how much would actually sell.

### Sensitivity test: guests who accept a quieter half hour

This is a sensitivity test, not a prediction. It moves a share of the guests in each Busy half hour of the forecast to the nearest Quiet one and replays full BuffetIQ.

| Share of guests who accept | Surplus (kg a day) | Stock-out minutes (a day) | Cost (S$ a day) |
| --- | --- | --- | --- |
| 0% | 17.6 | 5.7 | 93.6 |
| 10% | 16.2 | 4.5 | 86.3 |
| 20% | 15.6 | 7.3 | 83.3 |
| 30% | 15.9 | 16.4 | 84.4 |

Up to about 10%, a flatter rush helps on both counts. Beyond that, the moved guests turn the quiet half hours into new peaks, and stock-out minutes rise sharply, because in this test the forecast curve does not learn where the guests went. In the live app, guests who choose a time on the guest page are placed in their half hour, so the real effect should sit between these figures, but this replay cannot show that.

### Changes worth trying

The 45-minute cover window, the 10% buffer and the cook-to-order threshold of 12 guests per 15 minutes were set before any results were seen and have not been tuned. A shorter cover window late in the morning, or a half batch for the last cook of the day, would probably close the gap with forecast only on surplus, but any such change should be chosen on training days and tested once on these 65 days, not tuned against them.

### The live kitchen board

The kitchen board now runs entirely on the engine, apart from the last voice answer (Phase 6). Started with `python app.py --at 08:40`, it replays the demo morning to 08:40 with simulated guests and camera checks. It then shows 223 diners so far, "Expected today 310, was 300", Moderate for the next 15 minutes, arrivals 5% ahead of forecast, chicken sausages Empty with "Cook 5 kg · Now · tray empty since 08:35", the other dishes on Hold with their reserves, pan timers, and the stop-out and cook-to-order alerts. "Log arrivals +5" raised the expected total from 310 to 315 at the next refresh, "Override a call" changed scrambled eggs to "Let it run down" with the chef's reason shown on the card, and "Check a tray" shows a QR code for the runner page.

The tests in `tests/test_nowcast.py` cover zero arrivals, the nowcast formula, refill rounding, the lead-time cut-off, the pan timer thresholds (3 hours 30 minutes and 4 hours), the slot arrivals bug, cook-to-order timing, calls being followed only once, stop-out alerts, overrides and discards, Treatsure flags only in the last hour, the camera error model, conservation of food in the replay, and the live board after a replay.
