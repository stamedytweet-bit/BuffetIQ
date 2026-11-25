# BuffetIQ

BuffetIQ is an AI breakfast management prototype for hotels, built for the Ngee Ann Polytechnic AI showcase (leisure and hospitality). It forecasts breakfast demand the night before, lets guests share their plans and choose quieter times, checks buffet trays through a phone camera, revises demand during service, and tells chefs what to cook, when to stop and when to switch to cook-to-order. Every hotel, guest and number in it is fictional, and every result is simulated on fictional data.

The point of difference is timing. Tools such as Winnow Foresight plan quantities before service, while Winnow Vision, Orbisk and Leanpath measure waste after it is binned. BuffetIQ guides decisions during service and links them to what guests have told us.

## Status

| Phase | What it covers | State |
| --- | --- | --- |
| 0 | Repository, style tokens, static screens from the approved designs | Done |
| 1 | Synthetic data for a fictional 300-room Singapore hotel (frozen) | Done |
| 2 | Demand forecast for the night before | Done |
| 3 | Guest flow with live check-ins and the guest QR code | Done |
| 4 | Camera tray check (waiting for AI-generated training images) | Built |
| 5 | Nowcast, refill engine, live kitchen board and the 65-day replay | Done |
| 6 | Ask BuffetIQ voice assistant (Gemini run waiting for a key) | Built |
| 7 | Day-end report, history and retraining | Done |
| 8 | Colab notebook, showcase mode, demo script and backup video checklist | Done |

## Pages

The app is one Gradio program with five pages. The navigation bar is hidden on every page, so guests never see kitchen pages; the About page links to the others.

| Page | Path | Device | Look |
| --- | --- | --- | --- |
| Kitchen board | `/` | Laptop on a TV or projector at the pass, full screen | Dark |
| Runner phone (Tray check and Ask BuffetIQ) | `/runner` | Runner's phone | Dark |
| Guest page | `/guest` | Guest's phone, from the QR code | Light |
| Day-end report | `/report` | Manager's laptop | Light |
| About and presenter controls | `/about` | Presenter's laptop | Light |

## Run it locally (VS Code, CPU)

The app needs Python 3.11 or newer.

1. Open the folder in VS Code and create a virtual environment (an isolated set of Python packages for this project):

   ```bash
   python -m venv .venv
   ```

2. Activate it. On Windows use `.venv\Scripts\activate`, and on macOS or Linux:

   ```bash
   source .venv/bin/activate
   ```

3. Install the packages:

   ```bash
   pip install -r requirements.txt
   ```

4. Start the app:

   ```bash
   python app.py
   ```

5. Open http://127.0.0.1:7860 for the kitchen board, and add `/runner`, `/guest`, `/report` or `/about` for the other pages. Press F11 in the browser to put the board full screen on the TV.

To see the board in the middle of a service, start it replayed to a time of the demo morning (simulated guests and tray checks):

```bash
python app.py --at 08:40
```

To open the runner and guest pages on phones connected to the same Wi-Fi, start the app with `--host 0.0.0.0`, then open `http://<laptop IP address>:7860/runner` on the phone:

```bash
python app.py --host 0.0.0.0
```

Ask BuffetIQ works without a Gemini key, giving "Basic answers". For Gemini answers, create a free key at aistudio.google.com (Get API key), copy `.env.example` to `.env`, and fill in `GEMINI_API_KEY` and `GEMINI_MODEL` (copy the current free-tier Flash or Flash-Lite model ID from Google AI Studio). Git ignores `.env`, so the key never reaches GitHub. Restart the app after changing it.

Browsers allow the microphone only on secure links: it works on the laptop at `127.0.0.1`, on the Hugging Face Space and through a Colab share link, but not on a phone opening `http://192.168.x.x`, where the page offers typing instead.

## Try the guest page on a phone

1. Connect the phone to the same Wi-Fi as the laptop.
2. Start the app so that other devices can reach it:

   ```bash
   python app.py --host 0.0.0.0
   ```

3. On the laptop, open http://127.0.0.1:7860/about and click "Show the guest QR code". It shows the laptop's network address, such as `http://192.168.1.28:7860/guest`. If macOS asks whether to allow incoming connections, click Allow.
4. Scan the code with the phone's camera. The page opens without the kitchen pages, and a booking appears on the kitchen board within 5 seconds.

"Download sleeve insert (PNG)" saves an 85 x 55 mm card to print for the mock key-card sleeve. Some school or office Wi-Fi networks block phones from reaching laptops; a phone hotspot, the Hugging Face Space or the Colab share link avoids that.

