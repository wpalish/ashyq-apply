"""Reading an applicant's own transcript, without deciding anything for them.

The form asks for a GPA, its scale and a graduation date, and an applicant
copies all three off a PDF they already have. Typing them again is where the
digits get transposed.

Every rule here exists because the alternative is a silent guess: a GPA with no
scale is not a GPA, "03/04/2027" is two different dates, and a suggestion the
applicant has not looked at must never reach the profile.
"""

from __future__ import annotations

from app.domain.transcript import suggest_from_transcript

# The API suite already builds a client on a throwaway database; loaded as a
# plugin so this module gets the same fixture without a second copy of it.
pytest_plugins = ["tests.test_api"]

KZ_TRANSCRIPT = """
    ATTESTAT OF SECONDARY EDUCATION
    Nazarbayev Intellectual School of Physics and Mathematics, Almaty

    Student: Aigerim S.
    Grade point average: 4.82 out of 5
    Date of graduation: 25 May 2027
"""

US_TRANSCRIPT = """
    OFFICIAL ACADEMIC TRANSCRIPT
    Cumulative GPA: 3.85 / 4.00
    Graduation date: May 25, 2027
"""


def field(suggestions, name: str):
    return next((s for s in suggestions if s.field == name), None)


class TestWhatItReads:
    def test_a_grade_average_arrives_with_the_scale_it_was_measured_on(self):
        """4.82 means nothing until you know whether the scale ends at 5 or 4."""
        gpa = field(suggest_from_transcript(KZ_TRANSCRIPT), "academics.gpa")
        assert gpa is not None
        assert gpa.value["raw_value"] == 4.82
        assert gpa.value["raw_scale_max"] == 5.0

    def test_the_american_form_of_the_same_sentence_reads_the_same_way(self):
        gpa = field(suggest_from_transcript(US_TRANSCRIPT), "academics.gpa")
        assert gpa is not None
        assert gpa.value["raw_value"] == 3.85
        assert gpa.value["raw_scale_max"] == 4.0

    def test_a_graduation_date_is_read_when_the_month_is_written_out(self):
        graduation = field(suggest_from_transcript(KZ_TRANSCRIPT), "context.graduation_date")
        assert graduation is not None
        assert graduation.value == "2027-05-25"

    def test_every_suggestion_quotes_the_line_it_came_from(self):
        """The applicant checks the suggestion against their own document.

        Without the quote they would be confirming a number on trust, which is
        the same act as typing it in blind.
        """
        for suggestion in suggest_from_transcript(KZ_TRANSCRIPT):
            assert suggestion.excerpt.strip()
            assert suggestion.excerpt.strip() in " ".join(KZ_TRANSCRIPT.split())


class TestWhatItRefusesToGuess:
    def test_a_grade_average_without_a_scale_is_not_offered(self):
        """ "GPA: 4.82" alone is 4.82 out of 5, or out of 100, or out of 10."""
        assert field(suggest_from_transcript("Grade point average: 4.82"), "academics.gpa") is None

    def test_an_ambiguous_numeric_date_is_left_alone(self):
        """03/04/2027 is 3 April to half the world and 4 March to the other."""
        text = "GPA: 3.85 / 4.00\nDate of graduation: 03/04/2027"
        assert field(suggest_from_transcript(text), "context.graduation_date") is None

    def test_an_unambiguous_numeric_date_is_still_read(self):
        text = "Date of graduation: 25/05/2027"
        graduation = field(suggest_from_transcript(text), "context.graduation_date")
        assert graduation is not None
        assert graduation.value == "2027-05-25"

    def test_a_value_outside_its_own_scale_is_refused(self):
        """A 4.9 on a four-point scale is a misread line, not a strong student."""
        assert field(suggest_from_transcript("GPA: 4.9 / 4.0"), "academics.gpa") is None

    def test_a_document_that_is_not_a_transcript_yields_nothing(self):
        assert suggest_from_transcript("Dear applicant, thank you for your interest.") == []

    def test_an_unreadable_pdf_is_an_empty_answer_not_an_error(self):
        assert suggest_from_transcript("") == []


