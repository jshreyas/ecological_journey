from nicegui import ui

from ui.utils.utils_api import get_notion_tree


def notion_url(page_id: str) -> str:
    """Build the embeddable Notion page URL from a Notion page ID."""
    return f"https://delightful-canary-0f8.notion.site/ebd/{page_id.replace('-', '')}"


def update_iframe(notion_iframe, page_id: str | None) -> None:
    """Reuse the right-side iframe and navigate it to the selected page."""
    if not page_id:
        return

    notion_iframe.props["src"] = notion_url(page_id)
    notion_iframe.update()


def get_expanded_first_level_ids(pages):
    """Get IDs of first-level children (direct children of root)."""
    return [page["id"] for page in pages if "children" in page]


def reset_tree_to_first_level(tree, expanded_ids):
    tree._props["expanded"] = expanded_ids.copy()
    tree.update()


def render_tree(pages, notion_iframe):
    with ui.scroll_area().classes("w-full").style("height: 100vw; max-height: 100vh;"):
        expanded = False
        tree = None
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
            toggle_button = ui.button(
                icon="unfold_more",
                on_click=toggle_tree,
            ).props("dense flat")

        tree = ui.tree(
            pages,
            label_key="title",
            on_select=lambda e: update_iframe(notion_iframe, e.value),
        ).classes("w-full")

        tree.expand(expanded_ids.copy())


def notion_page():
    notion_pages = get_notion_tree()

    if not notion_pages:
        ui.label("No Notion pages found.")
        return

    with ui.splitter(horizontal=False, value=25).classes("w-full h-full rounded shadow") as splitter:

        # Create the right-side iframe first so the left-side callback
        # can hold and update its reference.
        with splitter.after:
            notion_iframe = (
                ui.element("iframe")
                .props(f"src={notion_url(notion_pages[0]['id'])}")
                .classes("w-full h-[calc(100vh-3em)] rounded shadow bg-white")
            )

        with splitter.before:
            render_tree(notion_pages, notion_iframe)
