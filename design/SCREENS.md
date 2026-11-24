# BuffetIQ screen designs

This folder holds the approved interface designs so that the Gradio app can be rebuilt to look and behave like them. Each screen has a screenshot in `screens/` and a static HTML snapshot in `html/` whose inline styles give the exact sizes, spacing and colours. The HTML snapshots are references only: rebuild each screen in Gradio with `style.py`, and never serve these files from the app. Colour tokens and the rules that apply to every screen live in `CLAUDE.md`; this file describes what each screen contains, how it behaves, and how it maps to Gradio.

All names, numbers and times on the screens are fictional sample data for Tuesday 24 November (kitchen) and Wednesday 25 November (guest). Hotel and restaurant names are the placeholders `[HOTEL NAME]`, `[RESTAURANT NAME]` and `[LEVEL]` until the group chooses them.

## Who uses which screen

| Screen | File | Mode | Device | Person |
| --- | --- | --- | --- | --- |
| Kitchen board | 01-kitchen-board | Dark | Laptop on a TV or projector at the pass, 1920 x 1080 | Head chef and line cooks, read from 2 to 3 metres |
| Ask BuffetIQ | 02-voice-assistant | Dark | Runner's phone, 390 x 844 | Chef or runner with busy hands |
| Tray check | 03-tray-check | Dark | Runner's phone | Runner walking the buffet line |
| Tray result | 04-tray-result | Dark | Runner's phone | Runner |
| Breakfast plan | 05-guest-plan | Light | Guest's phone, from the QR code | Hotel guest the night before |
| Choose a time | 06-guest-times | Light | Guest's phone | Hotel guest |
| Confirmed | 07-guest-confirmed | Light | Guest's phone | Hotel guest |
| Day-end report | 08-day-end-report | Light | Manager's laptop, fluid width, works down to a phone | F&B manager after service |

## The device decision for the kitchen

During a breakfast rush, cooks have wet, greasy or gloved hands, so the kitchen board is designed to be read rather than touched. It runs full screen on the laptop connected to a TV or projector at the pass (where finished food leaves the kitchen). Questions go through voice, and tray checks go through a runner's phone. The four large buttons along the bottom are the backup for the few moments when someone does need to touch the screen.

## 01 Kitchen board

Layout: a header row, a 4 x 2 grid of dish cards on the left, a 460px right rail, and a strip of four buttons along the bottom. The board never scrolls and must fit 1920 x 1080; on a 1366 x 768 laptop everything scales down together, never by dropping to fewer columns.

- Header: "BuffetIQ" in brand teal, a subtitle line with the date, service hours and "Fictional data", a large clock (80px), and three stat pills: "Diners so far", "Expected today" with the earlier figure as "was 268", and "Next 15 minutes" showing Quiet, Moderate or Busy with the expected count. The busy pill gets a saffron border and saffron text.
- Dish card (one per dish, always in the same order so cooks build muscle memory, never re-sorted by urgency):
  - Name (26px bold) and station label (Hot station 1, Live station, Bakery, Cold station).
  - Level bar (14px tall) with the level word and an icon below it: Full or Half in green with a tick-circle, Low in saffron with a warning triangle, Empty in coral with a cross-circle, plus the amount as "0.4 of 2.5 kg" or "18 of 40 pieces".
  - Action block that fills the rest of the card: the instruction in 40px bold ("Cook 4 kg", "Bake 24", "Hold", "Let it run down", "Cook to order") with one supporting line ("Now · ready in 8 min", "Next check 08:55", "Now · last bake 09:50"). Saffron fill for cook now, coral fill when the tray is already empty, raised dark fill for hold.
  - Card border matches the most urgent state (saffron, coral, or the normal dark border).
  - Footer line with a clock icon: "Out since 08:10 · swap by 12:10" for the 4-hour pan rule. The footer turns saffron with a warning icon at 3 hours 30 minutes and coral at 4 hours, with the words "Swap now".
- Right rail, top: "Arrivals" with one bar per 15-minute slot from 06:30 to 10:30. Actual arrivals are solid green, the current slot is saffron, the forecast is a dashed outline behind each bar, and the header states the finding, such as "12% ahead of forecast". Axis labels show 06:30, the current time, and 10:30, with a legend for Actual and Forecast.
- Right rail, middle: "Alerts" with at most three, newest first, each with a round icon (coral "!" for a stock-out or pan at 4 hours, teal "i" for information, saffron "›" for a suggestion), a bold title and one short line. Older alerts move to the log, not to a scrolling list.
- Right rail, bottom: "Last voice answer" with the question in quotes and the answer in 22px bold, so the whole kitchen hears and sees the same number.
- Bottom strip, four buttons at 96px tall with icons: "Log arrivals +5", "Check a tray", "Hold to ask BuffetIQ" (the only saffron button), and "Override a call".
  - Change agreed on 24 November 2026: the strip now has five 96px slots. "Start breakfast" (runs the clock live from 08:00, then reads "Restart", which needs a second tap and goes back to 06:15) comes first, and "Log arrivals" splits into +1, +2 and +5 buttons.
- Updates: refresh from shared state every 5 seconds with `gr.Timer`, with no animation apart from the change itself.

Gradio mapping: one `gr.HTML` per region (header, dish grid, arrivals, alerts, last answer), each rendered by a Python function from shared state, and native `gr.Button`s for the strip, styled through `elem_classes`.

## 02 Ask BuffetIQ (voice)

