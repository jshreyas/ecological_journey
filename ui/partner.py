from nicegui import ui
from utils_api import load_clips, load_videos
import json
from collections import defaultdict, Counter

def partner_page():
    with ui.column().classes("w-full items-center"):
        ui.label("🤝 Partner Network Graph").classes("text-2xl font-bold my-4")

        all_clips = load_clips()
        all_videos = load_videos()

        # 1. Assign a color to each playlist
        all_playlists = sorted({c['playlist_name'] for c in all_clips if 'playlist_name' in c} |
                               {v['playlist_name'] for v in all_videos if 'playlist_name' in v})
        palette = [
            "#4F8A8B", "#F9ED69", "#F08A5D", "#B83B5E", "#6A2C70", "#3B6978", "#204051", "#FF6F3C", "#A3A847"
        ]
        playlist_colors = {pl: palette[i % len(palette)] for i, pl in enumerate(all_playlists)}

        # 2. Gather partner playlist usage
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

        # 3. Build nodes with color and high-usage class
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

        # 4. Build edges, color by most common playlist among shared clips/films
        edge_weights = defaultdict(lambda: {"clips": 0, "films": 0, "clips_meta": [], "films_meta": []})
        for clip in all_clips:
            ps = clip.get('partners', [])
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    key = tuple(sorted([ps[i], ps[j]]))
                    edge_weights[key]["clips"] += 1
                    edge_weights[key]["clips_meta"].append(clip)
        for video in all_videos:
            ps = video.get('partners', [])
            for i in range(len(ps)):
                for j in range(i + 1, len(ps)):
                    key = tuple(sorted([ps[i], ps[j]]))
                    edge_weights[key]["films"] += 1
                    edge_weights[key]["films_meta"].append(video)

        edges = []
        for (p1, p2), counts in edge_weights.items():
            total = counts["clips"] + counts["films"]
            if total == 0:
                continue
            # Color edge by most common playlist among shared clips/films
            playlist_counter = Counter()
            for c in counts["clips_meta"]:
                playlist_counter[c.get('playlist_name', 'Unknown')] += 1
            for f in counts["films_meta"]:
                playlist_counter[f.get('playlist_name', 'Unknown')] += 1
            playlist, _ = playlist_counter.most_common(1)[0] if playlist_counter else ('Unknown', 0)
            color = playlist_colors.get(playlist, "#888")
            edge_data = {
                "id": f"{p1}_{p2}",
                "source": p1,
                "target": p2,
                "weight": total,
                "color": color,
                "title": f"Shared clips: {counts['clips']}, Shared films: {counts['films']}",
                "clips_meta": counts["clips_meta"],
                "films_meta": counts["films_meta"],
            }
            edges.append({"data": edge_data})

        elements = nodes + edges
        elements_json = json.dumps(elements)

        # Add the container to the main body, not shadow DOM
        ui.add_body_html("<div id='cy' style='height: 700px; width: 100%; border: 1px solid #ccc;'></div>")
        ui.add_body_html("<div id='meta' style='margin-top:10px; min-height:40px;'></div>")
        ui.add_body_html(f"""
        <script src="https://unpkg.com/cytoscape@3.24.0/dist/cytoscape.min.js"></script>
        <script>
            function renderCytoscape() {{
                if (typeof cytoscape === 'undefined' || !document.getElementById('cy')) {{
                    setTimeout(renderCytoscape, 100);
                    return;
                }}
                const elements = {elements_json};
                const cy = cytoscape({{
                    container: document.getElementById('cy'),
                    elements: elements,
                    style: [
                        {{
                            selector: 'node',
                            style: {{
                                'label': 'data(label)',
                                'background-color': 'data(color)',
                                'width': 'mapData(count, 1, 100, 20, 50)',
                                'height': 'mapData(count, 1, 100, 20, 50)',
                                'text-valign': 'center',
                                'text-halign': 'center',
                                'color': '#fff',
                                'font-size': 16,
                                'text-outline-width': 2,
                                'text-outline-color': '#222',
                                'shadow-blur': 0,
                                'shadow-color': '#000',
                                'shadow-opacity': 0
                            }}
                        }},
                        {{
                            selector: 'node.high-usage',
                            style: {{
                                'shadow-blur': 30,
                                'shadow-color': '#FFD700',
                                'shadow-opacity': 0.7
                            }}
                        }},
                        {{
                            selector: 'edge',
                            style: {{
                                'width': 'mapData(weight, 1, 100, 1, 10)',
                                'line-color': 'data(color)',
                                'curve-style': 'bezier',
                                'opacity': 0.8
                            }}
                        }}
                    ],
                    layout: {{
                        name: 'circle',
                        padding: 20
                    }}
                }});

                // Show metadata on hover/click
                function showMeta(html) {{
                    document.getElementById('meta').innerHTML = html;
                }}

                cy.on('mouseover', 'node', function(evt) {{
                    const d = evt.target.data();
                    showMeta(`<b>Partner:</b> ${d.label}<br><b>Playlist:</b> ${d.playlist}<br><b>Usage:</b> ${d.count}`);
                }});
                cy.on('mouseout', 'node', function(evt) {{
                    showMeta('');
                }});
                cy.on('tap', 'node', function(evt) {{
                    const d = evt.target.data();
                    showMeta(`<b>Partner:</b> ${d.label}<br><b>Playlist:</b> ${d.playlist}<br><b>Usage:</b> ${d.count}`);
                }});
                cy.on('mouseover', 'edge', function(evt) {{
                    const d = evt.target.data();
                    let html = `<b>Edge:</b> ${{d.source}} - ${{d.target}}<br><b>Shared clips:</b> ${{d.weight}}<br>`;
                    if (d.clips_meta && d.clips_meta.length)
                        html += `<b>Clips:</b><ul>` + d.clips_meta.map(c => `<li>${{c.title || ''}}</li>`).join('') + `</ul>`;
                    if (d.films_meta && d.films_meta.length)
                        html += `<b>Films:</b><ul>` + d.films_meta.map(f => `<li>${{f.title || ''}}</li>`).join('') + `</ul>`;
                    showMeta(html);
                }});
                cy.on('mouseout', 'edge', function(evt) {{
                    showMeta('');
                }});
                cy.on('tap', 'edge', function(evt) {{
                    const d = evt.target.data();
                    let html = `<b>Edge:</b> ${{d.source}} - ${{d.target}}<br><b>Shared clips:</b> ${{d.weight}}<br>`;
                    if (d.clips_meta && d.clips_meta.length)
                        html += `<b>Clips:</b><ul>` + d.clips_meta.map(c => `<li>${{c.title || ''}}</li>`).join('') + `</ul>`;
                    if (d.films_meta && d.films_meta.length)
                        html += `<b>Films:</b><ul>` + d.films_meta.map(f => `<li>${{f.title || ''}}</li>`).join('') + `</ul>`;
                    showMeta(html);
                }});
            }}
            renderCytoscape();
        </script>
        """)
