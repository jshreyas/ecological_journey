from pages.media_components import render_media_page
from utils.utils import navigate_to_film, parse_query_expression
from utils.utils_api import load_videos


def films_page():
    render_media_page(
        title="🎬 Films, Films, and more Films!",
        data_loader=load_videos,
        parse_query_expression=parse_query_expression,
        navigate_to_film=navigate_to_film,
        show_save_button=False,
        show_clips_count=True,
    )
