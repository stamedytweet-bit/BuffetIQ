# Kickoff prompt for Claude Code

Put `CLAUDE.md` and the `design/` folder in the project folder first. Then paste everything below the line into Claude Code as your first message.

---

Read CLAUDE.md first and follow it throughout, then read `design/SCREENS.md` and view the eight screenshots in `design/screens/`. We are building the BuffetIQ prototype in nine phases (0 to 8). Start with Phase 0: ask your multiple-choice questions, then wait for my answers before writing code.

## How the parts work together

The purpose of BuffetIQ is to match breakfast supply to demand as the morning unfolds, where most tools only plan the night before or measure waste afterwards. The night before, the demand forecast predicts how many guests will eat, when they will arrive in 15-minute slots, and how many kilograms of each dish they will need, which also gives a shopping list. Guests then open the guest page from a QR code to confirm their plans and see which half hours are quiet, and their check-ins update the forecast. During service, the host logs arrivals and a runner photographs trays on a phone, where the camera model turns each photo into a fill level. The nowcast engine (a forecast revised with what has already happened this morning) combines these signals to issue refill calls that respect each dish's cooking lead time, together with 4-hour pan timer alerts, cook-to-order switch suggestions and a surplus flag for Treatsure in the last hour. Chefs read all of this on the kitchen board at the pass or ask for it by voice through Ask BuffetIQ, which reads from the same functions so its answers always match the board. Every action is logged, the day-end report summarises waste, stock-outs and cost, and nightly retraining feeds that day back into tomorrow's forecast.

## Phase 0: Setup, style and static screens

- Create the repository layout from CLAUDE.md, `requirements.txt`, `README.md`, `.gitignore` and `config.yaml` with eight fictional dishes and their stations: scrambled eggs, chicken sausages and hash browns (Hot station 1), mee goreng and nasi lemak rice (Hot station 2), pancakes (Live station), croissants (Bakery, counted in pieces) and cut fruit (Cold station). Give each dish a lead time in minutes, batch size, pan capacity, last-cook time, cost per kg in S$, halal and vegetarian flags, and spoken synonyms (such as "eggs" and "scrambled").
- Build `style.py` with both modes from the CLAUDE.md tokens, scoped to `.bq-kitchen` and `.bq-guest`.
- Build `app.py` with the pages from CLAUDE.md: Kitchen board at "/", Runner (Tray check and Ask BuffetIQ), Guest (navbar hidden), Day-end report, and About (which also holds the presenter controls added in Phase 8).
- Build every screen as a static version of its design, using the sample data shown on the screenshots kept in `src/buffetiq/ui/sample.py`. Later phases replace the sample data with live state screen by screen, so the look is right before any logic exists.
- Done when the app launches locally, every page matches its screenshot side by side, and the README explains how to run it locally and in Colab.

## Phase 1: Synthetic data

- Simulate a fictional 300-room city hotel in Singapore over 365 days, with breakfast from 06:30 to 10:30 in sixteen 15-minute slots.
- Columns: date, day of week, Singapore public holiday flag, school holiday flag, occupancy rate, rooms occupied, adults, children, breakfast-inclusive rooms, business guest share, group booking flag, guest check-ins, arrivals per slot, and for each dish the prepared, consumed and leftover amounts.
- Ground the share of breakfast-inclusive bookings in the city hotel from the Hotel Booking Demand dataset (Antonio, de Almeida and Nunes, 2019), where about 78% of bookings were bed and breakfast, with day-to-day variation.
- Build in realistic behaviour: business-heavy weekdays peak between 07:00 and 08:00, weekends between 08:30 and 09:30, children raise pancake demand, and about one day in fifteen has a surprise (such as a tour group arriving early, or rain keeping guests in longer).
- Simulate check-ins with a response rate between 0% and 40% so the models never depend on them.
- Set "prepared" with a typical chef rule (the historical average plus a 15% buffer) so that the baseline has realistic surplus.
- Write every assumption and number into `docs/ASSUMPTIONS.md`.
- Done when sanity tests pass (no negatives, arrivals sum to diners, leftover equals prepared minus consumed) and you show me a chart of weekday and weekend arrival curves.

## Phase 2: Demand forecast (the night before)

- Total diners: a Random Forest regressor with features for day of week, holiday flags, occupancy, adults, children, breakfast-inclusive rooms, business share, group flag and check-ins.
- Arrival curve: predict each slot's share of the morning and normalise to 1. If a simpler average profile by day type is about as accurate, use it and explain why.
- Dish demand: kg (or pieces) per diner for each dish, multiplied by predicted diners, plus a shopping list from a simple recipe card in `config.yaml`.
- Evaluation: split by date, training on the first 300 days and testing on the last 65, so the model never sees the future. The baseline is the average of the same weekday over the previous four weeks. Report MAE (mean absolute error), RMSE and MAPE for diners and for each dish, with a feature importance chart.
- Done when the model beats the baseline on the test days and the numbers are saved to `docs/EVIDENCE.md`. If it does not beat the baseline, tell me why.

