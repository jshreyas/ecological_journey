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

# TODO: Make this whole section scrollable
# TODO: Add a small sync button to update the tree: recache=True
def render_tree(pages, level=0):
    ui.label('📚 Notion Pages').classes('w-full font-bold text-lg')
    tree = ui.tree(
        pages,  # Tree format
        label_key='title',
        on_select=lambda e: update_iframe(e.value)
    ).classes('w-full')
    expanded_ids = get_expanded_first_level_ids(pages)
    tree.expand(expanded_ids)

def notion_page():
    global notion_iframe
    notion_pages = get_notion_tree()

    with ui.splitter(horizontal=False, value=25).classes('w-full h-full rounded shadow') as splitter:
        with splitter.before:
            render_tree(notion_pages)
        with splitter.after:
            notion_iframe = ui.html('').classes('w-full h-full rounded shadow bg-white')
            update_iframe(notion_pages[0]['id'])
