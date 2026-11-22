"""Phase 6 tests: kitchen language, privacy, intents, board-matching answers and fallbacks."""

import pytest

from buffetiq import assistant, state


@pytest.fixture(scope="module")
def svc():
    s = state.Service(checkins_path=state.ROOT / "data" / "_t6.csv", log_path=state.ROOT / "data" / "_t6_log.csv")
    s.replay_to("08:40")
    yield s
    for f in ("_t6.csv", "_t6_log.csv"):
        (state.ROOT / "data" / f).unlink(missing_ok=True)


@pytest.fixture(autouse=True)
def use(svc, monkeypatch):
    monkeypatch.setattr(state, "_SERVICE", svc)


@pytest.mark.parametrize("words,dish", [
    ("how much egg should I cook", "scrambled_eggs"), ("scrambled", "scrambled_eggs"),
    ("more hotdogs", "chicken_sausages"), ("the rice", "nasi_lemak_rice"), ("nasi lemak", "nasi_lemak_rice"),
    ("mee goreng", "mee_goreng"), ("noodles", "mee_goreng"), ("pastries", "croissants"),
    ("watermelon", "cut_fruit"), ("hash brown", "hash_browns"), ("hotcakes", "pancakes"),
])
def test_dish_synonyms(words, dish):
    assert assistant.find_dish(words)["id"] == dish


def test_no_dish_in_general_questions():
    assert assistant.find_dish("how many guests today") is None


def test_room_numbers_never_leave_the_laptop():
    q = assistant.redact("Guest in room 1204 wants eggs, also rm 305, at 08:40 for 4 kg")
    assert "1204" not in q and "305" not in q
    assert "08:40" in q and "4 kg" in q


@pytest.mark.parametrize("q,intent", [
    ("How much egg should I cook?", "refill"), ("What is running low?", "stock"),
    ("Any pans near 4 hours?", "timer"), ("When do I stop croissants?", "stop"),
    ("How many guests are coming?", "forecast"), ("Any alerts?", "alerts"), ("What's the weather?", "unknown"),
])
def test_intents(q, intent):
    assert assistant.classify(q)[0] == intent


def test_refill_answer_uses_the_board_call(svc):
    board = assistant.get_refill_plan("sausages")
    a = assistant.ask("How much sausage should I cook?", use_gemini=False)
    assert board["board_call"] in a.text and a.mode == "basic"
    assert a.spoken.startswith(board["board_call"].replace("kg", "kilograms"))


def test_unknown_question_says_so():
    a = assistant.ask("What's the weather like?", use_gemini=False)
    assert a.text == assistant.NO_ANSWER and a.mode == "none"


def test_numbers_must_come_from_function_results():
    results = [("get_refill_plan", {"board_call": "Cook 5 kg", "amount_to_cook": 5.0, "ready_in_minutes": 15})]
    assert assistant.numbers_match("Cook 5 kg of chicken sausages now. Ready in 15 minutes.", results, "q")
    assert not assistant.numbers_match("Cook 6 kg of chicken sausages now.", results, "q")


def test_invented_gemini_numbers_fall_back_to_the_board(monkeypatch):
    board = assistant.get_refill_plan("sausages")
    monkeypatch.setattr(assistant, "gemini_answer",
                        lambda q: ("Cook 9 kg of chicken sausages now.", [("get_refill_plan", board)]))
    a = assistant.ask("How much sausage should I cook?", use_gemini=True)
    assert a.mode == "basic" and board["board_call"] in a.text


def test_matching_gemini_answer_is_used(monkeypatch):
    monkeypatch.setattr(assistant, "gemini_answer",
                        lambda q: ("Cook 5 kg of chicken sausages now. The tray is empty.",
                                   [("get_refill_plan", {"board_call": "Cook 5 kg", "amount_to_cook": 5})]))
    a = assistant.ask("How much sausage should I cook?", use_gemini=True)
    assert a.mode == "gemini" and a.main == "Cook 5 kg of chicken sausages now."


def test_gemini_errors_fall_back_and_pause(monkeypatch):
    def boom(q):
        raise RuntimeError("429 rate limited")
    monkeypatch.setattr(assistant, "gemini_answer", boom)
    monkeypatch.setenv("GEMINI_API_KEY", "test")
    monkeypatch.setenv("GEMINI_MODEL", "test-model")
    monkeypatch.setattr(assistant, "_cooldown_until", 0.0)
    a = assistant.ask("Any alerts?", use_gemini=True)
    assert a.mode == "basic"
    assert assistant.status() == "basic"        # cooling down after the error, so the pill says so


