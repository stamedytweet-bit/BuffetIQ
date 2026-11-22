"""Ask BuffetIQ (Phase 6): answer kitchen questions from the same numbers as the board.

The pipeline is:
  speech  -> faster-whisper ("small", on this laptop) -> question text
  question -> Gemini (model from GEMINI_MODEL) with five functions that read the
              kitchen engine: get_refill_plan, get_stock, get_forecast, get_timer
              and get_alerts -> one or two short spoken-style sentences
  answer  -> gTTS -> spoken audio, with the text shown as well

Gemini may only answer from function results. Every number in its answer is
checked against those results; if one does not match, the rule-based answer
built from the same results is used instead, so the answer always matches the
board. Without a key, with the free tier rate limited, or offline, a rule-based
intent parser answers the same question types and the status pill reads
"Basic answers".

Privacy: only dish names, quantities and times leave the laptop. Room numbers
and other long numbers in a question are removed before it is sent, because
free-tier requests may be used to improve Google's products.
"""

from __future__ import annotations

import hashlib
import os
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from pathlib import Path

from buffetiq import nowcast, state

NO_ANSWER = "I don't have that. Please check the board."
TTS_DIR = state.ROOT / "data" / "tts"
WHISPER_SIZE = "small"
GEMINI_TIMEOUT_S = 20
COOLDOWN_S = 60          # after a Gemini error, use basic answers for this long

try:  # read GEMINI_API_KEY and GEMINI_MODEL from a local .env file (ignored by git)
    from dotenv import load_dotenv

    load_dotenv(state.ROOT / ".env")
except ImportError:  # pragma: no cover
    pass


# ---------------------------------------------------------------------------
# Dishes from kitchen language
# ---------------------------------------------------------------------------

def find_dish(text: str | None) -> dict | None:
    """Match a dish by its name or spoken synonyms, longest phrase first ('scrambled eggs' before 'eggs')."""
    if not text:
        return None
    t = " " + re.sub(r"[^a-z ]", " ", text.lower()) + " "
    best, best_len = None, 0
    for d in state.load_config()["dishes"]:
        for phrase in [d["name"].lower(), d["id"].replace("_", " "), *d["synonyms"]]:
            if f" {phrase} " in t and len(phrase) > best_len:
                best, best_len = d, len(phrase)
    return best


def redact(question: str) -> str:
    """Remove room numbers and other 3 to 5 digit numbers before a question leaves the laptop."""
    q = re.sub(r"\b(room|rm)\s*#?\s*\d+\b", r"\1 [number]", question, flags=re.I)
    return re.sub(r"(?<![:\d])\b\d{3,5}\b(?![:\d])", "[number]", q)


# ---------------------------------------------------------------------------
# The five functions (read-only views of the kitchen engine)
# ---------------------------------------------------------------------------

def _svc():
    return state.service()


def _amount(d: dict, x: float) -> float:
    return int(round(x)) if d["unit"] == "pieces" else round(x, 1)


def _unit(d: dict) -> str:
    return "pieces" if d["unit"] == "pieces" else "kg"


def get_refill_plan(dish: str) -> dict:
    """What the board says to do for one dish now."""
    d = find_dish(dish)
    if d is None:
        return {"error": f"unknown dish: {dish}"}
    s = _svc()
    e = s.kitchen()
    call = e.calls.get(d["id"])
    cooking = sum(b.amount for b in e.batches_for(d["id"]))
    ready = min((b.ready for b in e.batches_for(d["id"])), default=None)
    action = nowcast.action_text(d, call) if (e.started and call) else "Hold"
    return {
        "dish": d["name"],
        "board_call": action,
        "action": call.action if (e.started and call) else "hold",
        "amount_to_cook": _amount(d, call.amount) if (call and call.action == "cook") else 0,
        "unit": _unit(d),
        "ready_in_minutes": int(max(1, round(ready - s.clock_minutes()))) if ready is not None else None,
        "board_line": (call.line if (e.started and call) else f"Service starts at {s.config['service']['start']}"),
        "last_cook_time": d["last_cook"],
        "lead_minutes": int(d["lead_minutes"]),
        "now": s.clock.strftime("%H:%M"),
        "cooking_now": _amount(d, cooking),
    }


def _level(stock: float, cap: float) -> str:
    frac = min(stock, cap) / cap
    return "Empty" if frac <= 0.02 else "Low" if frac < 0.25 else "Half" if frac <= 0.75 else "Full"


