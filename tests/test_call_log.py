from voice2fritz.call_log import CallLogEntry, append_call_log_entry, clear_call_log, load_call_log


def test_append_and_load_round_trip(tmp_path):
    path = tmp_path / "call_log.json"
    entry = CallLogEntry(number="+4917612345678", name="Anna Schmidt", direction="outgoing", timestamp="2026-08-04T14:32:00", duration_seconds=135)

    append_call_log_entry(entry, path)

    assert load_call_log(path) == [entry]


def test_load_missing_file_returns_empty_list(tmp_path):
    path = tmp_path / "does-not-exist.json"
    assert load_call_log(path) == []


def test_load_malformed_json_returns_empty_list(tmp_path):
    path = tmp_path / "call_log.json"
    path.write_text("{not valid json")
    assert load_call_log(path) == []


def test_load_call_log_skips_entries_missing_keys(tmp_path):
    path = tmp_path / "call_log.json"
    path.write_text(
        '[\n'
        '  {"number": "+4917612345678", "name": "Anna Schmidt", "direction": "outgoing", '
        '   "timestamp": "2026-08-04T14:00:00", "duration_seconds": 60},\n'
        '  {"number": "incomplete"},\n'
        '  "not a dict"\n'
        ']'
    )

    assert load_call_log(path) == [
        CallLogEntry(number="+4917612345678", name="Anna Schmidt", direction="outgoing", timestamp="2026-08-04T14:00:00", duration_seconds=60)
    ]


def test_append_creates_parent_dirs(tmp_path):
    path = tmp_path / "nested" / "dir" / "call_log.json"
    entry = CallLogEntry(number="+4917612345678", name="", direction="missed", timestamp="2026-08-04T14:20:00", duration_seconds=0)

    append_call_log_entry(entry, path)

    assert path.exists()
    assert load_call_log(path) == [entry]


def test_append_preserves_existing_entries(tmp_path):
    path = tmp_path / "call_log.json"
    first = CallLogEntry(number="+4917612345678", name="Anna Schmidt", direction="outgoing", timestamp="2026-08-04T14:00:00", duration_seconds=60)
    second = CallLogEntry(number="+4930123456", name="Ben Weber", direction="incoming", timestamp="2026-08-04T14:10:00", duration_seconds=30)

    append_call_log_entry(first, path)
    append_call_log_entry(second, path)

    assert load_call_log(path) == [first, second]


def test_clear_empties_the_log(tmp_path):
    path = tmp_path / "call_log.json"
    append_call_log_entry(CallLogEntry(number="+4917612345678", name="", direction="outgoing", timestamp="2026-08-04T14:00:00", duration_seconds=10), path)

    clear_call_log(path)

    assert load_call_log(path) == []


def test_clear_missing_file_is_noop(tmp_path):
    path = tmp_path / "does-not-exist.json"
    clear_call_log(path)
    assert load_call_log(path) == []
