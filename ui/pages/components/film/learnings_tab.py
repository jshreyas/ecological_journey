from nicegui import ui

from ui.data.crud import create_learning, delete_learning, load_learnings, update_learning
from ui.utils.utils import human_stamp

from .video_state import VideoState


class LearningsTab:
    def __init__(self, video_state: VideoState):
        self.video_state = video_state
        self.user = self.video_state.user
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
        self.editing_msg = None  # Track which message is being edited

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def on_del(self, msg):
        if not msg or not msg.get("_id"):
            return
        if not self.user or msg["author_id"] != self.user.id:
            return
        delete_learning(learning_id=msg["_id"], token=self.user.token)
        self.refresh()

    def on_edit(self, msg):
        self.text_input.props("content-class=text-primary toolbar-bg=primary toolbar-text-color=white")
        self.editing_msg = msg
        self.text_input.value = msg["text"]
        # Scroll the editor into view
        self.container.scroll_to(percent=100)
        self.cancel_button.set_visibility(True)

    def on_send(self):
        if not self.text_input.value.strip():
            return
        if self.editing_msg:
            # Update existing learning
            update_learning(
                learning_id=self.editing_msg["_id"],
                text=self.text_input.value,
                token=self.user.token,
            )
            self.editing_msg = None
        else:
            # Save new learning
            create_learning(
                author_id=self.user.id,
                text=self.text_input.value,
                video_id=self.video_state.video_id,
                token=self.user.token,
            )
        self.text_input.value = ""
        self.refresh()
        self.container.scroll_to(percent=100)

    def on_cancel(self):
        """Exit edit mode"""
        self.editing_msg = None
        self.text_input.value = ""
        self.cancel_button.set_visibility(False)  # 👈 hide cancel button
        self.refresh()
        self.container.scroll_to(percent=100)

    def _create_learnings_ui(self):
        with ui.card().classes("w-full flex-1 overflow-y-auto"):
            if self.video_state.conversation:
                for msg in self.video_state.conversation:
                    with ui.card().classes("relative w-full p-0 shadow-none bg-transparent"):
                        # Chat bubble
                        sent = msg["author_id"] == self.user.id if self.user else False
                        ui.chat_message(
                            text=msg["text"],
                            name=msg.get("alias") if msg.get("alias") else msg.get("author_name"),
                            stamp=human_stamp(msg.get("created_at")),
                            sent=sent,
                            text_html=True,
                        ).classes("w-full").props(f"{'text-color=white bg-color=primary' if sent else ''}")

                        # Floating action buttons (top-right corner)
                        if self.user and msg["author_id"] == self.user.id:
                            with ui.row().classes("absolute top-0 right-0 gap-0 pt-5"):
                                # ui.button(on_click=lambda m=msg: self.on_del(m)).props(
                                #     "flat dense round icon=close color=white size=xs"
                                # ).tooltip("Delete")
                                ui.button(on_click=lambda m=msg: self.on_edit(m)).props(
                                    "flat dense round icon=edit color=white size=xs"
                                ).tooltip("Edit")
            else:
                if self.user:
                    label = "Add your insights! 😀"
                else:
                    label = "Log in to add your insights! 😀"
                ui.chat_message(
                    label=label,
                ).classes("w-full text-center text-bold text-secondary")

            if self.user:
                self.text_input = ui.editor(placeholder="Type your learnings...").classes("flex-grow w-full")
                self.text_input.props["toolbar"] = self.toolbar
                ui.button(
                    icon="send",
                    on_click=self.on_send,
                ).classes(
                    "absolute bottom-0 right-0"
                ).props("color=primary")
                # Pre-create cancel button, but keep hidden
                self.cancel_button = (
                    ui.button(
                        icon="close",
                        on_click=self.on_cancel,
                    )
                    .classes("absolute bottom-0 left-0")
                    .tooltip("Cancel edit")
                )
                self.cancel_button.set_visibility(False)

    def refresh(self):
        if not self.container:
            return
        # Load learnings from DB and update conversation
        self.video_state.conversation = load_learnings(self.video_state.video_id)
        self.container.clear()
        with self.container:
            self._create_learnings_ui()
