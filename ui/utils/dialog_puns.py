import random

from nicegui import ui

ADJECTIVES = [
    "sneaky",
    "wobbly",
    "fuzzy",
    "brave",
    "zippy",
    "quirky",
    "grumpy",
    "jazzy",
    "spicy",
    "bouncy",
    "cosmic",
    "loopy",
    "snazzy",
    "cheeky",
    "dizzy",
    "peppy",
    "crunchy",
    "sassy",
    "whimsical",
    "zany",
]
NOUNS = [
    "otter",
    "ninja",
    "waffle",
    "pickle",
    "panda",
    "taco",
    "wizard",
    "giraffe",
    "robot",
    "pirate",
    "unicorn",
    "sloth",
    "penguin",
    "cactus",
    "dragon",
    "monkey",
    "yeti",
    "lobster",
    "hamster",
    "llama",
]


def generate_funny_title():
    return f"{random.choice(ADJECTIVES)}-{random.choice(NOUNS)}"


JOHN_DOE_PUNS = [
    lambda: create_dialog(
        title="🎭 Caught you, John Doe!",
        body="Click responsibly... or face more dad jokes.",
        button_text="Dismiss",
    ),
    lambda: create_dialog(
        title="🎉 John Doe Detected!",
        body="Trying to sneak a click, huh?\n\nDemo mode is safe for browsing but locked for edits.",
        button_text="I'll behave",
    ),
    lambda: create_dialog(
        title="🎭 John Doe detected... deploying sarcasm mode!",
        body="Click responsibly... or face more dad jokes.",
        button_text="Dismiss",
    ),
    lambda: create_dialog(
        title="🎉 John Doe Detected!",
        body="Demo users don't get to *ginga* all over the DB.",
        button_text="I'll tap",
    ),
]

INPROGRESS_PUNS = [
    lambda: create_dialog(
        title="🚧 Under Construction!",
        body="This feature is still warming up in ginga stance.\n\nCheck back after it learns to cartwheel.",
        button_text="Fair enough",
    ),
    lambda: create_dialog(
        title="🌀 Not Quite Rolê-Ready",
        body="This move's still in the lab — like a blue belt trying berimbolo.\n\nSoon™.",
        button_text="Respect the process",
    ),
    lambda: create_dialog(
        title="🔧 Still Being Hammered Out",
        body="Some features train harder than others.\n\nThis one's hitting pads in the shadows.",
        button_text="Stay strong, feature",
    ),
    lambda: create_dialog(
        title="🥋 Under Maintenance",
        body="Like a white belt figuring out grips — it's gonna take a few tries.",
        button_text="I'll be gentle",
    ),
    lambda: create_dialog(
        title="🛠️ Building Momentum",
        body="This button is just here for moral support... for now.",
        button_text="I support you too",
    ),
    lambda: create_dialog(
        title="🚫 Incomplete Technique Detected!",
        body="Don't worry — the dev is probably working on this in another tab right now.",
        button_text="Hope they're hydrated",
    ),
    lambda: create_dialog(
        title="⚙️ Prototype in Progress",
        body="Still figuring out whether this should sweep, submit, or just play pandeiro.",
        button_text="It's all rhythm",
    ),
]


def create_dialog(title: str, body: str, button_text: str):
    with ui.dialog() as d:
        with ui.card().classes("bg-yellow-50 shadow-md"):
            ui.label(title).classes("text-lg font-bold")
            ui.markdown(body)
            ui.button(button_text).on("click", d.close)
    d.open()


def caught_john_doe():
    random.choice(JOHN_DOE_PUNS)()


def in_progress():
    random.choice(INPROGRESS_PUNS)()


def handle_backend_error(response_text=None):
    # dialog for drama
    with ui.dialog() as d:
        with ui.card().classes("bg-red-100 text-red-900 shadow-lg"):
            ui.label(f"⚠️ Trouble in {generate_funny_title()} zone!").classes("text-lg font-bold")
            ui.markdown(
                "Our backend wizard appears to be napping.\n\n"
                "While we wait, feel free to sip your coffee and try in a bit."
            )
            ui.button("Buzz again").on("click", d.close)
    d.open()
