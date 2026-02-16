from datetime import datetime

from nicegui import ui

from ui.utils.query_cache_service import QueryCacheService
from ui.utils.search_index_service import SearchIndexService
from ui.utils.user_context import User, with_user_context


@with_user_context
def search_page(user: User | None):

    index_service = SearchIndexService()
    query_cache = QueryCacheService()

    user_id = user.id if user else "default_user"

    # Ensure index exists
    index_service.build_and_cache_index()
    index_data = index_service.get_active_index()

    if not index_data:
        ui.label("Search index unavailable")
        return

    rows_data = index_data["rows"]

    columns = [
        {"name": "title", "label": "Title", "field": "title"},
        {"name": "type", "label": "Type", "field": "type"},
        {"name": "duration", "label": "Duration", "field": "duration"},
        {"name": "description", "label": "Description", "field": "description"},
    ]

    search_query = {"value": "*"}

    # ----------------------------------------
    # Date Sticky Marker Logic
    # ----------------------------------------

    def apply_date_markers(results):
        last_date = None
        for r in results:
            if r["date"] != last_date:
                r["_is_date_start"] = True
                r["_date_label"] = datetime.fromisoformat(r["date"].replace("Z", "+00:00")).strftime("%b %d, %Y")
                last_date = r["date"]
            else:
                r["_is_date_start"] = False
        return results

    # ----------------------------------------
    # Search Execution
    # ----------------------------------------

    def perform_search():

        q = search_query["value"].strip().lower()

        # Wildcard = show all
        if q == "*" or not q:
            result_rows = list(rows_data.values())
        else:
            cached = query_cache.get(user_id, q)
            if cached:
                result_rows = [rows_data[rid] for rid in cached if rid in rows_data]
            else:
                result_rows = [
                    r
                    for r in rows_data.values()
                    if q in r["title"].lower() or q in r["description"].lower() or q in r["playlist"].lower()
                ]
                query_cache.set(
                    user_id,
                    q,
                    [r["id"] for r in result_rows],
                )

        result_rows.sort(key=lambda x: x["date"], reverse=True)

        result_rows = apply_date_markers(result_rows)

        footer = {
            "id": "__footer__",
            "_is_footer": True,
            "title": f"{len(result_rows)} results for '{q}'",
        }

        header = {
            "id": "__header__",
            "_is_footer": True,
            "title": q,
        }

        table.rows = [header] + result_rows + [footer]
        table.update()

    # ----------------------------------------
    # UI
    # ----------------------------------------

    with ui.column().classes("w-full"):

        seed_queries = ["*", "open mats", "heroes", "armbar", "sparring"]

        with ui.row():
            for seed in seed_queries:
                ui.button(
                    seed,
                    on_click=lambda s=seed: set_seed_query(s),
                )

        table = ui.table(
            columns=columns,
            rows=[],
            row_key="id",
        ).classes("w-full")

        # ----------------------------------------
        # Embedded Search Row (INSIDE TABLE)
        # ----------------------------------------

        query_input = ui.input(
            value="*",
            placeholder="Search...",
            on_change=lambda e: update_query(e.value),
        ).classes("w-full")

        def update_query(value):
            search_query["value"] = value
            perform_search()

        def set_seed_query(value):
            query_input.value = value
            search_query["value"] = value
            perform_search()

        table.add_slot(
            "top-row",
            """
            <q-tr>
              <q-td colspan="100%">
                <div id="query-slot"></div>
              </q-td>
            </q-tr>
            """,
        )

        # Mount the input into slot
        query_input.move(table)

        # ----------------------------------------
        # Proper Body Rendering
        # ----------------------------------------

        table.add_slot(
            "body",
            """
            <q-tr v-if="props.row._is_footer">
                <q-td colspan="100%" class="text-grey-6 text-sm text-center">
                    {{ props.row.title }}
                </q-td>
            </q-tr>

            <q-tr v-else>

                <q-td>
                    <div v-if="props.row._is_date_start"
                         class="text-grey-5 text-xs q-mb-xs">
                        {{ props.row._date_label }}
                    </div>
                    {{ props.row.title }}
                </q-td>

                <q-td>
                    {{ props.row.type }}
                </q-td>

                <q-td>
                    {{ props.row.duration || '' }}
                </q-td>

                <q-td>
                    {{ props.row.description }}
                </q-td>

            </q-tr>
            """,
        )

    # Run default wildcard search on load
    perform_search()