class TestTheScalesItKnows:
    def test_the_common_ways_of_writing_a_scale_all_work(self):
        for text, value, scale in (
            ("GPA: 3.85/4.0", 3.85, 4.0),
            ("Grade point average: 4.82 out of 5", 4.82, 5.0),
            ("Average mark: 87 out of 100", 87.0, 100.0),
            ("GPA 8.4 (scale 10)", 8.4, 10.0),
        ):
            gpa = field(suggest_from_transcript(text), "academics.gpa")
            assert gpa is not None, text
            assert (gpa.value["raw_value"], gpa.value["raw_scale_max"]) == (value, scale), text

    def test_a_scale_nobody_uses_is_refused_rather_than_accepted(self):
        """A "/7" would be an Australian scale; a "/3" is a misread character."""
        assert field(suggest_from_transcript("GPA: 2.1 / 3"), "academics.gpa") is None


class TestTheUploadItself:
    """The endpoint is a trust boundary: it takes a file from the internet."""

    def make_pdf(self, body: str) -> bytes:
        """A one-page PDF carrying `body` as a real text layer.

        Written by hand rather than with a PDF library: the suite would
        otherwise carry a dependency whose only job is to produce four lines of
        text in a test, and the point of the test is that the *product's*
        reader can read an ordinary PDF.
        """
        lines = [line.strip() for line in body.strip().splitlines() if line.strip()]
        drawn = "\n".join(
            f"BT /F1 12 Tf 40 {760 - i * 18} Td ({line}) Tj ET" for i, line in enumerate(lines)
        )
        stream = drawn.encode("latin-1")
        objects = [
            b"<< /Type /Catalog /Pages 2 0 R >>",
            b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
            b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] "
            b"/Resources << /Font << /F1 5 0 R >> >> /Contents 4 0 R >>",
            b"<< /Length %d >>\nstream\n%s\nendstream" % (len(stream), stream),
            b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        ]

        out = bytearray(b"%PDF-1.4\n")
        offsets = []
        for number, payload in enumerate(objects, start=1):
            offsets.append(len(out))
            out += b"%d 0 obj\n" % number + payload + b"\nendobj\n"

        start_xref = len(out)
        out += b"xref\n0 %d\n" % (len(objects) + 1)
        out += b"0000000000 65535 f \n"
        for offset in offsets:
            out += b"%010d 00000 n \n" % offset
        out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (
            len(objects) + 1,
            start_xref,
        )
        return bytes(out)

    def test_the_handmade_pdf_is_one_the_product_can_actually_read(self):
        """Guards the guard: a broken fixture would make the next test vacuous."""
        from app.adapters.extraction import pdf_to_text

        assert "4.82" in pdf_to_text(self.make_pdf(KZ_TRANSCRIPT))

    def test_a_transcript_comes_back_as_suggestions_and_nothing_is_saved(self, client):
        pdf = self.make_pdf(KZ_TRANSCRIPT)
        response = client.post(
            "/api/profiles/transcript",
            files={"file": ("attestat.pdf", pdf, "application/pdf")},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        fields = {s["field"] for s in body["suggestions"]}
        assert "academics.gpa" in fields
        assert "Nothing has been saved" in body["note"]
        # The profile list is untouched: reading is not saving.
        assert client.get("/api/profiles").json() == []

    def test_something_that_is_not_a_pdf_is_refused(self, client):
        response = client.post(
            "/api/profiles/transcript",
            files={"file": ("grades.png", b"\x89PNG\r\n\x1a\n", "image/png")},
        )
        assert response.status_code == 400
        assert "PDF" in response.json()["detail"]

    def test_an_oversized_upload_is_refused_rather_than_parsed(self, client):
        response = client.post(
            "/api/profiles/transcript",
            files={
                "file": ("huge.pdf", b"%PDF-1.4\n" + b"0" * (11 * 1024 * 1024), "application/pdf")
            },
        )
        assert response.status_code == 413

    def test_a_scan_with_no_text_layer_says_so_instead_of_failing(self, client):
        """The commonest real upload: a photograph of a paper document."""
        import io

        from pypdf import PdfWriter

        writer = PdfWriter()
        writer.add_blank_page(width=200, height=200)
        out = io.BytesIO()
        writer.write(out)

        response = client.post(
            "/api/profiles/transcript",
            files={"file": ("scan.pdf", out.getvalue(), "application/pdf")},
        )
        assert response.status_code == 200
        assert response.json()["suggestions"] == []
        assert "image" in response.json()["note"]