def test_status_without_a_key_is_basic(monkeypatch):
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    assert assistant.status() == "basic"


def test_no_internet_means_text_only(monkeypatch):
    import gtts

    class Broken:
        def __init__(self, *a, **k):
            raise OSError("no internet")
    monkeypatch.setattr(gtts, "gTTS", Broken)
    assert assistant.speak("A brand new sentence for this test only.") is None
    assert assistant.audio_html(None) == ""


def test_microphone_problems_offer_typing():
    ans, msg = assistant.ask_from_audio("ERROR:NotAllowedError")
    assert ans is None and "Type the question" in msg
    ans, msg = assistant.ask_from_audio("ERROR:TooShort")
    assert ans is None and "Hold the button" in msg


def test_answers_are_logged_without_guest_data(svc):
    assistant.ask("Guest in room 1204 asked about eggs", use_gemini=False)
    text = open(svc.log_path).read()
    assert "voice_question" in text and "1204" not in text


def test_declarations_cover_every_function():
    # the brief's five, plus the five topics added after Phase 7
    assert {d["name"] for d in assistant.DECLARATIONS} == set(assistant.FUNCTIONS) == {
        "get_refill_plan", "get_stock", "get_forecast", "get_timer", "get_alerts",
        "get_dietary", "get_allergens", "get_food_safety", "get_call_reason", "get_waste"}


# ---- topics added after Phase 7 ----

@pytest.mark.parametrize("q,intent", [
    ("Is the hash brown halal?", "dietary"), ("How many vegetarian meals today?", "dietary"),
    ("Does the mee goreng have peanuts?", "allergen"), ("Which dishes have gluten?", "allergen"),
    ("What temperature should the eggs be held at?", "safety"), ("Can I reheat the rice?", "safety"),
    ("Why cook more sausages?", "why"), ("How much have we thrown away?", "waste"),
    ("How much rice will be left at close?", "waste"), ("How much egg is left on the tray?", "stock"),
    ("How much egg should I cook?", "refill"),
])
def test_new_intents(q, intent):
    assert assistant.classify(q)[0] == intent


def test_dietary_answers_follow_the_config():
    assert assistant.ask("Are the croissants halal?", use_gemini=False).main == "Croissants are vegetarian but not halal."
    assert assistant.ask("Is the mee goreng halal?", use_gemini=False).main == "Mee goreng is halal but not vegetarian."


def test_dietary_counts_are_counts_only(svc):
    svc.save_plan(state.GuestPlan(service_date="", room="1204", attending=True, party=3, halal=2, vegetarian=1, slot="09:30"))
    r = assistant.get_dietary("all")
    assert (r["halal_meals_booked"], r["vegetarian_meals_booked"]) == (2, 1)
    assert "1204" not in str(r)
    svc.clear_plans()


def test_allergen_answers():
    a = assistant.ask("Does the mee goreng have peanuts?", use_gemini=False)
    assert a.main == "No, mee goreng has no peanuts." and "gluten, soy and egg" in a.more
    a = assistant.ask("Which dishes have gluten?", use_gemini=False)
    for name in ("chicken sausages", "pancakes", "mee goreng", "croissants"):
        assert name in a.main.lower()
    assert "hash browns" not in a.main.lower()


def test_food_safety_uses_sfa_numbers():
    a = assistant.ask("What temperature should the eggs be held at?", use_gemini=False)
    assert "60°C" in a.main and "5°C" in a.main and "4 hours" in a.more
    assert assistant.ask("What temperature for the cut fruit?", use_gemini=False).main.startswith("Keep cut fruit at 5°C")


def test_why_answer_repeats_the_board_call():
    board = assistant.get_refill_plan("sausages")["board_call"]
    a = assistant.ask("Why cook more sausages?", use_gemini=False)
    assert board in a.text or board == "Hold"


def test_waste_answer(svc):
    a = assistant.ask("How much have we thrown away so far?", use_gemini=False)
    assert a.main == "Nothing has been thrown away so far today." or "thrown away" in a.main
    assert assistant.numbers_match(a.text, [("get_waste", assistant.get_waste("all"))], "q")
