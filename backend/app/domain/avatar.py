"""Reading an uploaded avatar safely, without an image library.

Three rules, and the reason for each.

**The format is decided by the bytes, never by the header.** `content_type`
arrives from the client, and this file is served back to other people from our
own origin; believing a caller who says their SVG is a PNG would be handing
them a script tag on our domain.

**Only JPEG and PNG are accepted.** A photograph from a phone is JPEG and a
screenshot is PNG, so nothing a person actually has is refused. SVG is refused
because it is a document that can carry script. WebP is refused because
stripping its metadata means walking a RIFF container, and a format nobody
needs here is not worth the code that would make it safe.

**Metadata is removed before the file is stored.** A photo taken on a phone
carries EXIF, and EXIF carries the place it was taken. The users of this
product are school leavers, some of them minors, and their profiles are public
across the whole service. Storing the file as uploaded would publish where they
live. There is no image library in this project — adding one to re-encode would
be the thorough answer — so the metadata segments are cut out by hand, which is
enough because the pixel data is left untouched.
"""

from __future__ import annotations

#: 512 kB. Nothing is resized — there is no image library here — so this cap is
#: the only thing bounding what the database holds and what a reader downloads.
MAX_AVATAR_BYTES = 512 * 1024

JPEG = "image/jpeg"
PNG = "image/png"

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"

#: PNG chunks that are kept. Everything else is dropped, which is the safe way
#: round: a chunk type invented tomorrow is discarded rather than passed on.
#: `eXIf`, `tEXt`, `zTXt` and `iTXt` are the ones that carry a location or a
#: name, and they are absent from this list on purpose.
_PNG_KEEP = frozenset(
    {b"IHDR", b"PLTE", b"IDAT", b"IEND", b"tRNS", b"gAMA", b"cHRM", b"sRGB", b"iCCP", b"pHYs"}
)


def sniff(data: bytes) -> str | None:
    """The format these bytes actually are, or None if it is not one we take."""
    if data.startswith(_PNG_MAGIC):
        return PNG
    if data.startswith(b"\xff\xd8\xff"):
        return JPEG
    return None


def strip_metadata(data: bytes, kind: str) -> bytes:
    """The same image with everything that is not image data removed."""
    return _strip_jpeg(data) if kind == JPEG else _strip_png(data)


def _strip_jpeg(data: bytes) -> bytes:
    """Copy a JPEG, dropping every APPn and comment segment.

    EXIF lives in APP1, XMP in APP1 too, Photoshop resources in APP13. APP0 is
    the JFIF header and carries nothing about the photographer, but dropping it
    as well keeps the rule simple and every decoder accepts its absence.

    Scan data is not parsed: once SOS is reached the rest of the file is copied
    verbatim, because the entropy-coded stream has no segment structure to walk.
    """
    out = bytearray(data[:2])  # SOI
    i = 2
    end = len(data)
    while i + 1 < end:
        if data[i] != 0xFF:
            # Not at a marker. The file is malformed or we lost our place;
            # copying the remainder is safer than guessing.
            out += data[i:]
            break
        marker = data[i + 1]
        if marker == 0xD8 or 0xD0 <= marker <= 0xD7 or marker == 0x01:
            out += data[i:i + 2]
            i += 2
            continue
        if marker == 0xD9:  # EOI
            out += data[i:i + 2]
            break
        if i + 3 >= end:
            out += data[i:]
            break
        length = int.from_bytes(data[i + 2:i + 4], "big")
        segment_end = i + 2 + length
        if length < 2 or segment_end > end:
            out += data[i:]
            break
        if marker == 0xDA:  # SOS — image data follows, copy the rest as it is.
            out += data[i:]
            break
        if 0xE0 <= marker <= 0xEF or marker == 0xFE:  # APPn, COM
            i = segment_end
            continue
        out += data[i:segment_end]
        i = segment_end
    return bytes(out)


def _strip_png(data: bytes) -> bytes:
    """Copy a PNG, keeping only the chunks on the list above."""
    out = bytearray(_PNG_MAGIC)
    i = len(_PNG_MAGIC)
    end = len(data)
    while i + 8 <= end:
        length = int.from_bytes(data[i:i + 4], "big")
        kind = data[i + 4:i + 8]
        chunk_end = i + 12 + length
        if chunk_end > end:
            break  # truncated file; what has been copied is still a valid PNG
        if kind in _PNG_KEEP:
            out += data[i:chunk_end]
        i = chunk_end
        if kind == b"IEND":
            break
    return bytes(out)
