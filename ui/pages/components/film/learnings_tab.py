from data.crud import create_learning, load_learnings
from nicegui import ui
from utils.user_context import User
from utils.utils import human_stamp

from .video_state import VideoState


class LearningsTab:
    def __init__(self, video_state: VideoState, user: User | None = None):
        self.video_state = video_state
        self.user = user
        self.container = None
        self.text_input = None
        self.toolbar = [
            [
                "bold",
                "italic",
                "strike",
                "underline",
                "unordered",
                "ordered",
                "quote",
                "undo",
                "redo",
                "removeFormat",
                "fullscreen",
                "viewsource",
            ],
        ]
        ui.add_head_html(
            """
            <style>
            .q-message-text-content ul {
                list-style-type: disc;
                margin-left: 1.5em;
            }
            .q-message-text-content ol {
                list-style-type: decimal;
                margin-left: 1.5em;
            }
            .q-message-text-content li {
                margin: 0.25em 0;
            }
            .q-message-text-content blockquote {
                border-left: 3px solid #ccc;
                margin: 0.5em 1em;
                padding-left: 1em;
                color: #555;
                font-style: italic;
            }
            </style>
            """
        )

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def on_send(self):
        if not self.text_input.value.strip():
            return
        # Save to DB
        create_learning(
            author_id=self.user.id,
            text=self.text_input.value,
            video_id=self.video_state.video_id,
            token=self.user.token,
        )
        self.text_input.value = ""
        self.refresh()

    def _create_learnings_ui(self):
        with ui.card().classes("w-full h-[600px] flex flex-col"):
            with ui.scroll_area().classes("w-full flex-1 overflow-y-auto"):
                if self.video_state.conversation:
                    for msg in self.video_state.conversation:
                        ui.chat_message(
                            text=msg["text"],
                            name=msg.get("author_name"),
                            stamp=human_stamp(msg.get("created_at")),
                            sent=(msg["author_id"] == self.user.id if self.user else False),
                            text_html=True,
                        ).classes("w-full")
                else:
                    ui.label("No learnings added yet!").classes("mx-auto")
                if self.user:
                    self.text_input = ui.editor(placeholder="Type your learnings...").classes("flex-grow w-full")
                    self.text_input.props["toolbar"] = self.toolbar
                    ui.button(icon="send", on_click=self.on_send).classes("absolute bottom-0 right-0")

    def refresh(self):
        if not self.container:
            return
        # Load learnings from DB and update conversation
        self.video_state.conversation = load_learnings(self.video_state.video_id)
        self.container.clear()
        with self.container:
            self._create_learnings_ui()
