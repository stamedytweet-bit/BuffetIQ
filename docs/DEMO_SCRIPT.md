# Demo script

This script runs the five-minute BuffetIQ showcase demo with one presenter, a laptop connected to a TV, the presenter's phone and an assessor's phone. It shows the product's point of difference: BuffetIQ guides the kitchen during service, using what guests tell it and what has already happened this morning, where most tools only plan the night before or weigh waste afterwards. The numbers below come from a rehearsal of the prepared showcase morning on 22 November 2026; small differences on the day are normal, because guest bookings and taps change them. Everything shown is fictional data.

## Set up before the assessors arrive (10 minutes)

1. Start the app, either in Colab with `notebooks/run_in_colab.ipynb` (cell 4 loads the showcase morning and prints the links) or on the laptop with `python app.py --host 0.0.0.0 --showcase`.
2. On the laptop, open the kitchen board (`/`) on the TV and press F11 for full screen. Open the About page (`/about`) in a second window on the laptop screen for the presenter controls.
3. On your phone, open the runner page (`/runner`) from the QR code in the notebook. Over a Colab share link the microphone works; on the laptop's Wi-Fi address it does not, so type questions there instead.
4. Put the printed key-card sleeve (guest QR code) on the table, and have a small foil tray with a few pieces of food or props ready to photograph as a nearly empty pancake tray.
5. On the About page, click **Load showcase morning**. The status line should read "Showcase morning · Tuesday 24 November · clock 06:15 · Paused · 0 diners so far · expected 277".

## The demo (5 minutes)

### 1. A guest plans breakfast (0:00 to 0:45)

**Do:** Hand the assessor the key-card sleeve and ask them to scan it. On their phone they leave **Yes**, enter any room number such as 1204, keep 2 guests, tap **Choose a time**, pick **08:00** and see it marked **Busy**, then tap **Switch to 09:30** and **Confirm 09:30 for 2 guests**.

**Say:** "Guests share their plans the night before or on the morning itself. The page shows how busy each half hour usually is, from tomorrow's forecast, and nudges guests from a busy time to a quiet one. It asks only for a room number and counts of halal and vegetarian meals, never names."

### 2. The kitchen board reacts (0:45 to 1:15)

**Do:** Point at the TV. Within 5 seconds the Alerts panel shows "2 guests booked for 09:30" and the dashed forecast outlines shift towards 09:30.

**Say:** "That booking is now part of the forecast. One party barely changes the total of 277 guests expected, which is honest: most guests in the hotel eat breakfast anyway. What changes is when the kitchen expects them."

### 3. A tour group nobody booked (1:15 to 2:00)

**Do:** On the About page, set **Jump to** to **08:00** and click **Jump**. On the board, tap **Log arrivals +5** once to show how the host logs guests at the door.

**Say:** "It is now just after 08:00, and an unannounced tour group of 24 arrived at 07:45. Nothing in last night's bookings knew about them. BuffetIQ's nowcast, a forecast revised with what has already happened this morning, sees more diners than expected and raises today's total." Point at the alert **"Tour group of 24 arrived at 07:45 · Expected diners raised from 277 to 306"** and the **Expected today** pill, now about 311 with "was 277", and **Next 15 minutes: Busy**.

### 4. A tray check by phone (2:00 to 2:50)

**Do:** On the About page, jump to **08:40**. On your phone, in **Tray check**, tap **Change station** once (Live station, Pancakes), tap **Check tray** and photograph the nearly empty tray. The phone shows **Low** with how sure it is, and "Kitchen board updated · Pancakes: tray low". If the result is wrong or unsure, tap **Wrong level? Fix it** and choose **Low**, which is the backup for a real kitchen too.

**Say:** "A runner photographs a tray instead of weighing it. A small image model judges the level, and only a sure result reaches the board." Point at the pancake card on the TV, which now reads **Low · Cook 1.5 kg · Now · ready in 6 min** in saffron.

### 5. Ask BuffetIQ (2:50 to 3:30)

**Do:** On the phone, tap **Ask BuffetIQ** at the bottom, hold the yellow button and say "How many pancakes should I cook?", then let go. If the microphone is not available, tap **Type a question instead**.

**Say:** "Cooks have their hands full, so they ask aloud." The phone answers and speaks **"Cook 1.5 kg of pancakes now. Ready in 6 minutes."**, the same number as the board, and the board's **Last voice answer** panel shows it. "It can only answer from the board's own numbers. If it invents a number, BuffetIQ throws that answer away." If time allows, tap the chip **Which dishes have gluten?** to show allergen answers.

### 6. The end of service (3:30 to 4:15)

**Do:** On the About page, jump to **09:50**.

**Say:** "Fewer than 12 guests per 15 minutes are expected now, so the hot dishes switch to **Cook to order**: small portions as guests ask, instead of full pans that end up in the bin." Point at the Treatsure alerts, such as **Offer cut fruit on Treatsure · About 3.1 kg is likely to be left at close**: "In the last hour, BuffetIQ flags likely surplus to sell through Treatsure." Point at a card footer: "Every pan has a 4-hour timer from the Singapore Food Agency's rule; it turns saffron at three and a half hours and coral at four. This morning every pan was refreshed by a new batch, so none got close."

### 7. The day-end report (4:15 to 5:00)

**Do:** Open the Day-end report (`/report`) on the laptop.

**Say:** "After service, the manager sees today against the same morning run the usual way." In the rehearsal, this morning left **11.7 kg** of food against **12.6 kg** the usual way and wasted **S$59** against **S$76**, with more empty-tray minutes (24 against 13, mostly hash browns during the tour group rush). Point at **Across 65 simulated days**: "One morning can go either way. Across 65 simulated mornings, BuffetIQ leaves half as much food, 11.0 kg a day against 21.9 kg, and dishes stand empty 6.9 minutes a day against 12.9. All of this is simulated on fictional data." Finish with **Export NEA waste file (CSV)** and **Retrain tonight**: "Every service is logged and retrains the forecast overnight, and the waste file is ready for NEA reporting."

## If something goes wrong

* **The board does not update:** wait 5 seconds (it refreshes on a timer), then press the browser's reload key.
* **The camera result is wrong:** use **Wrong level? Fix it**; this is the designed fallback.
* **No microphone or no internet for speech:** type the question; answers appear as text.
* **The morning is in a strange state:** click **Reset to 06:15** and **Load showcase morning**, then jump to the step you need.
* **Wi-Fi or Colab fails:** play the backup video (see the README).
