"""Scripted evaluation of Ask BuffetIQ (Phase 6).

Twenty kitchen questions are asked on the demo morning replayed to 08:40. Each
expected answer is read from the board itself (the same functions), and an
answer matches when it contains every expected fact, such as the board's call
("Cook 5 kg") and the dish. Three runs are made where possible:

  typed, basic answers   the rule-based fallback, no Gemini, no microphone
  typed, Gemini          only when GEMINI_API_KEY and GEMINI_MODEL are set
  spoken                 each question turned into speech with gTTS, then the
                         whole chain: faster-whisper, then Gemini or basic answers

Optionally, recordings of your own voice in data/voice_tests/qNN.<ext> (NN is
the question number) are run through the same chain.

Run from the src folder:  python -m buffetiq.assistant_eval
"""

from __future__ import annotations

import json
import os
import re
import statistics
import time
from pathlib import Path

from buffetiq import assistant, state

RESULTS_PATH = state.ROOT / "docs" / "phase6_results.json"
OWN_VOICE_DIR = state.ROOT / "data" / "voice_tests"
SPOKEN_DIR = state.ROOT / "data" / "voice_tests_gtts"
GEMINI_PAUSE_S = 7     # stay under the free tier's requests per minute


def _call(dish):
    r = assistant.get_refill_plan(dish)
    if r["action"] == "cook":
        return [r["board_call"].lower()]
    return {"hold": ["hold"], "run_down": ["run down"], "cook_to_order": ["to order"]}[r["action"]]


def _stock(dish):
    t = assistant.get_stock(dish)["trays"][0]
    return [t["level"].lower()]


def _low():
    trays = assistant.get_stock("all")["trays"]
    low = [t["dish"].lower() for t in trays if t["level"] in ("Empty", "Low")]
    return low or ["nothing"]


def _timer(dish):
    p = assistant.get_timer(dish)["pans"][0]
    return [p["swap_by"]] if p.get("swap_by") else ["chilled"]


def _pans():
    pans = [p for p in assistant.get_timer("all")["pans"] if p.get("swap_by")]
    near = [p for p in pans if p["status"] != "fine"]
    return [near[0]["dish"].lower()] if near else ["no pan"]


def _alert():
    a = assistant.get_alerts()["alerts"]
    return [a[0]["title"].split(" ran out")[0].lower()] if a else ["no alerts"]


QUESTIONS = [
    ("How much egg should I cook?", lambda: _call("eggs") + ["egg"]),
    ("Do we need more sausages?", lambda: _call("sausages") + ["sausage"]),
    ("What about the hash browns?", lambda: _call("hash browns") + ["hash brown"]),
    ("Should I make more pancakes?", lambda: _call("pancakes") + ["pancake"]),
    ("How much mee goreng should I cook?", lambda: _call("mee goreng") + ["mee goreng"]),
    ("Do I need to cook more rice?", lambda: _call("rice") + ["rice"]),
    ("How many croissants should I bake?", lambda: _call("croissants") + ["croissant"]),
    ("Do we need more fruit?", lambda: _call("fruit") + ["fruit"]),
    ("What is running low?", _low),
    ("How much egg is left on the tray?", lambda: _stock("eggs") + ["egg"]),
    ("Is the fruit tray full?", lambda: _stock("fruit")),
    ("How many guests are we expecting today?", lambda: [str(assistant.get_forecast()["expected_today"])]),
    ("How many people have come in so far?", lambda: [str(assistant.get_forecast()["diners_so_far"])]),
    ("Is the next 15 minutes going to be busy?", lambda: [assistant.get_forecast()["next_15_minutes_crowd"].lower()]),
    ("Any pans near 4 hours?", _pans),
    ("When does the sausage pan need swapping?", lambda: _timer("sausages")),
    ("When do I stop croissants?", lambda: ["09:50"]),
    ("When is the last cook for nasi lemak?", lambda: ["09:55"]),
    ("Any alerts?", _alert),
    ("What's the weather like outside?", lambda: ["i don't have that"]),
]


# Topics added after Phase 7, scored separately so the brief's 20 questions stay unchanged
EXTRA_QUESTIONS = [
    ("Is the hash brown halal?", lambda: ["halal", "vegetarian"]),
    ("Are the croissants halal?", lambda: ["not halal"]),
    ("What can vegetarians eat today?", lambda: ["scrambled eggs", "cut fruit"]),
    ("Does the mee goreng have peanuts?", lambda: ["no", "peanuts"]),
    ("Which dishes have gluten?", lambda: ["pancakes", "croissants", "gluten"]),
    ("What temperature should the eggs be held at?", lambda: ["60"]),
    ("Can I reheat the leftover rice?", lambda: ["no"]),
    ("Why cook more sausages?", lambda: [assistant.get_call_reason("sausages")["board_call"].lower()]),
    ("How much have we thrown away so far?",
     lambda: [str(assistant.get_waste()["thrown_away_kg"])] if assistant.get_waste()["thrown_away_kg"] else ["nothing"]),
    ("How much rice will be left at close?",
     lambda: [str(assistant.get_waste("rice")["dishes"][0]["likely_left_at_close_kg"])]),
]


