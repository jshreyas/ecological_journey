from pages.media_components import render_media_page
from utils.utils_api import load_videos


def films_page():
    render_media_page(
        title="🎬 Films, Films, and more Films!",
        data_loader=load_videos,
        show_save_button=False,
        show_clips_count=True,
    )
