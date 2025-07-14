from nicegui import ui, app
from utils_api import load_clips, load_videos, load_playlists
import json
from collections import defaultdict, Counter

from nicegui import app
from fastapi import Request
from fastapi.responses import HTMLResponse

@app.get('/api/partner_details')
async def partner_details(request: Request):
    # Get query params (e.g., id, type, etc.)
    params = dict(request.query_params)
    # You can also use POST and JSON if you want more complex data
    # Build the HTML using your Python logic
    if params.get('type') == 'edge':
        html = f"<b>Edge:</b> {params['source']} - {params['target']}<br><b>Shared clips:</b> {params.get('clips', 0)}<br><b>Shared films:</b> {params.get('films', 0)}"
    # check for playlist nodes and partner nodes
    if params.get('type') == 'playlist':
        html = f"<b>Playlist:</b> {params['label']}<br><b>Usage:</b> {int(params['clips']) + int(params['films'])}<br><b>Partners:</b> {params['partners']}"
    elif params.get('type') == 'node':
        html = f"<b>Partner:</b> {params['label']}<br><b>Usage:</b> {params['count']}"
    return HTMLResponse(html)

def partner_page():
    with ui.splitter(value=70).classes('w-full h-[600px] mt-10') as splitter:
        with splitter.before:
            # Graph panel
            ui.html('<div id="cy" style="height: 600px; flex: 1 1 60%; min-width: 900px; border: 1px solid #ccc; background: #f7f7fa;"></div>').classes('w-full')
        with splitter.after:
            # Details panel (will be updated)
            details = ui.html('<div id="details_panel" class="p-4 text-primary" style="width: 100%"></div>')

    with ui.column().classes("items-center w-full"):
        playlists = load_playlists()
        all_clips = load_clips()
        all_videos = load_videos()

        all_playlists = sorted({c['playlist_name'] for c in all_clips if 'playlist_name' in c} |
                               {v['playlist_name'] for v in all_videos if 'playlist_name' in v})

        #TODO: From the playlists, add to all_playlists: clips and video count in the playlist, partner count in the playlist
        a_pp = []
        for playlist in playlists:
            playlist_name = playlist['name']
            playlist_clips = sum(1 for c in all_clips if c['playlist_name'] == playlist_name)
            playlist_videos = sum(1 for v in all_videos if v['playlist_name'] == playlist_name)
            # count number of unique partners from all videos and clips in the playlist
            partners_in_playlist = set()
            for c in all_clips:
                if c['playlist_name'] == playlist_name:
                    partners_in_playlist.update(c.get('partners', []))
            for v in all_videos:
                if v['playlist_name'] == playlist_name:
                    partners_in_playlist.update(v.get('partners', []))
            playlist_partners = len(partners_in_playlist)
            a_pp.append({
                'name': playlist_name,
                'clips': playlist_clips,
                'videos': playlist_videos,
                'partners': playlist_partners,
            })

        # import pdb; pdb.set_trace()
        # Color palette inspired by fcose demo - more subtle and cohesive
        palette = [
            "#E8F4FD", "#F0F8FF", "#F5F5DC", "#F0FFF0", "#FFF8DC",
            "#FDF5E6", "#F0F8FF", "#F5F5F5", "#FAF0E6", "#F8F8FF"
        ]
        playlist_colors = {pl: palette[i % len(palette)] for i, pl in enumerate(all_playlists)}

        # More subtle edge colors
        edge_colors = [
            "#4682B4", "#5F9EA0", "#708090", "#778899", "#B0C4DE",
            "#87CEEB", "#98FB98", "#F0E68C", "#DDA0DD", "#FFB6C1"
        ]
        edge_color_map = {
            pl: edge_colors[i % len(edge_colors)] for i, pl in enumerate(all_playlists)
        }

        partner_playlist_counter = defaultdict(Counter)
        for clip in all_clips:
            for p in clip.get('partners', []):
                partner_playlist_counter[p][clip.get('playlist_name', 'Unknown')] += 1
        for video in all_videos:
            for p in video.get('partners', []):
                partner_playlist_counter[p][video.get('playlist_name', 'Unknown')] += 1

        partner_set = set()
        for clip in all_clips:
            partner_set.update(clip.get('partners', []))
        for video in all_videos:
            partner_set.update(video.get('partners', []))
        partners = sorted(partner_set)

        usage_counts = {
            partner: sum(partner in clip.get('partners', []) for clip in all_clips) +
                     sum(partner in video.get('partners', []) for video in all_videos)
            for partner in partners
        }

        HIGH_USAGE_THRESHOLD = 10

        compound_nodes = []
        for playlist in a_pp:
            compound_nodes.append({
                "data": {
                    "id": f"playlist_{playlist['name']}",
                    "label": playlist['name'],
                    "color": playlist_colors.get(playlist['name'], "#FFFFFF"),
                    "clips": playlist['clips'],
                    "films": playlist['videos'],
                    "partners": playlist['partners'],
                    "type": "playlist",
                }
            })

        nodes = []
        for partner in partners:
            playlist, _ = partner_playlist_counter[partner].most_common(1)[0] if partner_playlist_counter[partner] else ('Unknown', 0)
            node_data = {
                "id": partner,
                "label": partner,
                "type": "node",
                "count": usage_counts[partner],
                "playlist": playlist,
                "color": playlist_colors.get(playlist, "#888"),  # Use playlist color for node
                "parent": f"playlist_{playlist}",
            }
            classes = "high-usage" if usage_counts[partner] >= HIGH_USAGE_THRESHOLD else ""
            node = {"data": node_data}
            if classes:
                node["classes"] = classes
            nodes.append(node)

        edge_weights = defaultdict(lambda: {"clips": 0, "films": 0})
        for clip in all_clips:
            ps = clip.get('partners', [])
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    key = tuple(sorted([ps[i], ps[j]]))
                    edge_weights[key]["clips"] += 1
        for video in all_videos:
            ps = video.get('partners', [])
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    key = tuple(sorted([ps[i], ps[j]]))
                    edge_weights[key]["films"] += 1

        edges = []
        for (p1, p2), counts in edge_weights.items():
            total = counts["clips"] + counts["films"]
            if total == 0:
                continue
            playlist_counter = Counter()
            for clip in all_clips:
                if p1 in clip.get('partners', []) and p2 in clip.get('partners', []):
                    playlist_counter[clip.get('playlist_name', 'Unknown')] += 1
            for video in all_videos:
                if p1 in video.get('partners', []) and p2 in video.get('partners', []):
                    playlist_counter[video.get('playlist_name', 'Unknown')] += 1
            playlist, _ = playlist_counter.most_common(1)[0] if playlist_counter else ('Unknown', 0)
            color = edge_color_map.get(playlist, "#888")
            edge_data = {
                "id": f"{p1}_{p2}",
                "source": p1,
                "type": "edge",
                "target": p2,
                "weight": total,
                "color": color,
                "clips": counts["clips"],
                "films": counts["films"],
            }
            edges.append({"data": edge_data})

        elements = compound_nodes + nodes + edges
        elements_json = json.dumps(elements)

    # Load dependencies in the correct order according to cytoscape-fcose documentation
    ui.add_head_html('<script src="https://unpkg.com/cytoscape@3.24.0/dist/cytoscape.min.js"></script>')
    ui.add_head_html('<script src="https://unpkg.com/layout-base/layout-base.js"></script>')
    ui.add_head_html('<script src="https://unpkg.com/cose-base/cose-base.js"></script>')
    ui.add_head_html('<script src="https://unpkg.com/cytoscape-fcose/cytoscape-fcose.js"></script>')

    # Load our custom graph implementation
    ui.add_head_html('<script src="/static/partner_graph.js"></script>')

    # Add a JS function to update the right panel
    ui.add_body_html(f"""
    <script>
    function showDetails(d) {{
        const panel = document.getElementById('details_panel');
        if (panel) {{
            // Build query string from d
            const params = new URLSearchParams(d).toString();
            fetch(`/api/partner_details?${{params}}`)
                .then(response => response.text())
                .then(html => {{
                    panel.innerHTML = html;
                }});
        }}
    }}

    // Wait until #cy exists and is visible before initializing Cytoscape
    function waitForCyAndInit() {{
        const cyDiv = document.getElementById('cy');
        if (!cyDiv || cyDiv.offsetWidth === 0 || cyDiv.offsetHeight === 0) {{
            setTimeout(waitForCyAndInit, 100);
            return;
        }}
        initializePartnerGraph({json.dumps(elements_json)});
    }}

    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', waitForCyAndInit);
    }} else {{
        waitForCyAndInit();
    }}
    </script>
    """)
