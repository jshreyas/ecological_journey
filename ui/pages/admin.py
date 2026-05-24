from nicegui import ui

from ui.data.crud import clear_cache
from ui.utils.user_context import User, with_user_context


@with_user_context
def admin_page(user: User | None):

    if not user:
        ui.label("Unauthorized")
        return

    # if user.role != "service":
    #     ui.label("Forbidden")
    #     return

    async def handle_clear_cache():
        try:
            clear_cache(token=user.token)

            ui.notify(
                "All caches cleared",
                type="positive",
            )

        except Exception as e:
            ui.notify(
                f"Failed to clear cache: {e}",
                type="negative",
            )

    ui.label("Admin")

    ui.button(
        "Clear All Caches",
        on_click=handle_clear_cache,
    )
