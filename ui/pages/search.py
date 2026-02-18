import time
from datetime import datetime

from nicegui import ui

from ui.utils.query_cache_service import QueryCacheService
from ui.utils.search_index_service import SearchIndexService
from ui.utils.user_context import User, with_user_context
from ui.utils.utils import format_time, navigate_to_film


@with_user_context
def search_page(user: User | None):

    index_service = SearchIndexService()
    query_cache = QueryCacheService()

    user_id = user.id if user else "default_user"

    index_service.build_and_cache_index()
    index_data = index_service.get_active_index()

    if not index_data:
        ui.label("Search index unavailable")
        return

    rows_data = index_data["rows"]

    # -------------------------
    # RESULT TABLE COLUMNS
    # -------------------------

    result_columns = [
        {
            "name": "thumbnail",
            "label": "Thumbnail",
            "field": "thumbnail",
            "align": "left",
            "style": "width:80px;",
        },
        {
            "name": "title",
            "label": "Title",
            "field": "title",
            "align": "left",
            "style": "width: 40%;",
        },
        {
            "name": "duration",
            "label": "Duration",
            "field": "duration",
            "align": "left",
            "style": "width: 15%;",
        },
        {
            "name": "description",
            "label": "Description",
            "field": "description",
            "align": "left",
            "style": "width: 50%;",
        },
    ]

    DEFAULT_TEMPLATE = "@playlist \n@type video clip anchor\n@search *"

    search_query = {"value": DEFAULT_TEMPLATE}
    metrics_state = {"value": {}}

    # -------------------------
    # QUERY PARSING
    # -------------------------

    def parse_query_template(text: str):
        lines = text.splitlines()
        parsed = {"playlist": None, "type": None, "search": None}

        for line in lines:
            line = line.strip()
            if line.startswith("@playlist"):
                parsed["playlist"] = line.replace("@playlist", "").strip()
            elif line.startswith("@type"):
                parsed["type"] = line.replace("@type", "").strip().split()
            elif line.startswith("@search"):
                parsed["search"] = line.replace("@search", "").strip()

        return parsed

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

    # -------------------------
    # SEARCH + METADATA WRAPPER
    # -------------------------
    with ui.column().classes("w-full").style("height:85vh"):

        # SEARCH INPUT
        query_input = (
            ui.textarea(
                value=search_query["value"],
                placeholder="@playlist \n@type video clip anchor\n@search *",
            )
            .props("autogrow dense outlined")
            .classes("w-full")
        )
        # METADATA FOOTER
        metadata_label = ui.label("").classes("text-grey-8 text-sm")
        # RESULTS TABLE
        # -------------------------
        # INNER RESULTS TABLE
        # -------------------------

        results_table = (
            ui.table(
                columns=result_columns,
                rows=[],
                row_key="id",
                pagination={"rowsPerPage": 50},
            )
            .props("hide-header")
            .classes("w-full")
            .style("height:85vh")
        )

        results_table.add_slot(
            "body",
            r"""
            <q-tr>

                <!-- THUMBNAIL -->
                <q-td style="width:90px; min-width:90px; padding:6px; cursor:pointer;"
                    @click="() => $parent.$emit('play', props.row)">
                    <q-img
                        v-if="props.row.thumbnail"
                        :src="props.row.thumbnail"
                        style="width:72px; height:40px; border-radius:4px;"
                        fit="cover"
                        loading="lazy"
                        transition="none"
                    />
                </q-td>

                <q-td>
                    <div v-if="props.row._is_date_start"
                        class="text-grey-5 text-xs q-mb-xs">
                        {{ props.row._date_label }}
                    </div>

                    <div class="row items-center">

                        <div :style="{ width: (props.row._level * 24) + 'px' }"></div>

                        <q-icon
                            v-if="props.row._type === 'video'"
                            name="movie"
                            color="primary"
                            class="q-mr-sm"
                        />
                        <q-icon
                            v-else-if="props.row._type === 'anchor'"
                            name="anchor"
                            color="orange"
                            class="q-mr-sm"
                        />
                        <q-icon
                            v-else-if="props.row._type === 'clip'"
                            name="content_cut"
                            color="green"
                            class="q-mr-sm"
                        />

                        <div>{{ props.row.title }}</div>
                    </div>
                </q-td>

                <q-td>{{ props.row.duration || '' }}</q-td>
                <q-td style="max-width:50%; overflow:auto; white-space:normal;">{{ props.row.description }}</q-td>

            </q-tr>
            """,
        )

    # -------------------------
    # SEARCH EXECUTION
    # -------------------------

    def perform_search():

        start_time = time.time()
        raw_query = query_input.value.strip()
        search_query["value"] = raw_query

        parsed = parse_query_template(raw_query)
        cache_key = raw_query.lower()

        cached = query_cache.get(user_id, cache_key)

        if cached:
            result_ids = cached["ids"]
            result_rows = [rows_data[rid] for rid in result_ids if rid in rows_data]
            metrics = cached["metrics"]
        else:
            result_rows = list(rows_data.values())

            if parsed["playlist"]:
                playlist_text = parsed["playlist"].lower()
                result_rows = [r for r in result_rows if playlist_text in r["playlist"].lower()]

            if parsed["type"]:
                result_rows = [r for r in result_rows if r["type"] in parsed["type"]]

            if parsed["search"] and parsed["search"] != "*":
                search_text = parsed["search"].lower()
                result_rows = [
                    r
                    for r in result_rows
                    if search_text in r["title"].lower() or search_text in r["description"].lower()
                ]

            result_rows.sort(key=lambda x: x["date"], reverse=True)

            metrics = {
                "training_days": len(set(r["date"] for r in result_rows)),
                "playlists": len(set(r["playlist"] for r in result_rows)),
                "videos": len([r for r in result_rows if r["type"] == "video"]),
                "anchors": len([r for r in result_rows if r["type"] == "anchor"]),
                "clips": len([r for r in result_rows if r["type"] == "clip"]),
                "query_time": f"{int((time.time() - start_time)*1000)}ms",
            }

            query_cache.set(
                user_id,
                cache_key,
                {
                    "ids": [r["id"] for r in result_rows],
                    "metrics": metrics,
                },
            )

        result_rows = apply_date_markers(result_rows)

        types_present = set(r["type"] for r in result_rows)

        for r in result_rows:
            r["thumbnail"] = f"https://img.youtube.com/vi/{r['video_id']}/0.jpg"

            if not r["description"]:
                r["description"] = ""

            if r["type"] == "anchor":
                r["duration"] = ""
            else:
                if not isinstance(r["duration"], str):
                    r["duration"] = format_time(int(r["duration"]))

            r["_type"] = r["type"]

            if len(types_present) == 1:
                r["_level"] = 0
            else:
                r["_level"] = 0 if r["type"] == "video" else 1

        # 🔥 Only update INNER table
        results_table.rows = result_rows
        results_table.update()

        # 🔥 Reset to first page on new search
        results_table.props("pagination.page=1")

        metrics_state["value"] = metrics

        metadata_label.set_text(
            f"Training Days: {metrics['training_days']} | "
            f"Playlists: {metrics['playlists']} | "
            f"Videos: {metrics['videos']} | "
            f"Anchors: {metrics['anchors']} | "
            f"Clips: {metrics['clips']} | "
            f"Query time: {metrics['query_time']}"
        )

    # -------------------------
    # EVENTS
    # -------------------------

    def on_play(e):
        row = e.args
        navigate_to_film(row["video_id"])
        ui.notify(f"Playing {row['type']}")

    results_table.on("play", on_play)
    query_input.on("keydown.enter", lambda e: perform_search())

    perform_search()
