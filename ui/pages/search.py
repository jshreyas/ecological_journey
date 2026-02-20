import time
from datetime import datetime
from typing import Any, Dict, List

from nicegui import ui

from ui.utils.query_cache_service import QueryCacheService
from ui.utils.search_index_service import SearchIndexService
from ui.utils.user_context import User, with_user_context
from ui.utils.utils import format_time, navigate_to_film

# ============================================================
# QUERY PARSER
# ============================================================


class QueryParser:

    DEFAULT_TEMPLATE = "@playlist an\n@type video clip anchor\n@search *"

    @staticmethod
    def parse(text: str) -> Dict[str, Any]:
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


# ============================================================
# SEARCH STATE
# ============================================================


class SearchState:

    def __init__(self, user: User | None):
        self.user = user
        self.user_id = user.id if user else "default_user"

        self.index_service = SearchIndexService()
        self.query_cache = QueryCacheService()

        self.query_text = QueryParser.DEFAULT_TEMPLATE
        self.rows_data = {}

        self.metrics = {}
        self.results: List[Dict] = []

    def initialize(self):
        self.index_service.build_and_cache_index()
        index_data = self.index_service.get_active_index()
        if not index_data:
            return False
        self.rows_data = index_data["rows"]
        return True


# ============================================================
# SEARCH ENGINE
# ============================================================


class SearchEngine:

    @staticmethod
    def apply_date_markers(results: List[Dict]) -> List[Dict]:
        last_date = None
        for r in results:
            if r["date"] != last_date:
                r["_is_date_start"] = True
                r["_date_label"] = datetime.fromisoformat(r["date"].replace("Z", "+00:00")).strftime("%b %d, %Y")
                last_date = r["date"]
            else:
                r["_is_date_start"] = False
        return results

    @staticmethod
    def execute(state: SearchState):

        start_time = time.time()
        raw_query = state.query_text.strip()
        parsed = QueryParser.parse(raw_query)
        cache_key = raw_query.lower()

        cached = state.query_cache.get(state.user_id, cache_key)

        if cached:
            result_ids = cached["ids"]
            result_rows = [state.rows_data[rid] for rid in result_ids if rid in state.rows_data]
            metrics = cached["metrics"]
        else:
            result_rows = list(state.rows_data.values())

            # Playlist filter
            if parsed["playlist"]:
                playlist_text = parsed["playlist"].lower()
                result_rows = [r for r in result_rows if playlist_text in r["playlist"].lower()]

            # Type filter
            if parsed["type"]:
                result_rows = [r for r in result_rows if r["type"] in parsed["type"]]

            # Text search
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
                "query_time": f"{int((time.time() - start_time) * 1000)}ms",
            }

            state.query_cache.set(
                state.user_id,
                cache_key,
                {
                    "ids": [r["id"] for r in result_rows],
                    "metrics": metrics,
                },
            )

        # Formatting layer (presentation shaping)
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

        result_rows = SearchEngine.apply_date_markers(result_rows)

        state.results = result_rows
        state.metrics = metrics


# ============================================================
# SEARCH LAYOUT (UI ONLY)
# ============================================================


class SearchLayout:

    def __init__(self, state: SearchState):
        self.state = state

        self.query_input = None
        self.metadata_label = None
        self.results_table = None

    def build(self):

        with ui.column().classes("w-full").style("height:85vh"):

            self.query_input = (
                ui.textarea(
                    value=self.state.query_text,
                    placeholder=QueryParser.DEFAULT_TEMPLATE,
                )
                .props("autogrow dense outlined")
                .classes("w-full")
            )

            self.metadata_label = ui.label("").classes("text-grey-8 text-sm")

            self.results_table = (
                ui.table(
                    columns=self._columns(),
                    rows=[],
                    row_key="id",
                    pagination={"rowsPerPage": 50},
                )
                .props("hide-header")
                .classes("w-full")
                .style("height:85vh")
            )

            self._attach_slots()

    def _columns(self):
        return [
            {"name": "thumbnail", "label": "Thumbnail", "field": "thumbnail", "align": "left", "style": "width:80px;"},
            {"name": "title", "label": "Title", "field": "title", "align": "left", "style": "width: 40%;"},
            {"name": "duration", "label": "Duration", "field": "duration", "align": "left", "style": "width: 15%;"},
            {
                "name": "description",
                "label": "Description",
                "field": "description",
                "align": "left",
                "style": "width: 50%;",
            },
        ]

    def _attach_slots(self):
        self.results_table.add_slot(
            "body",
            r"""
            <q-tr>
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

                <q-td style="max-width:50%; white-space:normal;">
                    <div v-if="props.row._is_date_start"
                        class="text-grey-5 text-xs q-mb-xs">
                        {{ props.row._date_label }}
                    </div>

                    <div class="row items-center">
                        <div :style="{ width: (props.row._level * 24) + 'px' }"></div>

                        <q-icon v-if="props.row._type === 'video'" name="movie" color="primary" class="q-mr-sm"/>
                        <q-icon v-else-if="props.row._type === 'anchor'" name="anchor" color="orange" class="q-mr-sm"/>
                        <q-icon v-else-if="props.row._type === 'clip'" name="content_cut" color="green" class="q-mr-sm"/>

                        <div>{{ props.row.title }}</div>
                    </div>
                </q-td>

                <q-td>{{ props.row.duration || '' }}</q-td>
                <q-td style="max-width:50%; overflow:auto; white-space:normal;">
                    {{ props.row.description }}
                </q-td>
            </q-tr>
            """,
        )

    # ----- Render Updates -----

    def update(self):
        self.results_table.rows = self.state.results
        self.results_table.update()
        self.results_table.props("pagination.page=1")

        m = self.state.metrics
        self.metadata_label.set_text(
            f"Training Days: {m['training_days']} | "
            f"Playlists: {m['playlists']} | "
            f"Videos: {m['videos']} | "
            f"Anchors: {m['anchors']} | "
            f"Clips: {m['clips']} | "
            f"Query time: {m['query_time']}"
        )


# ============================================================
# PAGE COMPOSITION ROOT
# ============================================================


@with_user_context
def search_page(user: User | None):

    state = SearchState(user)

    if not state.initialize():
        ui.label("Search index unavailable")
        return

    layout = SearchLayout(state)
    layout.build()

    def perform_search():
        state.query_text = layout.query_input.value
        SearchEngine.execute(state)
        layout.update()

    def on_play(e):
        row = e.args
        navigate_to_film(row["video_id"])
        ui.notify(f"Playing {row['type']}")

    layout.results_table.on("play", on_play)
    layout.query_input.on("keydown.enter.exact.prevent", lambda e: perform_search())

    perform_search()