def get_stock(dish: str = "all") -> dict:
    """Tray level and amount for one dish, or every dish."""
    e = _svc().kitchen()
    dishes = state.load_config()["dishes"]
    chosen = [find_dish(dish)] if dish and dish != "all" and find_dish(dish) else dishes
    out = []
    for d in chosen:
        cap = float(d["pan_capacity"])
        stock = e.stock.get(d["id"], cap)
        out.append({"dish": d["name"], "level": _level(stock, cap), "on_tray": _amount(d, min(stock, cap)),
                    "tray_capacity": _amount(d, cap), "in_reserve": _amount(d, max(stock - cap, 0.0)),
                    "unit": _unit(d)})
    return {"trays": out}


def get_forecast(window: str = "today") -> dict:
    """Guests expected today, so far, and in the next 15 minutes or hour."""
    s = _svc()
    e = s.kitchen()
    n = e.n() if e.started else s.expected_diners()
    now = s.clock_minutes()
    nxt15 = nowcast.remaining_between(n, e.arrived(), e.shares, now, now + 15) if e.started else 0.0
    nxt60 = nowcast.remaining_between(n, e.arrived(), e.shares, now, now + 60) if e.started else 0.0
    slots = s.expected_slots()
    return {"expected_today": int(round(n)), "night_before_forecast": int(round(s.n0)),
            "diners_so_far": int(round(e.arrived())), "next_15_minutes": int(round(nxt15)),
            "next_15_minutes_crowd": state.crowd_word(nxt15, float(max(slots.max(), 1))),
            "next_hour": int(round(nxt60)), "now": s.clock.strftime("%H:%M"), "window": window}


def get_timer(dish: str = "all") -> dict:
    """4-hour pan timers: when each pan went out and when it must be swapped."""
    s = _svc()
    e = s.kitchen()
    now = s.clock_minutes()
    dishes = state.load_config()["dishes"]
    chosen = [find_dish(dish)] if dish and dish != "all" and find_dish(dish) else dishes
    out = []
    for d in chosen:
        if d.get("chilled"):
            out.append({"dish": d["name"], "status": "chilled", "note": "Chilled display, check temperature"})
            continue
        out_at = e.out_at.get(d["id"]) if e.started else None
        status, _ = nowcast.pan_status(out_at, now)
        out.append({"dish": d["name"], "status": {"ok": "fine", "warn": "near 4 hours", "limit": "swap now"}[status],
                    "out_since": nowcast.hhmm(out_at) if out_at is not None else None,
                    "swap_by": nowcast.hhmm(out_at + nowcast.PAN_LIMIT) if out_at is not None else None,
                    "minutes_held": int(now - out_at) if out_at is not None else None})
    return {"pans": out, "now": s.clock.strftime("%H:%M")}


def get_alerts() -> dict:
    from buffetiq.ui import kitchen

    return {"alerts": [{"title": a["title"], "detail": a["line"]} for a in kitchen.live_alerts()]}


FUNCTIONS = {"get_refill_plan": get_refill_plan, "get_stock": get_stock, "get_forecast": get_forecast,
             "get_timer": get_timer, "get_alerts": get_alerts}

DECLARATIONS = [
    {"name": "get_refill_plan", "description": "The kitchen board's current call for one dish: what to cook and how much, "
     "when it will be ready, and the dish's last cook or bake time.",
     "parameters_json_schema": {"type": "object", "properties": {"dish": {"type": "string",
                                "description": "Dish name or kitchen word, such as eggs, sausages, rice or croissants"}},
                                "required": ["dish"]}},
    {"name": "get_stock", "description": "Tray level (Empty, Low, Half or Full) and amount for one dish, or 'all' dishes.",
     "parameters_json_schema": {"type": "object", "properties": {"dish": {"type": "string"}}, "required": ["dish"]}},
    {"name": "get_forecast", "description": "Guests expected today, diners so far, and guests expected in the next 15 minutes and next hour.",
     "parameters_json_schema": {"type": "object", "properties": {"window": {"type": "string",
                                "enum": ["today", "next_15_minutes", "next_hour"]}}, "required": ["window"]}},
    {"name": "get_timer", "description": "4-hour hot-holding timers for one dish's pan, or 'all' pans.",
     "parameters_json_schema": {"type": "object", "properties": {"dish": {"type": "string"}}, "required": ["dish"]}},
    {"name": "get_alerts", "description": "The kitchen board's newest alerts.",
     "parameters_json_schema": {"type": "object", "properties": {}}},
]

