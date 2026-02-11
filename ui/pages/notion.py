from nicegui import ui

from ui.data.crud import trigger_notion_refresh
from ui.utils.dialog_puns import caught_john_doe
from ui.utils.user_context import User, with_user_context
from ui.utils.utils_api import get_notion_tree

notion_iframe = ""


def update_iframe(id: str):
    url = f"https://delightful-canary-0f8.notion.site/ebd/{id.replace('-', '')}"
    notion_iframe.content = (
        f'<iframe src="{url}" width="100%" height="700px" frameborder="0" allowfullscreen"></iframe>'
    )


def get_expanded_first_level_ids(pages):
    """Get IDs of first-level children (direct children of root)."""
    expanded_ids = []
    for page in pages:
        if "children" in page:
            expanded_ids.append(page["id"])
    return expanded_ids


def reset_tree_to_first_level(tree, expanded_ids):
    tree._props["expanded"] = expanded_ids.copy()  # overwrite, don't add
    tree.update()  # trigger UI refresh


def render_tree(pages, user_token):
    with ui.scroll_area().classes("w-full").style("height: 100vw; max-height: 100vh;"):
        expanded = False
        tree = None  # Placeholder so we can assign it later
        expanded_ids = get_expanded_first_level_ids(pages)

        def toggle_tree():
            nonlocal expanded, tree
            if expanded:
                reset_tree_to_first_level(tree, expanded_ids)
                toggle_button.set_icon("unfold_more")
            else:
                tree.expand()
                toggle_button.set_icon("unfold_less")
            expanded = not expanded
            tree.update()

        with ui.row().classes("w-full justify-between items-center"):
            ui.label("📚 Notion Pages").classes("font-bold text-lg text-primary")
            with ui.row().classes("gap-2"):
                if user_token:
                    ui.button(icon="sync", on_click=lambda: trigger_notion_refresh()).props(
                        "flat dense round color=primary"
                    ).tooltip("Sync")
                else:
                    ui.button(icon="sync", on_click=lambda: caught_john_doe()).props(
                        "flat dense round color=primary"
                    ).tooltip("Sync")
                toggle_button = ui.button(icon="unfold_more", on_click=toggle_tree).props("dense flat")

        # Create the tree AFTER buttons, so it's below
        tree = ui.tree(pages, label_key="title", on_select=lambda e: update_iframe(e.value)).classes("w-full")

        # Expand first-level nodes
        tree.expand(expanded_ids.copy())


@with_user_context
def notion_page(user: User | None):
    global notion_iframe
    notion_pages = get_notion_tree()
    user_token = user.token if user else None
    with ui.splitter(horizontal=False, value=25).classes("w-full h-full rounded shadow") as splitter:
        with splitter.before:
            render_tree(notion_pages, user_token)
        with splitter.after:
            notion_iframe = ui.html("").classes("w-full h-full rounded shadow bg-white")
            update_iframe(notion_pages[0]["id"])
