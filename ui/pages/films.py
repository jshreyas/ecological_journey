from pages.components.media import render_media_page
from utils.user_context import User, with_user_context
from utils.utils_api import load_videos


@with_user_context
def films_page(user: User | None):
    render_media_page(
        title="🎬 Films, Films, and more Films!",
        data_loader=load_videos,
        show_save_button=False,
        show_clips_count=True,
    )