def normalise(text: str) -> str:
    t = text.lower().replace("’", "'")
    t = re.sub(r"(\d)\s*kilograms?\b", r"\1 kg", t)
    t = re.sub(r"\b(\d)\.0\b", r"\1", t)
    return t


def matches(answer: str, expected: list[str]) -> bool:
    a = normalise(answer)
    return all(normalise(e) in a for e in expected)


def setup() -> None:
    s = state.Service(checkins_path=state.ROOT / "data" / "_eval_checkins.csv",
                      log_path=state.ROOT / "data" / "_eval_log.csv")
    state._SERVICE = s
    s.replay_to("08:40")


def run_typed(use_gemini: bool, questions=None) -> list[dict]:
    rows = []
    for i, (q, expect) in enumerate(questions or QUESTIONS, start=1):
        exp = expect()
        t = time.time()
        a = assistant.ask(q, use_gemini=use_gemini)
        rows.append({"n": i, "question": q, "expected": exp, "answer": a.text, "mode": a.mode,
                     "match": matches(a.text, exp), "seconds": round(time.time() - t, 2)})
        if use_gemini:
            time.sleep(GEMINI_PAUSE_S)
    return rows


def make_spoken() -> None:
    from gtts import gTTS

    SPOKEN_DIR.mkdir(parents=True, exist_ok=True)
    for i, (q, _) in enumerate(QUESTIONS, start=1):
        path = SPOKEN_DIR / f"q{i:02d}.mp3"
        if not path.exists():
            gTTS(q, lang="en", tld="com.sg").save(str(path))


def run_audio(folder: Path, use_gemini: bool) -> list[dict]:
    rows = []
    assistant.whisper()                       # load once, outside the timing
    for i, (q, expect) in enumerate(QUESTIONS, start=1):
        files = sorted(folder.glob(f"q{i:02d}.*"))
        if not files:
            continue
        exp = expect()
        t = time.time()
        heard = assistant.transcribe(str(files[0]))
        t_stt = time.time() - t
        a = assistant.ask(heard, use_gemini=use_gemini)
        rows.append({"n": i, "question": q, "heard": heard, "expected": exp, "answer": a.text, "mode": a.mode,
                     "match": matches(a.text, exp), "seconds": round(time.time() - t, 2),
                     "speech_to_text_seconds": round(t_stt, 2)})
        if use_gemini:
            time.sleep(GEMINI_PAUSE_S)
    return rows


def summary(rows: list[dict]) -> dict:
    if not rows:
        return {}
    return {"questions": len(rows), "matched": sum(r["match"] for r in rows),
            "median_seconds": round(statistics.median(r["seconds"] for r in rows), 2),
            "max_seconds": round(max(r["seconds"] for r in rows), 2)}


def evaluate() -> dict:
    setup()
    gemini = assistant.gemini_ready()
    results = {"model": os.environ.get("GEMINI_MODEL") if gemini else None, "runs": {}}
    results["runs"]["typed_basic"] = run_typed(False)
    results["runs"]["extra_topics_basic"] = run_typed(False, EXTRA_QUESTIONS)
    if gemini:
        results["runs"]["typed_gemini"] = run_typed(True)
        results["runs"]["extra_topics_gemini"] = run_typed(True, EXTRA_QUESTIONS)
    make_spoken()
    results["runs"]["spoken_gtts"] = run_audio(SPOKEN_DIR, gemini)
    if OWN_VOICE_DIR.exists() and any(OWN_VOICE_DIR.iterdir()):
        results["runs"]["spoken_own_voice"] = run_audio(OWN_VOICE_DIR, gemini)
    results["summary"] = {k: summary(v) for k, v in results["runs"].items()}
    RESULTS_PATH.write_text(json.dumps(results, indent=2))
    for f in ("_eval_checkins.csv", "_eval_log.csv"):
        (state.ROOT / "data" / f).unlink(missing_ok=True)
    return results


def main() -> None:
    r = evaluate()
    for name, s in r["summary"].items():
        print(f"{name:<18} {s['matched']}/{s['questions']} match the board, median {s['median_seconds']} s")
    for name, rows in r["runs"].items():
        for row in rows:
            if not row["match"]:
                print(f"  {name} #{row['n']}: {row['question']} | heard: {row.get('heard', '-')} | "
                      f"expected {row['expected']} | got: {row['answer']}")


if __name__ == "__main__":
    main()