- Header: "Ask BuffetIQ", the time, and a "Board connected" status pill (it reads "Basic answers" when the rule-based fallback is answering, and "Board offline" if shared state cannot be reached).
- The last question as a right-aligned bubble with "You said · 08:40".
- Answer card with a saffron border: the instruction in 28px bold ("Cook 4 kg of scrambled eggs now."), one supporting sentence, a "Same numbers as the board" tick line, and a "Replay" button for the spoken answer.
- "Try asking" chips in one horizontally scrolling row: "What is running low?", "Any pans near 4 hours?", "When do I stop croissants?". Tapping a chip asks that question.
- At the bottom, in the thumb zone, a 132px round saffron microphone button and a "Type a question instead" link.

Gradio mapping: `gr.Audio(sources=["microphone"])` styled as the round button. Gradio's recorder starts and stops on a tap, so if true press-and-hold is not possible, label it "Tap to talk" and say so. Chips are `gr.Button`s in a `gr.Row`, and the typed input is a `gr.Textbox` that is hidden until the link is tapped.

## 03 Tray check and 04 Tray result

- Tray check: title, station and time, a "Change station" button, then "Which tray?" with up to three dish chips for the current station (a radio group, selected chip filled in brand teal). Below that sits a viewfinder with corner brackets and the hint "Hold the phone above the tray · Whole tray in frame · flash off", a full-width saffron "Check tray" button with a camera icon, and the fallback link "Camera not working? Set the level by hand".
- Tray result: a back link, the dish and time, the photo, then a result card with the level word in 48px with its icon, a confidence pill ("91% sure"), the estimate ("About 0.4 kg left of 2.5 kg"), and a four-part scale (Empty, Low, Half, Full) with the detected part highlighted. A confirmation row with a green tick says "Kitchen board updated" and repeats the new call, such as "Scrambled eggs: cook 4 kg now". Buttons: "Check next tray" (primary, saffron), "Retake photo" and "Wrong level? Fix it".
- Low confidence (below 0.6): replace the result card with "Not sure about this one" in saffron, show the closest guess as text only, and make "Retake photo" the primary button. Nothing is sent to the board.
  - Change agreed on 24 November 2026, for messy trays: the card names the two closest levels without a percentage, and two buttons ("Mark as Half", "Mark as Low") let the runner pick one. The pick goes to the board as a manual reading and the photo is saved in that level's folder for retraining. "Another level" opens all four manual levels.

Gradio mapping: `gr.Radio` for dishes, `gr.Image(sources=["upload", "webcam"])` (on a phone, upload opens the camera), and `gr.HTML` for the result card.

## 05 to 07 Guest flow

The guest flow should feel like a calm, premium hotel page rather than an operations tool. It has three steps, with "Step 1 of 2" and "Step 2 of 2" pills on the first two, and no navigation bar.

- 05 Breakfast plan: `[HOTEL NAME]` in Fraunces, "Breakfast tomorrow" (32px Fraunces), the date, hours and restaurant, and one sentence on why we ask. A white card holds:
  - "Will you join us?" with Yes and "Not this time" as a two-button toggle (selected is filled teal).
  - "Room number" as a numeric text field.
  - "How many guests?" as a stepper from 1 to 8 with 44px round buttons.
  - "Dietary needs (optional)" with halal and vegetarian meal steppers, each capped at the party size.
  - Below the card: a full-width teal "Choose a time" button, then the privacy line "We use your room number only to plan how much food to prepare, and delete it when you check out."
- 06 Choose a time: a back link, "When would you like to come?" and "How busy each half hour usually is, based on tomorrow's bookings." One row per 30-minute slot from 06:30 to 10:00 (a radio group), each with the time, a bar, and the word Quiet, Moderate or Busy. The selected row has a teal border and a light teal fill. When a Busy slot is selected, a saffron tip card appears: "09:30 is usually quiet · Shorter queues and dishes straight from the kitchen" with a "Switch to 09:30" button. The confirm button repeats the choice, such as "Confirm 09:00 for 2 guests".
- 07 Confirmed: a teal circle with a tick, "You're all set", a details card with icons (When, Guests · Room, Where), a saffron tip card "A small plate, as often as you like" explaining that the buffet is topped up all morning, one quiet line that planning helps the kitchen cook fresh and waste less food, and a secondary "Change my plans" button.
- Tone: welcoming and practical. Waste is mentioned once, quietly, on the last screen, and never as guilt.

Gradio mapping: a separate page through `Blocks.route()` so that guests never see the kitchen tabs, with the navbar hidden through `gr.Navbar(visible=False)`. The three steps are `gr.Column`s whose visibility is switched, using `gr.Radio` for slots and `gr.Number` or custom steppers built from two `gr.Button`s and a `gr.HTML` count.

## 08 Day-end report

- Header: "BuffetIQ", "Day-end report", a date and service line ending "Example data, simulated", and two buttons: "Export NEA waste file (CSV)" (secondary, download icon) and "Retrain tonight" (primary teal).
- Four figure cards in a responsive grid: "Food left over" 18.6 kg with "55% less than a usual day (41.2 kg)", "Cost of food wasted" S$96 against S$214, "Minutes a dish was empty" 6 against 9 with which dish and when, and "Guests served" 293 with the forecast and revision.
- "Leftovers by dish": a table of prepared, eaten and left kilograms, with a final column of paired bars (today in teal, usual day in beige) and a bold total row.
- "What happened today": up to four events, each a bold title with one line, such as the early tour group, the six-minute stock-out, the Treatsure offer and chef overrides.
- "Forecast keeps improving": a four-bar chart of average forecast error by week of use, with the latest week in teal and earlier weeks in light teal.
- Footer note that the data is simulated and what the NEA file contains.

Gradio mapping: `gr.HTML` for the cards, table and event list, `gr.DownloadButton` for the CSV, and a Plotly chart or `gr.HTML` bars for the learning curve, styled with the light tokens.
