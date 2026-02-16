import time
from datetime import datetime

from nicegui import ui

from ui.utils.query_cache_service import QueryCacheService
from ui.utils.search_index_service import SearchIndexService
from ui.utils.user_context import User, with_user_context
from ui.utils.utils import format_time


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

    # ----------------------------------------
    # Columns
    # ----------------------------------------

    # columns = [
    #     {"name": "title", "label": "Title", "field": "title"},
    #     {"name": "type", "label": "Type", "field": "type"},
    #     {"name": "duration", "label": "Duration (s)", "field": "duration"},
    #     {"name": "description", "label": "Description", "field": "description"},
    # ]

    columns = [
        {
            "name": "title",
            "label": "Title",
            "field": "title",
            "align": "left",
            "style": "width: 35%;",
        },
        {
            "name": "duration",
            "label": "Duration (s)",
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

    # ----------------------------------------
    # Default Template
    # ----------------------------------------

    DEFAULT_TEMPLATE = "@playlist a\n" "@type video clip anchor\n" "@search *"

    search_query = {"value": DEFAULT_TEMPLATE}

    # ----------------------------------------
    # Query Parsing
    # ----------------------------------------

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

    # ----------------------------------------
    # Date Markers
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
    # Search Logic
    # ----------------------------------------

    def perform_search():

        start_time = time.time()
        raw_query = search_query["value"].strip()
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

        # add tree metadata (MVP simple: flat unless mixed types)
        types_present = set(r["type"] for r in result_rows)

        for r in result_rows:
            if r["type"] == "anchor":
                r["duration"] = ""
            else:
                r["duration"] = format_time(int(r["duration"]))
            r["_type"] = r["type"]

            # If only one type returned → flat
            if len(types_present) == 1:
                r["_level"] = 0
            else:
                # Video higher level
                if r["type"] == "video":
                    r["_level"] = 0
                else:
                    r["_level"] = 1

        # Build unified table rows
        table.rows = (
            [
                {
                    "id": "__search__",
                    "_is_search": True,
                    "query": raw_query,
                }
            ]
            + result_rows
            + [
                {
                    "id": "__footer__",
                    "_is_footer": True,
                    "metrics": metrics,
                }
            ]
        )

        table.update()

    # ----------------------------------------
    # UI
    # ----------------------------------------

    table = (
        ui.table(
            columns=columns,
            rows=[],
            row_key="id",
        )
        .props("hide-header")
        .classes("w-full my-sticky-table")
        .style("height:85vh")
    )

    # ----------------------------------------
    # Body Slot (Search Row + Results + Footer)
    # ----------------------------------------

    table.add_slot(
        "body",
        r"""
        <!-- SEARCH ROW -->
        <q-tr v-if="props.row._is_search" class="bg-grey-2">
          <q-td colspan="100%">
            <div style="white-space: pre-wrap; cursor: pointer;">
              {{ props.row.query }}
            </div>

            <q-popup-edit
              v-model="props.row.query"
              v-slot="scope"
              @update:model-value="(val) => $parent.$emit('search-update', val)"
            >
            <div class="row q-gutter-sm">
                        <div class="col">
                        <q-input
                            v-model="scope.value"
                            type="textarea"
                            dense
                            autogrow
                            autofocus
                            placeholder="@playlist any\n@type video clip\n@search *"
                        />
                        </div>
                        <div class="col-auto justify-end">
                        <q-btn dense flat color="primary" icon="send" @click="scope.set" />
                        </div>
                    </div>
            </q-popup-edit>
          </q-td>
        </q-tr>

        <!-- FOOTER ROW -->
        <q-tr v-else-if="props.row._is_footer" class="bg-grey-3">
          <q-td colspan="100%" class="text-left text-grey-8 text-sm">
            Training Days: {{ props.row.metrics.training_days }} |
            Playlists: {{ props.row.metrics.playlists }} |
            Videos: {{ props.row.metrics.videos }} |
            Anchors: {{ props.row.metrics.anchors }} |
            Clips: {{ props.row.metrics.clips }} |
            Query time: {{ props.row.metrics.query_time }}
          </q-td>
        </q-tr>

        <!-- NORMAL ROW -->
        <q-tr v-else>
        <q-td>

            <!-- DATE GROUP LABEL -->
            <div v-if="props.row._is_date_start"
                class="text-grey-5 text-xs q-mb-xs">
            {{ props.row._date_label }}
            </div>

            <!-- TREE INDENTATION -->
            <div class="row items-center">

            <!-- INDENT -->
            <div :style="{ width: (props.row._level * 24) + 'px' }"></div>

            <!-- ICON BY TYPE -->
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

            <!-- TITLE -->
            <div>{{ props.row.title }}</div>

            </div>
        </q-td>

        <q-td>{{ props.row.duration || '' }}</q-td>

        <q-td colspan="50%">{{ props.row.description }}</q-td>
        </q-tr>
        """,
    )

    # ----------------------------------------
    # Sticky CSS
    # ----------------------------------------

    ui.add_head_html(
        """
    <style>
    .my-sticky-table {
        height: 75vh;
    }
    .my-sticky-table tbody tr:first-child td {
        position: sticky;
        top: 0;
        background: #f5f5f5;
        z-index: 2;
    }
    .my-sticky-table tbody tr:last-child td {
        position: sticky;
        bottom: 0;
        background: #eeeeee;
        z-index: 2;
    }
    </style>
    """
    )

    # ----------------------------------------
    # Event Listener
    # ----------------------------------------

    def handle_search_update(e):
        search_query["value"] = e.args
        perform_search()

    table.on("search-update", handle_search_update)

    perform_search()
