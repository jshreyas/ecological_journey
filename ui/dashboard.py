from nicegui import ui
from utils_api import load_videos
import datetime
from collections import Counter
from itertools import chain


def home_page():
    ui.label("🤼 Grappling Portfolio Dashboard").classes('text-2xl font-bold mb-4')

    videos = load_videos()
    if not videos:
        ui.notify('⚠️ No videos found!')
        return

    # Process data
    dates = [datetime.datetime.strptime(v['date'], "%Y-%m-%dT%H:%M:%SZ") for v in videos]
    total_videos = len(videos)
    unique_partners = len(set(p for v in videos for p in v['partners']))
    unique_positions = len(set(p for v in videos for p in v['positions']))

    # Stats
    with ui.row().classes('w-full gap-4'):
        with ui.card().classes('p-4').tight():
            ui.label(f"📹 Total Videos: {total_videos}").classes('text-lg')
        with ui.card().classes('p-4').tight():
            ui.label(f"🧑‍🤝‍🧑 Training Partners: {unique_partners}").classes('text-lg')
        with ui.card().classes('p-4').tight():
            ui.label(f"📍 Unique Positions: {unique_positions}").classes('text-lg')

    # Activity over time
    ui.label("📊 Activity Over Time").classes('text-xl mt-8 mb-2')

    date_counts = Counter(d.date() for d in dates)
    sorted_dates = sorted(date_counts.keys())
    chart_data = {
        'labels': [d.strftime('%Y-%m-%d') for d in sorted_dates],
        'datasets': [{
            'label': 'Video count',
            'data': [date_counts[d] for d in sorted_dates],
        }]
    }
    ui.echart({
        'title': {'left': 'center'},
        'tooltip': {'trigger': 'axis'},
        'xAxis': {'type': 'category', 'data': chart_data['labels']},
        'yAxis': {'type': 'value'},
        'series': [{
            'type': 'bar',
            'data': chart_data['datasets'][0]['data'],
        }]
    }).classes('w-full h-80')
