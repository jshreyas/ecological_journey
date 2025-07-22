from ui.pages.components.media import QueryBuilder


def dummy_parse(tokens):
    return lambda x: True


class DummyRow:
    def classes(self, *a, **k):
        return self

    def tooltip(self, *a, **k):
        return self

    def clear(self):
        pass

    def __enter__(self):
        return self

    def __exit__(self, a, b, c):
        pass


class DummyChip:
    def on_click(self, f):
        return self

    def props(self, p):
        return self

    def classes(self, c):
        return self


class DummyLabel:
    def classes(self, *a, **k):
        return self

    def tooltip(self, *a, **k):
        return self


def test_query_builder_adds_tokens(monkeypatch):
    monkeypatch.setattr("nicegui.ui.label", lambda *a, **k: DummyLabel())
    monkeypatch.setattr("nicegui.ui.row", lambda *a, **k: DummyRow())
    monkeypatch.setattr("nicegui.ui.chip", lambda *a, **k: DummyChip())
    monkeypatch.setattr("nicegui.ui.notify", lambda *a, **k: None)

    qb = QueryBuilder(["a", "b"], "Test", "tip")
    qb.add_item("a")
    qb.add_operator("AND")
    qb.add_item("b")
    assert qb.tokens == ["a", "AND", "b"]
    qb.add_operator("NOT")
    assert qb.tokens[-1] == "NOT"
