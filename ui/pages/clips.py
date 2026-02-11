from ui.pages.components.media import render_media_page
from ui.utils.user_context import User, with_user_context
from ui.utils.utils_api import load_clips, save_cliplist


@with_user_context
def clips_page(user: User | None):
    render_media_page(
        title="🎬 Clips, Clips, and more Clips!",
        data_loader=load_clips,
        save_cliplist=save_cliplist,
        user=user,
        show_save_button=True,
        show_clips_count=False,
    )
