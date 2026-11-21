# BuffetIQ

BuffetIQ is an AI breakfast management prototype for hotels, built for the Ngee Ann Polytechnic AI showcase (leisure and hospitality). It forecasts breakfast demand the night before, lets guests share their plans and choose quieter times, checks buffet trays through a phone camera, revises demand during service, and tells chefs what to cook, when to stop and when to switch to cook-to-order. Every hotel, guest and number in it is fictional, and every result is simulated on fictional data.

The point of difference is timing. Tools such as Winnow Foresight plan quantities before service, while Winnow Vision, Orbisk and Leanpath measure waste after it is binned. BuffetIQ guides decisions during service and links them to what guests have told us.

## Status

| Phase | What it covers | State |
| --- | --- | --- |
| 0 | Repository, style tokens, static screens from the approved designs | Done |
| 1 | Synthetic data for a fictional 300-room Singapore hotel (frozen) | Done |
| 2 | Demand forecast for the night before | Next |
| 3 to 8 | Guest flow, camera, nowcast and board, voice, report, showcase | Planned |

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

To open the runner and guest pages on phones connected to the same Wi-Fi, start the app with `--host 0.0.0.0`, then open `http://<laptop IP address>:7860/runner` on the phone:

```bash
python app.py --host 0.0.0.0
```

The Gemini key is not needed until Phase 6. When it is, copy `.env.example` to `.env` and fill in `GEMINI_API_KEY` and `GEMINI_MODEL` (copy the current free-tier Flash or Flash-Lite model ID from Google AI Studio). Git ignores `.env`, so the key never reaches GitHub.

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