SYSTEM = (
    "You are Ask BuffetIQ, the voice assistant for a hotel breakfast kitchen. Answer only from the function results "
    "you receive; never guess or use outside knowledge. Reply in one or two short sentences in a plain spoken style, "
    "with the instruction first. Use the numbers exactly as the results give them: kilograms with at most one decimal "
    "place, whole minutes, croissants as whole pieces, times as HH:MM. Copy the board_call wording, such as 'Cook 4 kg'. "
    f"If the functions do not answer the question, reply exactly: {NO_ANSWER}"
)


# ---------------------------------------------------------------------------
# Answers
# ---------------------------------------------------------------------------

@dataclass
class Answer:
    question: str
    main: str
    more: str = ""
    mode: str = "basic"            # "gemini", "basic" (rule-based) or "none"
    verified: bool = True          # every number matches a function result
    seconds: float = 0.0
    calls: list = field(default_factory=list)
    at: str = ""

    @property
    def text(self) -> str:
        return f"{self.main} {self.more}".strip()

    @property
    def spoken(self) -> str:
        """Kitchen-board wording for speech: units in full."""
        t = re.sub(r"(\d)\s*kg\b", r"\1 kilograms", self.text)
        return re.sub(r"(\d)\s*min\b", r"\1 minutes", t)


def split_sentences(text: str) -> tuple[str, str]:
    parts = re.split(r"(?<=[.!?])\s+", text.strip(), maxsplit=1)
    return parts[0], (parts[1] if len(parts) > 1 else "")


def _pretty(line: str) -> str:
    return line.replace(" · ", ", ")


def _plural(name: str) -> str:
    return name.lower()


# ---- rule-based intent parser (the fallback) ----

def classify(question: str) -> tuple[str, dict | None]:
    q = question.lower()
    dish = find_dish(q)
    if re.search(r"\b(alert|alerts|problem|problems|anything wrong|what'?s happening|warning)\b", q):
        return "alerts", dish
    if re.search(r"\b(pan|pans|timer|four hours|4 hours|swap|discard)\b", q):
        return "timer", dish
    if re.search(r"\b(stop|last (cook|bake|batch)|until when)\b", q) and dish:
        return "stop", dish
    if re.search(r"\b(guests?|diners?|people|covers|busy|expected|forecast|coming|crowd)\b", q):
        return "forecast", dish
    if re.search(r"\b(running low|low|empty|left|level|tray|stock|remaining)\b", q):
        return "stock", dish
    if dish and re.search(r"\b(cook|make|bake|need|refill|more|should|prepare|fry|how much)\b", q):
        return "refill", dish
    if dish:
        return "refill", dish
    return "unknown", None


def rule_answer(question: str) -> tuple[str, str, list]:
    """(main, more, function calls used) from the five functions, without Gemini."""
    intent, dish = classify(question)
    calls = []
    if intent in ("refill", "stop"):
        r = get_refill_plan(dish["name"]); calls.append(("get_refill_plan", r))
        name = dish["name"].lower()
        if intent == "stop":
            verb = "bake" if dish["unit"] == "pieces" else "cook"
            return f"The last {verb} for {name} is {r['last_cook_time']}.", f"The board says {r['board_call']} now.", calls
        if r["action"] == "cook":
            main = f"{r['board_call']} of {name} now."
            more = (f"Ready in {r['ready_in_minutes']} minutes." if r["ready_in_minutes"] else _pretty(r["board_line"]) + ".")
            if "empty since" in r["board_line"]:
                more = f"The tray has been empty since {r['board_line'].split('since ')[-1]}."
            return main, more, calls
        if r["action"] == "run_down":
            return f"Let the {name} run down.", f"The last cook was {r['last_cook_time']}.", calls
        if r["action"] == "cook_to_order":
            return f"Cook {name} to order now.", "Small portions as guests ask.", calls
        return f"Hold the {name}.", _pretty(r["board_line"]) + ".", calls
    if intent == "stock":
        r = get_stock(dish["name"] if dish else "all"); calls.append(("get_stock", r))
        if dish:
            t = r["trays"][0]
            return (f"{t['dish']} is {t['level'].lower()}, with {t['on_tray']} {t['unit']} on the tray.",
                    f"{t['in_reserve']} {t['unit']} more in reserve." if t["in_reserve"] else "", calls)
        low = [t for t in r["trays"] if t["level"] in ("Empty", "Low")]
        if not low:
            return "Nothing is running low.", "Every tray is half full or more.", calls
        parts = [f"{t['dish'].lower()} {'is empty' if t['level'] == 'Empty' else 'is low'}" for t in low]
        sentence = ", ".join(parts[:-1]) + (" and " if len(parts) > 1 else "") + parts[-1]
        return sentence[0].upper() + sentence[1:] + ".", "Check the board for what to cook.", calls
    if intent == "forecast":
        r = get_forecast("today"); calls.append(("get_forecast", r))
        return (f"{r['expected_today']} guests expected today, {r['diners_so_far']} so far.",
                f"The next 15 minutes look {r['next_15_minutes_crowd'].lower()}, about {r['next_15_minutes']} guests.", calls)
    if intent == "timer":
        r = get_timer(dish["name"] if dish else "all"); calls.append(("get_timer", r))
        pans = [p for p in r["pans"] if p.get("swap_by")]
        near = [p for p in pans if p["status"] in ("near 4 hours", "swap now")]
        if dish and pans:
            p = pans[0]
            return f"The {p['dish'].lower()} pan went out at {p['out_since']}.", f"Swap it by {p['swap_by']}.", calls
        if near:
            p = near[0]
            return f"The {p['dish'].lower()} pan is {p['status']}.", f"Swap it by {p['swap_by']}.", calls
        if pans:
            oldest = min(pans, key=lambda p: p["swap_by"])
            return "No pans are near 4 hours.", f"The next swap is {oldest['dish'].lower()} at {oldest['swap_by']}.", calls
        return "No pans are out yet.", "", calls
    if intent == "alerts":
        r = get_alerts(); calls.append(("get_alerts", r))
        if not r["alerts"]:
            return "No alerts right now.", "", calls
        a = r["alerts"][0]
        return a["title"] + ".", a["detail"], calls
    return NO_ANSWER, "", calls


