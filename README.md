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
| 4 | Camera tray check (waiting for the group's photos to train the real model) | Built |
| 5 | Nowcast, refill engine, live kitchen board and the 65-day replay | Done |
| 6 | Ask BuffetIQ voice assistant (Gemini run waiting for a key) | Built |
| 7 | Day-end report, history and retraining | Next |
| 8 | Colab and showcase mode | Planned |

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

Browsers allow the microphone only on secure links: it works on the laptop at `127.0.0.1` and through a Colab share link, but not on a phone opening `http://192.168.x.x`, where the page offers typing instead.

## Try the guest page on a phone

1. Connect the phone to the same Wi-Fi as the laptop.
2. Start the app so that other devices can reach it:

   ```bash
   python app.py --host 0.0.0.0
   ```

3. On the laptop, open http://127.0.0.1:7860/about and click "Show the guest QR code". It shows the laptop's network address, such as `http://192.168.1.28:7860/guest`. If macOS asks whether to allow incoming connections, click Allow.
4. Scan the code with the phone's camera. The page opens without the kitchen pages, and a booking appears on the kitchen board within 5 seconds.

"Download sleeve insert (PNG)" saves an 85 x 55 mm card to print for the mock key-card sleeve. Some school or office Wi-Fi networks block phones from reaching laptops; a phone hotspot or the Colab share link avoids that.

## Run it in Google Colab

Phase 8 adds `notebooks/run_in_colab.ipynb`, which does all of this in one go. Until then, create a new Colab notebook and run these cells in order.

```python
!git clone https://github.com/stamedytweet-bit/BuffetIQ.git
%cd BuffetIQ
!pip install -q -r requirements.txt
```

```python
!python app.py --share
```

Colab prints a public link ending in `gradio.live`. Add `/runner`, `/guest`, `/report` or `/about` to it for the other pages. Gradio share links last 72 hours and anyone with the link can open them, so launch on the day and never enter real guest data.

From Phase 6, add `GEMINI_API_KEY` and `GEMINI_MODEL` under Colab Secrets (the key icon in the left bar) rather than typing them into a cell.

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
```

## Backup if Wi-Fi or Colab fails

Phase 8 adds a checklist for recording a three-minute backup video and a link to it here.

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

1. Take the tray photos following `docs/PHOTO_CHECKLIST.md` and put them in `tray_photos/empty`, `low`, `half` and `full`.
2. From the `src` folder, check them:

   ```bash
   python -m buffetiq.camera check
   ```

3. Train, either in Colab with `notebooks/01_train_camera_model.ipynb` (faster, on a GPU) or on the laptop:

   ```bash
   python -m buffetiq.camera train
   ```

   This saves `models/tray_cls.pt` and writes the test accuracy and confusion matrix into `docs/`. Restart the app to use it.

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
