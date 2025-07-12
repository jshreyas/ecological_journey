from nicegui import ui

from utils import get_notion_tree


notion_iframe = ''

def update_iframe(id: str):
    url = f"https://delightful-canary-0f8.notion.site/ebd/{id.replace('-', '')}"
    notion_iframe.content = f'<iframe src="{url}" width="100%" height="700px" frameborder="0" allowfullscreen"></iframe>'

def get_expanded_first_level_ids(pages):
    """Get IDs of first-level children (direct children of root)."""
    expanded_ids = []
    for page in pages:
        if 'children' in page:
            expanded_ids.append(page['id'])
    return expanded_ids

def reset_tree_to_first_level(tree, expanded_ids):
    tree._props['expanded'] = expanded_ids.copy()  # overwrite, don't add
    tree.update()  # trigger UI refresh

# TODO: Make this whole section scrollable
# TODO: Add a small sync button to update the tree: recache=True
def render_tree(pages, level=0):
    with ui.scroll_area().classes('w-full').style('height: 100vw; max-height: 100vh;'):
        expanded = False
        tree = None  # Placeholder so we can assign it later
        expanded_ids = get_expanded_first_level_ids(pages)

        def toggle_tree():
            nonlocal expanded, tree
            if expanded:
                reset_tree_to_first_level(tree, expanded_ids)
                toggle_button.set_icon('unfold_more')
            else:
                tree.expand()
                toggle_button.set_icon('unfold_less')
            expanded = not expanded
            tree.update()

        with ui.row().classes('w-full justify-between items-center'):
            ui.label('📚 Notion Pages').classes('font-bold text-lg text-primary')
            with ui.row().classes('gap-2'):
                toggle_button = ui.button(icon='unfold_more', on_click=toggle_tree).props('dense flat')

        # Create the tree AFTER buttons, so it's below
        tree = ui.tree(
            pages,
            label_key='title',
            on_select=lambda e: update_iframe(e.value)
        ).classes('w-full')

        # Expand first-level nodes
        tree.expand(expanded_ids.copy())

def notion_page():
    global notion_iframe
    notion_pages = get_notion_tree()

    with ui.splitter(horizontal=False, value=25).classes('w-full h-full rounded shadow') as splitter:
        with splitter.before:
            render_tree(notion_pages)
        with splitter.after:
            notion_iframe = ui.html('').classes('w-full h-full rounded shadow bg-white')
            update_iframe(notion_pages[0]['id'])