# ---- consistency check ----

NUM = re.compile(r"\d{1,2}:\d{2}|\d+(?:\.\d+)?")


def _numbers_in(obj) -> set[str]:
    found: set[str] = set()
    if isinstance(obj, dict):
        for v in obj.values():
            found |= _numbers_in(v)
    elif isinstance(obj, (list, tuple)):
        for v in obj:
            found |= _numbers_in(v)
    elif isinstance(obj, bool) or obj is None:
        pass
    elif isinstance(obj, (int, float)):
        x = float(obj)
        found |= {f"{x:g}", f"{x:.1f}", str(int(round(x)))}
    elif isinstance(obj, str):
        found |= set(NUM.findall(obj))
    return found


def numbers_match(answer: str, results: list, question: str) -> bool:
    """True when every number in the answer appears in the function results or the question."""
    allowed = _numbers_in([r for _, r in results]) | set(NUM.findall(question)) | {"4"}   # "4 hours" is the rule itself
    return all(n in allowed or n.rstrip("0").rstrip(".") in allowed for n in NUM.findall(answer))


# ---- Gemini ----

_LOCK = threading.Lock()
_cooldown_until = 0.0


def gemini_ready() -> bool:
    return bool(os.environ.get("GEMINI_API_KEY")) and bool(os.environ.get("GEMINI_MODEL")) and time.time() >= _cooldown_until


def status() -> str:
    """Status pill: 'connected', 'basic' or 'offline'."""
    try:
        state.service()
    except Exception:
        return "offline"
    return "connected" if gemini_ready() else "basic"


def gemini_answer(question: str) -> tuple[str, list]:
    from google import genai
    from google.genai import types

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"],
                          http_options=types.HttpOptions(timeout=GEMINI_TIMEOUT_S * 1000))
    tools = [types.Tool(function_declarations=[types.FunctionDeclaration(**d) for d in DECLARATIONS])]
    config = types.GenerateContentConfig(system_instruction=SYSTEM, tools=tools, temperature=0,
                                         automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True))
    contents = [types.Content(role="user", parts=[types.Part(text=redact(question))])]
    results: list = []
    for _ in range(4):
        resp = client.models.generate_content(model=os.environ["GEMINI_MODEL"], contents=contents, config=config)
        calls = resp.function_calls or []
        if not calls:
            return (resp.text or "").strip(), results
        contents.append(resp.candidates[0].content)
        parts = []
        for c in calls:
            fn = FUNCTIONS.get(c.name)
            out = fn(**(c.args or {})) if fn else {"error": f"unknown function {c.name}"}
            results.append((c.name, out))
            parts.append(types.Part.from_function_response(name=c.name, response={"result": out}))
        contents.append(types.Content(role="user", parts=parts))
    return NO_ANSWER, results


