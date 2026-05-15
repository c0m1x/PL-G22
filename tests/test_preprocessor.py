from preprocessor import preprocess


def test_preprocess_removes_comments_and_blanks():
    source = (
        "C comentario\n"
        "      PROGRAM T\n"
        "\n"
        "* outro comentario\n"
        "      END\n"
    )

    out = preprocess(source)

    assert len(out) == 2
    assert out[0][2] == "PROGRAM T"
    assert out[1][2] == "END"


def test_preprocess_handles_label_and_continuation():
    source = (
        "      PROGRAM T\n"
        "      INTEGER A\n"
        " 10   A = 1\n"
        "     + + 2\n"
        "      END\n"
    )

    out = preprocess(source)

    assign_line = out[2]
    assert assign_line[1] == "10"
    # Normalizamos espacos para validar a juncao logica da continuacao.
    assert " ".join(assign_line[2].split()) == "A = 1 + 2"


def test_preprocess_accepts_lightly_indented_free_form_lines():
    source = (
        "PROGRAM T\n"
        "     INTEGER X\n"
        "     X = 1\n"
        "END\n"
    )

    out = preprocess(source)

    assert [line[2] for line in out] == ["PROGRAM T", "INTEGER X", "X = 1", "END"]