## Phase 3: Guest flow (screens 05 to 07)

- Build the three steps exactly as designed: Breakfast plan (attending, room number, party size from 1 to 8, halal and vegetarian meal counts capped at the party size), Choose a time, and Confirmed.
- Crowd view: one row per 30-minute slot from 06:30 to 10:00, made by adding the two 15-minute forecast slots. Label each as Quiet (below 40% of the busiest half hour), Moderate (40% to 75%) or Busy (above 75%), always with the word beside the bar. When a guest selects a Busy slot, suggest the nearest Quiet slot with a one-tap "Switch to" button.
- The confirm button repeats the choice ("Confirm 09:00 for 2 guests"), and the confirmation screen shows the small-plate tip and a "Change my plans" button.
- Shared state: confirmed check-ins feed the diner model and shift the arrival curve towards the chosen slots.
- Keep the privacy line under the first button, and store dietary needs as counts, never names.
- Generate a QR code that opens the guest page directly, so that we can print it on a mock key-card sleeve.
- Done when a submission from a phone changes the kitchen board forecast within one refresh (5 seconds) and the three steps match their screenshots on a real phone.

## Phase 4: Camera tray check (screens 03 and 04)

- Dataset: we will photograph four containers holding real food or props at four fill levels, namely empty, low (under 25%), half (25% to 75%) and full (over 75%). Aim for at least 50 photos per class, with different angles, lighting and backgrounds, stored as `tray_photos/<class>/`. Ultralytics classification uses one folder per class with no label files, and splits the images 80/20 automatically when there is no train folder. Give us a short photo checklist before we start shooting.
- `notebooks/01_train_camera_model.ipynb` trains the smallest current Ultralytics classification model on the Colab GPU, saves the weights to `models/tray_cls.pt`, and writes the test accuracy and a confusion matrix image into `docs/`.
- `camera.py`: classify an image into a level with a confidence score, then estimate the amount as pan capacity multiplied by 0, 0.15, 0.5 or 0.9. If confidence is below 0.6, show the "Not sure about this one" state from SCREENS.md and send nothing to the board.
- Runner page: build Tray check and Tray result as designed, with dish chips for the chosen station, the result card with level, confidence and estimate, the "Kitchen board updated" confirmation, and the buttons "Check next tray", "Retake photo" and "Wrong level? Fix it". Add an end-of-service "Record leftovers" mode that writes to the history.
- Add a line on the About page explaining that a fixed camera in a real kitchen would check every one to two minutes, while the prototype checks on demand.
- Fallback: the manual tray buttons from CLAUDE.md, reached through "Camera not working? Set the level by hand".
- Done when test accuracy is reported on held-out photos and live classification works from a phone.

## Phase 5: Nowcast, refill engine and kitchen board (the hero feature, screen 01)

Nowcast during service:

N(t) = w(t) x A(t) / F(t) + (1 - w(t)) x N0, where w(t) = F(t)

A(t) is the number of diners logged by the host so far (through the "Log arrivals +5" button and a +1 or +10 option on the presenter controls), F(t) is the expected share of the morning's arrivals by time t from the forecast curve, and N0 is the pre-service forecast. If F(t) is below 0.05, use N0.

Refill call for dish d:

R_d(t) = max(0, (1 + b) x (N(t) - A(t)) x c_d - S_d(t) - P_d(t))

c_d is the expected amount per remaining diner (from the dish model, adjusted for time of morning), b is a safety buffer (default 10%), S_d is the stock from the camera or manual level, and P_d is any batch already cooking. Round up to the batch size, and only recommend cooking if the current time plus the lead time is before the dish's last-cook time. Otherwise show "Let it run down".

Other rules:
- 4-hour pan timer: the Singapore Food Agency advises that food held between 5°C and 60°C for more than four hours should not be served. Timestamp every batch when it goes out, show "Out since 08:10 · swap by 12:10" on its card, turn the line saffron at 3 hours 30 minutes and coral with "Swap now" at 4 hours, and log a "Discard" action as waste.
- Cook-to-order switch: when predicted remaining diners per 15 minutes falls below a threshold the chef sets (default 12), raise the saffron "Switch to cook-to-order" alert and change hot dish actions to "Cook to order".
- Treatsure flag: in the last 60 minutes, list dishes with more than 1 kg of predicted surplus as candidates for surplus sale.
- Chef override: "Override a call" opens a simple chooser (dish, new action, reason from a dropdown), and every override is logged.

Kitchen board: replace the sample data on screen 01 with live state, including the stat pills, dish cards with level, action and pan timer, the arrivals chart with forecast outlines and the current slot, the three newest alerts, and the last voice answer. Refresh every 5 seconds with `gr.Timer`. The board shows no replay slider or settings; those live in the presenter controls.

