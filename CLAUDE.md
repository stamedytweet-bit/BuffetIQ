# BuffetIQ prototype: rules for Claude Code

## What we are building

BuffetIQ is an AI breakfast management prototype for hotels, built by our team for the Ngee Ann Polytechnic AI showcase (leisure and hospitality sector). It forecasts breakfast demand the night before, lets guests share their plans and choose quieter times, checks buffet trays through a phone camera, recalculates demand during service, and tells chefs what to cook, when to stop and when to switch to cook-to-order, both on screen and by voice. Every service is recorded so that the forecast improves overnight.

The unique selling point to protect in every design choice is timing. Competitors such as Winnow Foresight plan quantities before service, while Winnow Vision, Orbisk and Leanpath measure waste after it is binned. BuffetIQ guides decisions during service and links them to what guests have told us.

The interface is already designed and approved. The screens are in `design/` (see "Screen designs" below), and the app must match them.

## Hard constraints

- Free tools only. No paid APIs and no billing accounts. One agreed exception: the showcase is hosted on a Hugging Face Space under the owner's existing PRO account (free CPU Basic hardware).
- Hardware is one laptop, a TV or projector, and the team's phones. There are no scales, sensors or fixed cameras, so phone cameras, the laptop webcam and the laptop microphone are the only inputs.
- The same code must run in three places: locally in VS Code on CPU for development, on a Hugging Face Space (CPU) for the showcase, and in Google Colab Pro on GPU for training and as a spare.
- All data is synthetic. Label it "Fictional data" wherever it appears on screen, and label every result "Simulated on fictional data".
- Secrets: read `GEMINI_API_KEY` from an environment variable locally, from the Space's secrets on Hugging Face, and from Colab Secrets in Colab. Never write a key into code, notebooks, logs or commits, and keep `.env` in `.gitignore`.
- Model names: read the Gemini model ID from `GEMINI_MODEL`. Do not hardcode one, because Google renames and retires models often. Tell us to copy the current free-tier Flash or Flash-Lite model ID from Google AI Studio.
- Privacy: never send personal data to an external API. Only dish names, quantities and times may leave the machine. Room numbers stay local and are deleted after checkout in the simulation.
- Every AI feature must still work, in a simpler form, when its model, key, microphone or internet connection is missing (see Fallbacks).

## Tech stack

- Python 3.11 with pandas, numpy, scikit-learn (Random Forest or HistGradientBoosting) and plotly
- Gradio for every interface, as one app with separate pages made with `Blocks.route()`, refreshed with `gr.Timer`, and launched with `share=True` in Colab. Pin the Gradio version in `requirements.txt`. From Gradio 6, `theme`, `css` and `head` are passed to `launch()` rather than `gr.Blocks()`, so check the installed version's docs before writing them.
- Ultralytics YOLO classification (the smallest current `-cls` model) for tray fill levels
- faster-whisper (base or small) for speech to text, running locally
- Gemini API free tier through the `google-genai` SDK, with function calling, for the chef assistant
- gTTS for text to speech, `qrcode` for the guest page QR code
- pytest for tests

## Repository layout

```
buffetiq/
  CLAUDE.md
  README.md
  requirements.txt
  config.yaml              # dishes, stations, lead times, batch sizes, last-cook times, pan capacities, costs, synonyms
  design/                  # approved screens: SCREENS.md, screens/*.png, html/*.html (reference only)
  data/                    # generated CSVs and service logs (git-ignored except small samples)
  tray_photos/             # empty/, low/, half/, full/ (our own phone photos)
  models/                  # trained weights (git-ignored)
  src/buffetiq/
    data_gen.py
    forecast.py
    nowcast.py
    camera.py
    assistant.py
    reports.py
    state.py               # shared state for all pages, with a lock
    style.py               # tokens for both modes, CSS and copy helpers
    ui/
      kitchen.py           # page "/" (kitchen board)
      runner.py            # tray check and Ask BuffetIQ for the runner's phone
      guest.py             # guest flow, opened from the QR code
      report.py            # day-end report
  app.py                   # builds the pages and launches
  notebooks/
    01_train_camera_model.ipynb
    02_evaluate_forecast.ipynb
    run_in_colab.ipynb
  tests/
  docs/
    ASSUMPTIONS.md
    EVIDENCE.md
    DEMO_SCRIPT.md
```

## Writing style (on-screen text, README, docs and code comments)

- Use British and Singaporean spelling, such as utilise, programme, organisation, colour and optimise.
- Never use em dashes. Use commas, "such as", or parentheses instead.
- Keep a formal but plain register with no hype or filler. Words such as "revolutionary", "seamless" and "leverage" are not allowed.
- Explain technical terms inline the first time they appear, such as "nowcast (a forecast revised with what has already happened this morning)".
- Anchor claims in specifics such as dates, counts, kilograms, minutes, Singapore dollars and named sources.
- In docs, open each section with its purpose, widen to the context, then narrow to the concrete point, and fold short lists into sentences where that reads naturally.
- UI microcopy uses sentence case and verb-first buttons ("Log arrivals", "Check tray", "Retrain tonight"), no exclamation marks, and error messages that say what happened and what to do next. Copy the wording on the design screens exactly unless it conflicts with real data.