## Run it online (Hugging Face Space)

The showcase copy runs on a Hugging Face Space, a hosted page that runs the same `app.py` as the laptop on Hugging Face's computers. Its address never changes, so the printed QR codes keep working, and it is a secure (https) link, so the phone microphone and camera work for every phone. Hosting runs on the free CPU Basic hardware (2 processors, 16 GB of memory); since July 2026 creating a Gradio Space on it needs a Hugging Face PRO account, which the project owner has.

Set it up once:

1. On huggingface.co, open Settings, then Access Tokens, and create a token with **Write** permission. Never paste it into code, chat or a commit.
2. In the GitHub repository, open Settings, then Secrets and variables, then Actions. Add a **secret** `HF_TOKEN` with the token, and a **variable** `HF_SPACE` with the Space name, such as `your-username/buffetiq`.
3. Publish: every push to `main` now publishes the Space through `.github/workflows/deploy-space.yml`, and the Actions tab has a **Run workflow** button. To publish from the laptop instead, add `HF_TOKEN=...` to the git-ignored `.env` file and run `python deploy/push_to_space.py --space your-username/buffetiq`. Either way, only files that git tracks are sent, so `.env` never leaves the laptop.
4. On the Space page, open Settings, then Variables and secrets. Add a **secret** `BUFFETIQ_PASSCODE` (the presenter passcode, such as three random words), a **secret** `GEMINI_API_KEY` and a **variable** `GEMINI_MODEL` (the current free-tier Flash or Flash-Lite model ID from Google AI Studio). Without the passcode, the presenter controls on the Space stay locked; without the Gemini settings, Ask BuffetIQ uses basic answers. From the laptop, `python deploy/push_to_space.py --space your-username/buffetiq --settings` copies `BUFFETIQ_PASSCODE` and `GEMINI_API_KEY` from `.env` into the Space's secrets and `GEMINI_MODEL` into its variables, without printing them.

The pages are then at `https://your-username-buffetiq.hf.space/` (kitchen board), `/runner`, `/guest`, `/report` and `/about`. On a Space the app opens the showcase morning by itself. Three things to know: the Space sleeps after a period with no visitors and takes a few minutes to wake, so open it about 10 minutes before the demo; bookings, service logs and retraining are wiped whenever the Space restarts, which is fine for a demo; and anyone with the link can open every page, so never enter real guest data. Only the About page's presenter controls are behind the passcode; the kitchen board and runner buttons stay open because the demo needs them.

## Run it in Google Colab

Open `notebooks/run_in_colab.ipynb` in Colab (File, then Open notebook, then the GitHub tab, then this repository and branch) and run the cells in order. The notebook clones the repository, installs the packages, reads `GEMINI_API_KEY` and `GEMINI_MODEL` from Colab Secrets (the key icon in the left bar), prepares the camera model, starts the app with the showcase morning, prints a link for each page and shows QR codes for the guest and runner pages. Gradio share links last 72 hours and anyone with the link can open them, so launch on the day and never enter real guest data.

## Showcase mode

```bash
python app.py --host 0.0.0.0 --showcase
```

This loads the prepared showcase morning: a fictional Tuesday 24 November at 82% occupancy, with an unannounced tour group of 24 arriving at 07:45. The About page (`/about`) holds the presenter controls, locked behind the passcode in `BUFFETIQ_PASSCODE` when one is set (always on the Space; open on the laptop if it is left empty). Each browser unlocks separately, and five wrong tries lock the box for a minute. The controls are: **Load showcase morning**, **Reset to 06:15**, **Jump to** a time, the clock speed (paused, 1x, 2x, 5x or 10x), and **Log arrivals +1** or **+10**. Simulated guests arrive and a simulated runner checks every tray every 15 minutes, while real taps, photos and questions are added on top. The kitchen board has its own **Start breakfast** button, which opens service at 06:30 and runs the clock in real time, then becomes **Restart** (tap twice to go back to 06:15), and **+1**, **+2** and **+5** buttons for logging diners. After **Start breakfast** the clock runs at 5 times real speed (06:30 to 10:30 in 48 minutes) with simulated guests and tray checks, and logged diners, photos and the chef's actions are added on top. Tapping a dish card opens **Top up or change a call** with that dish picked: **Tray topped up** fills the pan at once (a batch that was cooking counts as brought out), and the other actions override the call. Anyone with the board's link can use these, so share it only with the team. The five-minute demo is in `docs/DEMO_SCRIPT.md`.

