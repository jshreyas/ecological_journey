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
        palette = [
            "#4F8A8B", "#F9ED69", "#F08A5D", "#B83B5E", "#6A2C70",
            "#3B6978", "#204051", "#FF6F3C", "#A3A847"
        ]
        playlist_colors = {pl: palette[i % len(palette)] for i, pl in enumerate(all_playlists)}

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
        nodes = []
        for partner in partners:
            playlist, _ = partner_playlist_counter[partner].most_common(1)[0] if partner_playlist_counter[partner] else ('Unknown', 0)
            color = playlist_colors.get(playlist, "#888")
            node_data = {
                "id": partner,
                "label": partner,
                "count": usage_counts[partner],
                "playlist": playlist,
                "color": color,
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
            color = playlist_colors.get(playlist, "#888")
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

        elements = nodes + edges
        elements_json = json.dumps(elements)

        with ui.row().classes('w-full mt-10 gap-4').style('align-items: flex-start; flex-wrap: wrap;'):
            ui.html('<div id="cy" style="height: 500px; flex: 1 1 60%; min-width: 700px; border: 1px solid #ccc;"></div>')
            
            global meta_panel
            meta_panel = ui.column().classes('p-2 bg-gray-50 border border-gray-200 rounded') \
                .style('min-height: 500px; flex: 1 1 35%; min-width: 200px; overflow:auto;') \
                .props('id=meta_panel')

        ui.add_body_html(f"""
        <script src=\"https://unpkg.com/cytoscape@3.24.0/dist/cytoscape.min.js\"></script>
        <script>
        function renderCytoscape() {{
            if (typeof cytoscape === 'undefined' || !document.getElementById('cy')) {{
                setTimeout(renderCytoscape, 100);
                return;
            }}
            if (window.cy && window.cy.destroy) {{
                window.cy.destroy();
            }}
            const elements = {elements_json};
            window.cy = cytoscape({{
                container: document.getElementById('cy'),
                elements: elements,
                style: [
                    {{ selector: 'node', style: {{
                        'label': 'data(label)',
                        'background-color': 'data(color)',
                        'width': 'mapData(count, 1, 100, 20, 50)',
                        'height': 'mapData(count, 1, 100, 20, 50)',
                        'text-valign': 'center',
                        'text-halign': 'center',
                        'color': '#fff',
                        'font-size': 16,
                        'text-outline-width': 2,
                        'text-outline-color': '#222'
                    }} }},
                    {{ selector: 'node.high-usage', style: {{
                        'shadow-blur': 30,
                        'shadow-color': '#FFD700',
                        'shadow-opacity': 0.7
                    }} }},
                    {{ selector: 'edge', style: {{
                        'width': 'mapData(weight, 1, 100, 1, 10)',
                        'line-color': 'data(color)',
                        'curve-style': 'bezier',
                        'opacity': 0.8
                    }} }},
                    {{ selector: '.faded', style: {{
                        'opacity': 0.15,
                        'text-opacity': 0.1
                    }} }}
                ],
                layout: {{ name: 'circle', padding: 20 }}
            }});

            function showMeta(html) {{
                const panel = document.getElementById('meta_panel');
                if (panel) {{
                    panel.innerHTML = html;
                }}
            }}

            function focusOnNode(node) {{
                const neighborhood = node.closedNeighborhood();
                const connectedNodes = node.connectedEdges().connectedNodes();

                node.style({{
                    'width': 120,
                    'height': 120,
                    'font-size': 22
                }});

                connectedNodes.forEach(n => {{
                    n.style({{
                        'width': 60,
                        'height': 60,
                        'font-size': 18
                    }});
                }});

                window.cy.animate({{
                    fit: {{ eles: neighborhood, padding: 60 }},
                    duration: 500
                }});

                window.cy.nodes().not(neighborhood).style({{
                    'width': 20,
                    'height': 20,
                    'font-size': 12
                }});

                window.cy.elements().removeClass('faded');
                window.cy.elements().not(neighborhood).addClass('faded');

                const d = node.data();
                showMeta(`<b>Partner:</b> ${{d.label}}<br><b>Playlist:</b> ${{d.playlist}}<br><b>Usage:</b> ${{d.count}}`);
            }}

            window.cy.on('tap', 'node', function(evt) {{
                window.cy.nodes().forEach(n => n.removeStyle());
                focusOnNode(evt.target);
            }});

            window.cy.on('mouseover', 'node', function(evt) {{
                const d = evt.target.data();
                showMeta(`<b>Partner:</b> ${{d.label}}<br><b>Playlist:</b> ${{d.playlist}}<br><b>Usage:</b> ${{d.count}}`);
            }});

            window.cy.on('mouseout', 'node', function(evt) {{
                showMeta('');
            }});

            window.cy.on('mouseover', 'edge', function(evt) {{
                const d = evt.target.data();
                showMeta(`<b>Edge:</b> ${{d.source}} - ${{d.target}}<br><b>Shared clips:</b> ${{d.clips}}<br><b>Shared films:</b> ${{d.films}}`);
            }});

            window.cy.on('mouseout', 'edge', function(evt) {{
                showMeta('');
            }});

            window.cy.on('tap', 'edge', function(evt) {{
                const d = evt.target.data();
                showMeta(`<b>Edge:</b> ${{d.source}} - ${{d.target}}<br><b>Shared clips:</b> ${{d.clips}}<br><b>Shared films:</b> ${{d.films}}`);
            }});

            const defaultNode = window.cy.nodes().sort((a, b) => b.data('count') - a.data('count'))[0];
            if (defaultNode) focusOnNode(defaultNode);
        }}
        renderCytoscape();
        </script>
        """)
