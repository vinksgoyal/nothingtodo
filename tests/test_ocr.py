def test_txt_file_returns_text_and_full_confidence(tmp_path) -> None:
    from core.extract import extract_text

    path = tmp_path / "note.txt"
    path.write_text("A plain text document.")

    assert extract_text(path) == ("A plain text document.", 1.0)


def test_unknown_extension_returns_empty_result(tmp_path) -> None:
    from core.extract import extract_text

    assert extract_text(tmp_path / "document.bin") == ("", 0.0)


def test_nonexistent_file_returns_empty_result(tmp_path) -> None:
    from core.extract import extract_text

    assert extract_text(tmp_path / "missing.txt") == ("", 0.0)
