from pages.media_components import render_media_page
from utils.user_context import User, with_user_context
from utils.utils import navigate_to_film, parse_query_expression
from utils.utils_api import load_clips, save_cliplist


@with_user_context
def clips_page(user: User | None):
    render_media_page(
        title="🎬 Clips, Clips, and more Clips!",
        data_loader=load_clips,
        parse_query_expression=parse_query_expression,
        navigate_to_film=navigate_to_film,
        save_cliplist=save_cliplist,
        user=user,
        show_save_button=True,
        show_clips_count=False,
    )
