import file_parser


def test_tsv_with_commas_in_text_is_parsed_as_tab_separated():
    text = "PATIENT_ID\tDIAGNOSIS\tNOTES\n" + "".join(
        f"P{i}\tAdenocarcinoma\tstage II, grade 3, left lung, resected\n"
        for i in range(5))
    df = file_parser.parse_file(text.encode(), "clinical.tsv")
    assert list(df.columns) == ["PATIENT_ID", "DIAGNOSIS", "NOTES"]
    assert len(df) == 5


def test_plain_csv_still_uses_comma():
    text = "A,B,C\n1,2,3\n4,5,6\n"
    assert file_parser._detect_separator(text) == ","


def test_plain_tsv_still_uses_tab():
    text = "A\tB\tC\n1\t2\t3\n4\t5\t6\n"
    assert file_parser._detect_separator(text) == "\t"


def test_semicolon_and_pipe():
    assert file_parser._detect_separator("A;B;C\n1;2;3\n") == ";"
    assert file_parser._detect_separator("A|B|C\n1|2|3\n") == "|"


def test_quoted_csv_with_uneven_commas_falls_back_to_comma():
    text = 'A,B,C\n1,"x, y",3\n4,5,6\n'
    assert file_parser._detect_separator(text) == ","