## Run the tests

```bash
python -m pytest -q
```

## Project layout

```
app.py                 builds the five pages and launches Gradio
config.yaml            hotel, service hours, rules and the eight dishes
design/                approved screens (reference only, never served)
src/buffetiq/style.py  colour tokens for both modes, icons, CSS and copy helpers
src/buffetiq/state.py  shared state for all pages, with a lock
src/buffetiq/ui/       one module per page, plus sample.py with the screenshot data
tests/                 pytest checks
docs/                  assumptions, evidence and the demo script
deploy/                publishing to the Hugging Face Space
```

## Backup video if Wi-Fi, the Space or Colab fails

Record a three-minute screen video a few days before the showcase, so the demo can still be shown if the network fails. Link it here once it is uploaded: **Backup video: (add the link)**.

1. Start the app on the laptop with `python app.py --showcase` and close other apps and notifications.
2. On a Mac, press Cmd, Shift and 5 and choose "Record Entire Screen" with the microphone on, so you can narrate.
3. Follow `docs/DEMO_SCRIPT.md`, shortened: the guest booking at 08:00 switched to 09:30 (30 seconds), the board alert (15 seconds), jump to 08:00 and the tour group alert (30 seconds), jump to 08:40, the pancake tray photo and "Cook 1.5 kg" (30 seconds), Ask BuffetIQ on the runner page (20 seconds), jump to 09:50 for cook-to-order and Treatsure (25 seconds), and the day-end report with the 65-day panel (30 seconds).
4. Use the browser window at 1920 x 1080 for the board, and a phone-sized window (or the phone, mirrored) for the guest and runner pages.
5. Say "simulated on fictional data" when showing results, as on screen.
6. Watch it back once, trim the start and end, and save it as MP4 under 3 minutes.
7. Keep one copy on the laptop's desktop and one on a USB drive or Google Drive, and test that it plays offline.

## Regenerate the synthetic data

The fictional year of breakfasts is already in `data/synthetic_breakfast.csv` and is frozen (see `docs/EVIDENCE.md`). To check that the generator still reproduces it, run this from the `src` folder:

```bash
python -m buffetiq.data_gen
```

The printed SHA-256 checksum must match the one in `docs/EVIDENCE.md`.

## Evaluate the forecast

From the `src` folder:

```bash
python -m buffetiq.forecast
```

It trains on the first 300 days, tests on the last 65, prints the errors against the baseline, and redraws the charts in `docs/charts/`. The same steps are in `notebooks/02_evaluate_forecast.ipynb`, which also runs in Colab.

## Train the camera model

1. Make the training images in the Gemini app with `docs/GENERATED_PHOTOS.md`: eight 2 by 2 grids saved in `tray_photos/grids/` (such as `grid_low_1.png`) and four demo cards in `tray_photos/demo_cards/`. Real phone photos, taken with `docs/PHOTO_CHECKLIST.md`, can go straight into the level folders.
2. From the `src` folder, cut the grids into photos, look through each level folder, then check them:

   ```bash
   python -m buffetiq.camera grids
   python -m buffetiq.camera check
   ```

3. Train, either in Colab with `notebooks/01_train_camera_model.ipynb` (faster, on a GPU) or on the laptop:

   ```bash
   python -m buffetiq.camera train
   ```

   This saves `models/tray_cls.pt`, writes the test accuracy and confusion matrix into `docs/`, and scores the four demo cards, which the model never trains on. Restart the app to use it, and commit `models/tray_cls.pt` so the Hugging Face Space uses it too.

Until then, `python -m buffetiq.camera standin` trains a stand-in model on computer-drawn trays so the runner page can be tried; the page labels its results as coming from a test model.

## Replay the 65 test days

From the `src` folder:

```bash
python -m buffetiq.simulate
```

It replays every test morning under the baseline chef rule, forecast only and full BuffetIQ, prints surplus, cost and stock-out minutes, and redraws `docs/charts/phase5_policies.png`.

## Evaluate Ask BuffetIQ

From the `src` folder:

```bash
python -m buffetiq.assistant_eval
```

It asks 20 scripted questions on the demo morning at 08:40, typed and spoken (computer voice), with basic answers and, if a key is set, with Gemini, and reports how many match the board and the median response time. To add your own voice, record questions as `data/voice_tests/q01.m4a` and so on, numbered as in `src/buffetiq/assistant_eval.py`.
