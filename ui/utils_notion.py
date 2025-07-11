import os
from notion_client import Client
import json
from dotenv import load_dotenv

load_dotenv()
notion = Client(auth=os.getenv("NOTION_TOKEN"))

def get_all_blocks(page_id):
    all_blocks = []
    start_cursor = None

    while True:
        response = notion.blocks.children.list(
            block_id=page_id,
            start_cursor=start_cursor
        )
        all_blocks.extend(response["results"])
        if response.get("has_more"):
            start_cursor = response["next_cursor"]
        else:
            break

    return all_blocks

def crawl_page_recursive(page_id):
    children = []
    blocks = get_all_blocks(page_id)

    for block in blocks:
        if block["type"] == "child_page":
            child_id = block["id"]
            title = block["child_page"]["title"]
            child_tree = crawl_page_recursive(child_id)
            children.append({
                "id": child_id,
                "title": title,
                "embed_url": f"https://delightful-canary-0f8.notion.site/ebd/{child_id.replace('-', '')}",
                "children": child_tree
            })

    return children

def generate_tree(root_id="1c1bc4e1-2692-8016-97db-f4d92b5d2464"):
    title = notion.pages.retrieve(root_id)["properties"]["title"]["title"][0]["plain_text"]
    tree = [{
        "id": root_id,
        "title": title,
        "embed_url": f"https://delightful-canary-0f8.notion.site/ebd/{root_id.replace('-', '')}",
        "children": crawl_page_recursive(root_id)
    }]
    return tree
