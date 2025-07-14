from nicegui import ui
from utils_api import load_clips, load_videos
import json
from collections import defaultdict, Counter

def partner_page():
    with ui.column().classes("items-center w-full"):
        all_clips = load_clips()
        all_videos = load_videos()

        all_playlists = sorted({c['playlist_name'] for c in all_clips if 'playlist_name' in c} |
                               {v['playlist_name'] for v in all_videos if 'playlist_name' in v})
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

        HIGH_USAGE_THRESHOLD = 100

        compound_nodes = []
        for playlist in all_playlists:
            compound_nodes.append({
                "data": {
                    "id": f"playlist_{playlist}",
                    "label": playlist,
                    "color": playlist_colors.get(playlist, "#FFFFFF"),
                }
            })

        nodes = []
        for partner in partners:
            playlist, _ = partner_playlist_counter[partner].most_common(1)[0] if partner_playlist_counter[partner] else ('Unknown', 0)
            node_data = {
                "id": partner,
                "label": partner,
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
                "target": p2,
                "weight": total,
                "color": color,
                "clips": counts["clips"],
                "films": counts["films"],
            }
            edges.append({"data": edge_data})

        elements = compound_nodes + nodes + edges
        elements_json = json.dumps(elements)

        with ui.row().classes('w-full mt-10 gap-4').style('align-items: flex-start; flex-wrap: wrap;'):
            ui.html('<div id="cy" style="height: 600px; flex: 1 1 60%; min-width: 700px; border: 1px solid #ccc; background: #f7f7fa;"></div>')
            global meta_panel
            meta_panel = ui.column().classes('p-2 bg-gray-50 border border-gray-200 rounded') \
                .style('min-height: 600px; flex: 1 1 35%; min-width: 200px; overflow:auto;') \
                .props('id=meta_panel')

        # Load dependencies in the correct order according to cytoscape-fcose documentation
        ui.add_head_html('<script src="https://unpkg.com/cytoscape@3.24.0/dist/cytoscape.min.js"></script>')
        ui.add_head_html('<script src="https://unpkg.com/layout-base/layout-base.js"></script>')
        ui.add_head_html('<script src="https://unpkg.com/cose-base/cose-base.js"></script>')
        ui.add_head_html('<script src="https://unpkg.com/cytoscape-fcose/cytoscape-fcose.js"></script>')

        # Load our custom graph implementation
        ui.add_head_html('<script src="/static/partner_graph.js"></script>')

        ui.add_body_html(f"""
        <script>
        // Initialize the graph when the page is ready
        document.addEventListener('DOMContentLoaded', function() {{
            console.log('DOM loaded, initializing partner graph...');
            initializePartnerGraph('{elements_json}');
        }});

        // Fallback initialization if DOMContentLoaded already fired
        if (document.readyState === 'loading') {{
            document.addEventListener('DOMContentLoaded', function() {{
                console.log('DOM loaded (fallback), initializing partner graph...');
                initializePartnerGraph('{elements_json}');
            }});
        }} else {{
            console.log('DOM already loaded, initializing partner graph immediately...');
            initializePartnerGraph('{elements_json}');
        }}
        </script>
        """)