Simulation for `docs/EVIDENCE.md`: replay all 65 test days under three policies, namely (1) the baseline chef rule, (2) forecast only, and (3) full BuffetIQ. Report surplus kg at close, stock-out minutes per dish and food cost in S$, with the change for each. Add a sensitivity slider for the share of guests who accept a quieter slot (0% to 30%), presented as a sensitivity test rather than a prediction.

Tests: zero arrivals, refill rounding, the lead-time cut-off and timer thresholds.

Done when tests pass, the board matches screenshot 01 with live data, and policy 3 cuts surplus compared with policy 1 without adding stock-out minutes. If it does not, report it honestly and suggest changes.

## Phase 6: Ask BuffetIQ voice assistant (screen 02)

- Runner page: build Ask BuffetIQ as designed, with the question bubble, the answer card with "Same numbers as the board" and Replay, the scrolling "Try asking" chips, the large microphone button and "Type a question instead". On the kitchen board, "Hold to ask BuffetIQ" uses the laptop microphone, and the answer appears in the "Last voice answer" panel.
- Pipeline: faster-whisper transcribes the question; Gemini (model from `GEMINI_MODEL`) uses function calling with `get_refill_plan(dish)`, `get_stock(dish)`, `get_forecast(window)`, `get_timer(dish)` and `get_alerts()`; the answer is one or two short spoken-style sentences with rounded numbers in kg and minutes; gTTS plays it back and the text is shown too.
- The model may only answer from function results. If it cannot, it says "I don't have that. Please check the board."
- Use the dish synonyms from `config.yaml` so kitchen language works.
- Fallback: a rule-based intent parser that covers the same five functions, with the status pill reading "Basic answers".
- Write 20 scripted test questions with expected answers into `docs/EVIDENCE.md`, and report how many answers match the board and the median response time.
- Never send room numbers or guest data to Gemini, because free-tier data may be used to improve Google's products.
- Done when at least 18 of 20 answers match, and the fallback works with the key removed.

## Phase 7: History, day-end report and retraining (screen 08)

- Append every action (arrivals, tray checks, refills, discards, overrides and leftovers) to `data/service_log.csv`.
- Day-end report: build screen 08 from the log, with the four figure cards against a usual day, leftovers by dish with paired bars, "What happened today" drawn from the log, and "Forecast keeps improving".
- "Export NEA waste file (CSV)" downloads each day's food waste by dish in kilograms, ready to adapt to NEA's reporting template.
- "Retrain tonight" retrains the forecast models with the logged days, and the learning chart shows forecast error falling as more weeks are added.
- Done when a demo morning run end to end produces the report and retraining changes the next forecast.

## Phase 8: Integration, Colab and showcase mode

- `notebooks/run_in_colab.ipynb` clones our GitHub repo, installs requirements, loads Colab Secrets, downloads or trains the models, launches the app with `share=True`, and prints the link for each page plus a QR code for the guest page. Note in the notebook that Gradio share links last 72 hours and are public, so we launch on the day and never use real guest data.
- Presenter controls on the About page: "Load showcase morning" (a prepared fictional morning at 82% occupancy, with a tour group of 24 arriving at 07:45), reset, jump to a time, and a clock running at up to ten times normal speed.
- `docs/DEMO_SCRIPT.md`: the five-minute demo below, with what each presenter clicks and says, in our writing style.
- `docs/EVIDENCE.md`: every metric, chart and test result in one place for the slides.
- Add a checklist to the README for recording a three-minute backup video in case Wi-Fi or Colab fails.
- Done when a teammate who has never seen the code can run the notebook and complete the demo script.

## The showcase demo to build towards

1. The kitchen board is full screen on the TV. An assessor scans the QR code on a mock key-card sleeve, confirms breakfast for two at 09:00, sees that 09:00 is Busy, and taps "Switch to 09:30".
2. The kitchen board updates within five seconds: "Expected today" and the forecast outlines shift.
3. The presenter jumps the clock to 07:45 as the tour group of 24 arrives. The host taps "Log arrivals +5" a few times, the alert "Tour group of 24 arrived" appears, and "Expected today" rises from 268 to 286.
4. At 08:40 the egg card turns saffron with "Cook 4 kg". A presenter photographs the nearly empty egg tray on a phone, the result reads "Low, 91% sure", and the phone confirms "Kitchen board updated".
5. The chef asks aloud "How much egg should I cook?" and Ask BuffetIQ answers "Cook 4 kg of scrambled eggs now", the same number as the board.
6. The clock moves to 09:50: croissants show "Let it run down" because of their lead time, the cook-to-order alert appears, one dish gets a Treatsure flag, and a pan timer turns saffron.
7. The Day-end report compares today with a usual day and shows the 65-day simulation, labelled "Simulated on fictional data".

Start Phase 0 now, beginning with your questions.