## Screen designs

- Before building or changing any screen, read `design/SCREENS.md`, view that screen's PNG in `design/screens/`, and read its HTML in `design/html/` for exact sizes and spacing. Rebuild the look in Gradio; never serve the HTML files.
- Pages and modes: Kitchen board (dark, page "/"), Runner with Tray check and Ask BuffetIQ (dark, phone), Guest (light, phone, no navbar, so guests never see kitchen pages) and Day-end report (light, laptop, fluid).
- The kitchen board is read, not touched. It runs full screen on a TV or projector at the pass, never scrolls, keeps dishes in a fixed order, and uses voice and the runner's phone for input, with four 96px backup buttons.
- Build read-only regions (dish cards, stat pills, alerts, report cards) as `gr.HTML` rendered by Python functions from `state.py`, and inputs as native Gradio components styled with `elem_classes`.
- When a screen is done, tell us which screenshot to compare it with and list any differences you know of.

## Visual style

Both modes share Inter (from Google Fonts, with system-ui as fallback) and tabular numbers. Keep every token in `style.py` as CSS custom properties scoped to `.bq-kitchen` and `.bq-guest`, so the group can change colours in one place.

Kitchen and runner (dark, high contrast):

| Token | Value | Use |
| --- | --- | --- |
| bg | #0E1415 | page |
| surface | #172123 | cards and panels |
| raised | #1F2B2D | hold blocks, secondary buttons |
| border / border-strong | #2C3A3C / #3C4D4F | card and button borders |
| text / text-2 / text-3 | #F4F1EA / #C9D1D0 / #A9B4B3 | primary, supporting and meta text |
| brand | #7FD3C3 | product name, links, selected chips |
| ok | #5BC0A8 | Full and Half, actual arrivals |
| act | #F2B33D with ink #1A1300 | Low, cook now, the main button, the current slot |
| empty | #FF6B5E with ink #1A1300 | Empty, pan at 4 hours |
| forecast | #6F8584 | dashed forecast outlines |

Guest and report (light, warm):

| Token | Value | Use |
| --- | --- | --- |
| bg / surface | #FAF8F4 / #FFFFFF | page and cards |
| border / border-strong / divider | #E7E2D8 / #CFC8BA / #EFEAE0 | cards, inputs, rows |
| text / muted | #1F2328 / #5F646B | body and secondary text |
| teal / teal-dark / teal-tint | #0F6E6E / #0A4F4F / #E3F1EF | primary buttons, hover, selected rows |
| crowd | Quiet #7FC4BA, Moderate #3E938A, Busy #0F6E6E | time-slot bars, with the word beside each |
| saffron | #E0A030 | tip card border only, never text |
| tip | background #FFF4DD, title #3A2A00, body #5A4512 | the one helpful tip per screen |
| chart | today #0F6E6E, usual day #D9D3C7, earlier weeks #9FC9C3 | report bars |

Type scale: kitchen board clock 80px, action 40px, dish names 26px, buttons 26px, and nothing below 15px. Runner phone titles 26px, answer 28px, body 15 to 17px. Guest headings use Fraunces 600 (32px for page titles, 22px for the hotel name) with Inter for everything else. Report title 34px, figures 36px, section titles 20px. Nothing on any screen is smaller than 13px.

Shape: cards have an 18px radius and a 1px border, buttons and inputs a 12 to 14px radius, and pills are fully rounded, with no gradients and no heavy shadows. Charts show data with one accent on the series the title is about, label values on the marks, and use titles that state the finding.

Accessibility (non-negotiable): every tap target is at least 44px (56px for runner chips, 96px on the kitchen board), text contrast is at least 4.5:1, status is never shown by colour alone (always a word and an icon), icon-only buttons have an `aria-label`, choices use real radio or toggle semantics, and nothing flashes or animates apart from the change itself.

## How to work with me

- Work through the phases in the kickoff prompt one at a time.
- Before each phase, ask me two to four detailed multiple-choice questions about any decision that is genuinely open, with your recommended option first. Do not ask about anything this file already decides.
- After each phase, stop and give a short plain-English summary covering what was built, how to run it, what to show the group, and anything you need from us (such as photos to take).
- Write tests for the logic (nowcast, refill rules, pan timer and fallbacks) and run them before saying a phase is done.
- Commit at the end of each phase with a clear message.
- Do not add features outside the plan without asking first.
- If a result is weaker than expected, say so plainly and suggest changes. Never tune the synthetic data just to make BuffetIQ win.

## Fallbacks that must exist

- No camera model trained yet: manual tray buttons (Full, Half, Low, Empty), labelled as manual.
- No Gemini key, or the free tier is rate limited: a rule-based intent parser that answers the same question types from the same functions, and the status pill on Ask BuffetIQ reads "Basic answers" so chefs know.
- No microphone: typed questions.
- No internet for gTTS: text answers only.
- The Space, Colab or Wi-Fi fails on the day: the laptop copy, then the backup screen recording linked in the README.
