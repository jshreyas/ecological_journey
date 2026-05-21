from nicegui import ui

from ui.data.crud import clear_cache
from ui.utils.user_context import User, with_user_context


@with_user_context
def about_page(user: User | None):
    # TODO: make it available to other pages, can this be added as decorator?
    if ui.context.client.request.query_params.get("clear_cache", "") == "true":
        clear_cache()
    with ui.column().classes("w-full max-w-4xl mx-auto p-6"):

        def add_row():
            new_id = max((dx["id"] for dx in aggrid.options["rowData"]), default=-1) + 1
            aggrid.options["rowData"].append({"id": new_id, "name": "New name", "age": None})
            ui.notify(f"Added row with ID {new_id}")

        def handle_cell_value_change(e):
            new_row = e.args["data"]
            ui.notify(f'Updated row to: {e.args["data"]}')
            aggrid.options["rowData"][:] = [
                row | new_row if row["id"] == new_row["id"] else row for row in aggrid.options["rowData"]
            ]

        async def delete_selected():
            selected_id = [row["id"] for row in await aggrid.get_selected_rows()]
            aggrid.options["rowData"][:] = [row for row in aggrid.options["rowData"] if row["id"] not in selected_id]
            ui.notify(f"Deleted row with ID {selected_id}")

        aggrid = ui.aggrid(
            {
                "columnDefs": [
                    {"field": "name", "editable": True, "sortable": True},
                    {"field": "age", "editable": True},
                    {"field": "id"},
                ],
                "rowData": [
                    {"id": 0, "name": "Alice", "age": 18},
                    {"id": 1, "name": "Bob", "age": 21},
                    {"id": 2, "name": "Carol", "age": 20},
                ],
                "rowSelection": {"mode": "multiRow"},
                "stopEditingWhenCellsLoseFocus": True,
            }
        ).on("cellValueChanged", handle_cell_value_change)

        ui.button("Delete selected", on_click=delete_selected)
        ui.button("New row", on_click=add_row)

        ui.label("🥋 About This Platform").classes("text-3xl font-bold mb-4")

        ui.markdown(
            """
        ### Empowering the Martial Artist

        This platform is an open-source ecosystem for martial artists to **track**,
        **vlog**, and **share** their training journeys.

        Whether you're a beginner rolling your first rounds, a capoeirista exploring
        the flow, or a cross-discipline athlete, this space is yours.

        We believe in **empowering students** to own their journey, reflect with
        confidence, and build a **living portfolio** of their evolving skills.
        """
        )

        ui.label("🔍 A Familiar Comparison, Made Martial").classes("text-xl font-semibold")
        ui.markdown(
            "**Think of it like GitHub for your training — with Strava's community "
            "spirit — all grounded in the soul of a dojo.**"
        )

        with ui.row().classes("gap-4 flex-wrap"):
            with ui.card().classes("flex-1 min-w-[250px]"):
                ui.label("🧠 GitHub").classes("text-lg font-bold")
                ui.markdown(
                    """
                GitHub is where developers **track code versions** and collaborate on projects.

                Here, it means:
                - Track your training like **version history**
                - Review past sessions and progress
                - Collaborate with partners like teammates in a shared repo
                """
                )

            with ui.card().classes("flex-1 min-w-[250px]"):
                ui.label("💪 Strava").classes("text-lg font-bold")
                ui.markdown(
                    """
                Strava is a social app for **athletes to log workouts** and share with a community.

                Here, it means:
                - Log your sessions and milestones
                - Feel the support of a growing **training tribe**
                - Celebrate your peers, and stay inspired
                """
                )

            with ui.card().classes("flex-1 min-w-[250px]"):
                ui.label("🧘 The Dojo").classes("text-lg font-bold")
                ui.markdown(
                    """
                A dojo is a **sacred training space** — more than just a gym.

                Here, it means:
                - This is about **ritual, reflection, and rhythm**
                - Build not just skill, but **character and clarity**
                - Honor your path — and the path of others
                """
                )

        ui.separator().classes("my-2")

        ui.markdown(
            """
        ### 🧠 Inspiration

        This project was born out of two needs:

        1. **Personal insight** — As martial artists, we often forget how far we've come.
        This tool helps you **see the arc** of your own growth.
        2. **Community learning** — Training isn't just about what you learn from the coach —
        it's about **what we teach each other**, by playing, failing, and reflecting.

        It's also a love letter to all the late-night YouTube video breakdowns, the after-class
        chats, the sparring sessions that changed our game, and the feeling of being part of
        something **bigger than ourselves**.
        """
        )

        ui.separator()

        ui.markdown(
            """
        ### 🧘‍♂️ Philosophy

        Martial arts isn't just combat — it's a way of **being**.

        We see martial arts as a **living ecosystem** of body, mind, and community. This platform exists to:

        - Help you build an **intentional practice**
        - Support **cross-training and open learning**
        - Celebrate not just results, but **process and progression**
        - Create a sense of **ritual and reflection**, the way ancient martial traditions did

        This is a space for **students of movement**. For those who flow between disciplines.
        For those who want to leave a trail behind — not just for themselves, but for the next traveler.

        We train. We log. We grow. Together.
        """
        )

        ui.label("💡 Open source. Forever free. Forever yours.").classes(
            "bg-blue-100 text-blue-900 p-4 rounded shadow mt-4"
        )
