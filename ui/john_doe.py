import random
from nicegui import ui


JOHN_DOE_PUNS = [
    lambda: create_dialog(
        title="🎭 Caught you, John Doe!",
        body="Click responsibly... or face more dad jokes.",
        button_text="Dismiss"
    ),
    lambda: create_dialog(
        title="🎉 John Doe Detected!",
        body="Trying to sneak a click, huh?\n\nDemo mode is safe for browsing but locked for edits.",
        button_text="I’ll behave"
    ),
    lambda: create_dialog(
        title="🎭 John Doe detected... deploying sarcasm mode!",
        body="Click responsibly... or face more dad jokes.",
        button_text="Dismiss"
    ),
    lambda: create_dialog(
        title="🎉 John Doe Detected!",
        body="Demo users don’t get to *ginga* all over the DB.",
        button_text="I’ll tap"
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