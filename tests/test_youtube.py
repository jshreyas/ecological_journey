from ui.utils.youtube import parse_training_date_from_title


def test_parse_training_date_from_compact_date():
    assert parse_training_date_from_title("Open mat 20240115") == "2024-01-15T00:00:00Z"


def test_parse_training_date_infers_year_from_upload_date():
    result = parse_training_date_from_title(
        "Open mat 05 25",
        upload_date_iso="2024-06-01T00:00:00Z",
    )

    assert result == "2024-05-25T00:00:00Z"


def test_parse_training_date_returns_none_when_no_date_is_present():
    assert parse_training_date_from_title("Open mat highlights") is None
