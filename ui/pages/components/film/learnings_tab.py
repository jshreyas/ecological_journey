from datetime import datetime

from nicegui import ui


class LearningsTab:
    def __init__(self, video_state, current_user):
        self.video_state = video_state
        self.current_user = current_user
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

    def create_tab(self, container):
        self.container = container
        self.refresh()

    def on_send(self):
        if not self.text_input.value.strip():
            return
        self.video_state.conversation.append(
            {
                "author_id": self.current_user["id"],
                "author_name": self.current_user["name"],
                "text": self.text_input.value,
                "stamp": datetime.now().strftime("%H:%M"),
            }
        )
        self.text_input.value = ""
        self.refresh()

    def _create_learnings_ui(self):
        with ui.card().classes("w-full h-[600px] flex flex-col"):
            with ui.scroll_area().classes("w-full flex-1 overflow-y-auto"):
                for msg in self.video_state.conversation:
                    ui.chat_message(
                        text=msg["text"],
                        name=msg["author_name"],
                        stamp=msg["stamp"],
                        sent=(msg["author_id"] == self.current_user["id"]),
                        text_html=True,
                    ).classes("w-full")
                self.text_input = ui.editor(placeholder="Type your learnings...").classes("flex-grow w-full")
                self.text_input.props["toolbar"] = self.toolbar
                ui.button(icon="send", on_click=self.on_send).classes("absolute bottom-0 right-0")

    def refresh(self):
        if not self.container:
            return
        self.container.clear()
        with self.container:
            self._create_learnings_ui()
