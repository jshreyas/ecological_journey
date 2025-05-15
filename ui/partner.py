from nicegui import ui
from utils_api import get_all_partners, find_clips_by_partner
from utils import format_time, embed_youtube_player


def partner_page():
    ui.label('🤼 Meet our Training Partners!').classes('text-2xl font-bold')

#     partners = get_all_partners()
#     if not partners:
#         ui.label('No partners found!').classes('text-red-500')
#         return

#     selected_partner = None
#     all_clips = []
#     label_checkboxes = {}
#     player_container = ui.column().classes('w-full mt-4')

#     def get_all_labels(clips):
#         labels_set = set()
#         has_no_label = False
#         for clip in clips:
#             labels = clip.get("labels") or []
#             if labels:
#                 labels_set.update(labels)
#             else:
#                 has_no_label = True
#         all_labels = sorted(labels_set)
#         if has_no_label:
#             all_labels.append("No Label")
#         return all_labels

#     def is_clip_visible(clip, selected_labels):
#         labels = clip.get("labels") or []
#         is_empty = not labels
#         if is_empty and "No Label" in selected_labels:
#             return True
#         return any(label in selected_labels for label in labels)

#     def update_clip_buttons():
#         clips_column.clear()

#         selected_labels = [label for label, cb in label_checkboxes.items() if cb.value]

#         visible_clips = [clip for clip in all_clips if is_clip_visible(clip, selected_labels)]

#         with clips_column:
#             for i, clip in enumerate(visible_clips):
#                 title = clip.get('title', f'Clip {i+1}')
#                 start_time = format_time(clip['start'])
#                 end_time = format_time(clip['end'])
#                 label = f"{title} ({start_time} → {end_time})"

#                 def make_on_click(v):
#                     def on_click():
#                         player_container.clear()
#                         with player_container:
#                             embed_youtube_player(
#                                 v["video_id"],
#                                 start=v["start"],
#                                 end=v["end"],
#                                 speed=1.0,
#                             )
#                     return on_click

#                 ui.button(label, on_click=make_on_click(clip)).classes(
#                     'w-full text-left p-4 bg-gray-100 rounded shadow-md hover:bg-gray-200'
#                 )

#     def update_clips(partner):
#         nonlocal all_clips, label_checkboxes
#         clips_column.clear()
#         filters_column.clear()
#         player_container.clear()
#         label_checkboxes = {}

#         all_clips = find_clips_by_partner(partner)
#         all_labels = get_all_labels(all_clips)

#         with filters_column:
#             ui.label('🎯 Filter by Labels').classes('text-lg font-bold')
#             for label in all_labels:
#                 cb = ui.checkbox(label, value=True, on_change=update_clip_buttons)
#                 label_checkboxes[label] = cb

#         update_clip_buttons()

#     def on_partner_change(e):
#         nonlocal selected_partner
#         selected_partner = e.value
#         update_clips(selected_partner)

#     ui.select(partners, clearable=True, on_change=on_partner_change)

#     with ui.splitter(horizontal=False, reverse=False, value=80).classes('w-full mt-4') as splitter:
#         with splitter.before:
#             clips_column = ui.column().classes('w-full gap-2')
#         with splitter.after:
#             filters_column = ui.column().classes('ml-2 gap-2')
#         with splitter.separator:
#             ui.icon('filter_alt').classes('text-blue')

#     update_clips(selected_partner)


# partner_page()
