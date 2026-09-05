"""Reading an avatar without trusting the uploader, and without a library.

The stakes here are not cosmetic. These files are served to every signed-in
applicant, so a format decided by the client's header would let somebody put a
script on our origin; and a photo kept as uploaded would publish the place it
was taken, for users who are school leavers with public profiles.
"""

from __future__ import annotations

import struct
import zlib

from app.domain.avatar import JPEG, PNG, sniff, strip_metadata

GPS = b"a fake EXIF payload with a location in it"


def jpeg_with_exif() -> bytes:
    """A minimal JPEG carrying an APP1 (EXIF) and a comment segment."""
    exif = b"Exif\x00\x00" + GPS
    app1 = b"\xff\xe1" + struct.pack(">H", len(exif) + 2) + exif
    comment = b"\xff\xfe" + struct.pack(">H", 2 + len(b"taken by")) + b"taken by"
    # A quantisation table stands in for the real tables a photo would carry.
    dqt = b"\xff\xdb" + struct.pack(">H", 2 + 65) + b"\x00" + bytes(64)
    sos = b"\xff\xda" + struct.pack(">H", 2 + 1) + b"\x00" + b"scan-data-here"
    return b"\xff\xd8" + app1 + comment + dqt + sos + b"\xff\xd9"


def png_chunk(kind: bytes, payload: bytes) -> bytes:
    return (
        struct.pack(">I", len(payload))
        + kind
        + payload
        + struct.pack(">I", zlib.crc32(kind + payload) & 0xFFFFFFFF)
    )


def png_with_text() -> bytes:
    """A minimal PNG carrying a text chunk and an eXIf chunk."""
    header = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)
    return (
        b"\x89PNG\r\n\x1a\n"
        + png_chunk(b"IHDR", header)
        + png_chunk(b"tEXt", b"Author\x00A school leaver")
        + png_chunk(b"eXIf", GPS)
        + png_chunk(b"IDAT", zlib.compress(b"\x00\xff\xff\xff"))
        + png_chunk(b"IEND", b"")
    )


class TestWhatIsAccepted:
    def test_the_bytes_decide_the_format(self):
        assert sniff(png_with_text()) == PNG
        assert sniff(jpeg_with_exif()) == JPEG

    def test_an_svg_is_refused_however_it_is_labelled(self):
        """It would be served from our own origin, and it can carry script."""
        assert sniff(b'<svg xmlns="http://www.w3.org/2000/svg"><script/></svg>') is None

    def test_a_format_we_do_not_handle_is_refused_rather_than_guessed(self):
        assert sniff(b"RIFF\x00\x00\x00\x00WEBPVP8 ") is None  # WebP
        assert sniff(b"GIF89a") is None
        assert sniff(b"%PDF-1.7") is None
        assert sniff(b"") is None


class TestWhatIsRemoved:
    def test_a_photo_does_not_keep_the_place_it_was_taken(self):
        stripped = strip_metadata(jpeg_with_exif(), JPEG)
        assert GPS not in stripped
        assert b"Exif" not in stripped
        assert b"taken by" not in stripped

    def test_the_picture_itself_survives(self):
        stripped = strip_metadata(jpeg_with_exif(), JPEG)
        assert stripped.startswith(b"\xff\xd8")
        assert stripped.endswith(b"\xff\xd9")
        # The tables and the scan data are what make it an image at all.
        assert b"\xff\xdb" in stripped
        assert b"scan-data-here" in stripped

    def test_a_png_keeps_its_pixels_and_loses_its_labels(self):
        stripped = strip_metadata(png_with_text(), PNG)
        assert stripped.startswith(b"\x89PNG\r\n\x1a\n")
        assert b"IHDR" in stripped
        assert b"IDAT" in stripped
        assert b"IEND" in stripped
        assert b"A school leaver" not in stripped
        assert GPS not in stripped

    def test_an_unknown_chunk_is_dropped_rather_than_passed_on(self):
        """The list is what is kept, so a chunk invented later is not carried."""
        odd = png_with_text().replace(b"eXIf", b"zZzZ")
        assert b"zZzZ" not in strip_metadata(odd, PNG)

    def test_a_truncated_file_does_not_crash_the_reader(self):
        for source, kind in ((jpeg_with_exif(), JPEG), (png_with_text(), PNG)):
            for cut in (4, 10, 20, len(source) - 3):
                strip_metadata(source[:cut], kind)  # must not raise

    def test_stripping_is_idempotent(self):
        once = strip_metadata(jpeg_with_exif(), JPEG)
        assert strip_metadata(once, JPEG) == once