def ask(question: str, use_gemini: bool | None = None) -> Answer:
    """Answer a typed or transcribed question. Never raises: errors fall back to basic answers."""
    global _cooldown_until
    question = (question or "").strip()
    t0 = time.time()
    s = state.service()
    at = s.clock.strftime("%H:%M")
    if not question:
        return Answer(question, NO_ANSWER, mode="none", at=at)
    use_gemini = gemini_ready() if use_gemini is None else use_gemini
    main = more = ""
    mode, verified, calls = "basic", True, []
    if use_gemini:
        try:
            text, calls = gemini_answer(question)
            if text and numbers_match(text, calls, question):
                main, more = split_sentences(text)
                mode = "gemini"
            else:
                verified = False
        except Exception:
            with _LOCK:
                _cooldown_until = time.time() + COOLDOWN_S
    if not main:
        main, more, calls = rule_answer(question)
        mode = "basic" if main != NO_ANSWER else "none"
    ans = Answer(question, main, more, mode, verified if mode != "none" else False,
                 round(time.time() - t0, 2), [c[0] for c in calls], at)
    remember(ans)
    return ans


def remember(ans: Answer) -> None:
    s = state.service()
    with state.LOCK:
        s.last_answer = {"question": ans.question, "answer": ans.text, "spoken": ans.spoken, "at": ans.at,
                         "mode": ans.mode}
        s.log_event("voice_question", note=f"{ans.mode}: {redact(ans.question)[:80]} -> {ans.text[:120]}",
                    source="assistant")


# ---------------------------------------------------------------------------
# Speech in and out
# ---------------------------------------------------------------------------

_WHISPER = None
_WHISPER_LOCK = threading.Lock()
VOCAB = ("Scrambled eggs, chicken sausages, hash browns, pancakes, mee goreng, nasi lemak rice, croissants, "
         "cut fruit, kilograms, pans, four hours, cook to order.")


def whisper():
    global _WHISPER
    with _WHISPER_LOCK:
        if _WHISPER is None:
            from faster_whisper import WhisperModel

            _WHISPER = WhisperModel(WHISPER_SIZE, device="cpu", compute_type="int8")
        return _WHISPER


def preload_whisper() -> None:
    threading.Thread(target=lambda: _safe(whisper), daemon=True).start()


def _safe(fn):
    try:
        return fn()
    except Exception:
        return None


def decode_audio(path: str, rate: int = 16000):
    """Decode any recording (webm, mp4, mp3, wav) to 16 kHz mono floats with PyAV."""
    import av
    import numpy as np

    chunks = []
    with av.open(str(path)) as c:
        rs = av.AudioResampler(format="s16", layout="mono", rate=rate)
        for frame in c.decode(audio=0):
            chunks.extend(f.to_ndarray().reshape(-1) for f in rs.resample(frame))
        chunks.extend(f.to_ndarray().reshape(-1) for f in rs.resample(None))
    return (np.concatenate(chunks).astype(np.float32) / 32768.0) if chunks else np.zeros(0, np.float32)


def transcribe(path: str) -> str:
    audio = decode_audio(path)
    if audio.size < 1600:          # under 0.1 seconds
        return ""
    segs, _ = whisper().transcribe(audio, language="en", initial_prompt=VOCAB, beam_size=1, vad_filter=True)
    return " ".join(s.text for s in segs).strip()


def speak(text: str) -> str | None:
    """MP3 of the answer with gTTS, or None when there is no internet (text answers only)."""
    try:
        from gtts import gTTS

        TTS_DIR.mkdir(parents=True, exist_ok=True)
        path = TTS_DIR / (hashlib.md5(text.encode()).hexdigest()[:16] + ".mp3")
        if not path.exists():
            gTTS(text, lang="en", tld="com.sg").save(str(path))
        return str(path)
    except Exception:
        return None


def audio_html(path: str | None) -> str:
    """An autoplaying <audio> element with the MP3 inline, or nothing when there is no audio."""
    if not path:
        return ""
    import base64

    data = base64.b64encode(Path(path).read_bytes()).decode()
    return f'<audio autoplay src="data:audio/mpeg;base64,{data}"></audio>'


def ask_from_audio(path: str) -> tuple[Answer | None, str]:
    """(answer, message). The message explains a problem when there is no answer."""
    if not path or path.startswith("ERROR:"):
        reason = path[6:] if path else ""
        if reason in ("NotAllowedError", "SecurityError", "TypeError", "NotFoundError"):
            return None, ("The microphone is not available on this link. Type the question instead, "
                          "or open the app through its https share link.")
        return None, "Nothing was recorded. Hold the button while you speak, or type the question."
    try:
        text = transcribe(path)
    except Exception:
        return None, "The recording could not be read. Try again, or type the question."
    if not text:
        return None, "I did not catch that. Hold the button while you speak, then let go."
    return ask(text), ""
