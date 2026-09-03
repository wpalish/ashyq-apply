"""Grade conversion — offered, never applied silently.

Conversion tables are approximations published by credential-evaluation bodies
and universities differ on them. This module therefore *proposes* a conversion
with its method and source attached; nothing writes a converted value into a
profile unless the caller accepts it explicitly.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.schemas.profile import GradeValue


@dataclass(frozen=True)
class ConversionMethod:
    key: str
    from_scale: str
    to_scale: str
    description: str
    source: str
    caveat: str


METHODS: dict[str, ConversionMethod] = {
    "kz5_to_us4_linear": ConversionMethod(
        key="kz5_to_us4_linear",
        from_scale="KZ 5-point",
        to_scale="US 4.0",
        description="Linear map of the passing band 3.0-5.0 onto 2.0-4.0.",
        source="ASHYQ Apply built-in approximation (app/domain/grades.py) — not a credential evaluation",
        caveat=(
            "Universities in the United States generally require an evaluation by a NACES member "
            "(WES, ECE, SpanTran). This figure is for shortlisting only and must not be entered "
            "on an application form."
        ),
    ),
    "pct100_to_us4_linear": ConversionMethod(
        key="pct100_to_us4_linear",
        from_scale="Percentage /100",
        to_scale="US 4.0",
        description="Linear map of 50-100% onto 1.0-4.0.",
        source="ASHYQ Apply built-in approximation (app/domain/grades.py) — not a credential evaluation",
        caveat="Institutions differ widely on percentage bands; treat as indicative only.",
    ),
    "uk_class_to_us4": ConversionMethod(
        key="uk_class_to_us4",
        from_scale="UK percentage /100",
        to_scale="US 4.0",
        description="UK degree classification bands mapped to common US equivalents.",
        source="ASHYQ Apply built-in approximation (app/domain/grades.py) — not a credential evaluation",
        caveat="UK marking is not linear; a 70% first-class mark is not a 2.8 GPA.",
    ),
}


def available_methods(scale_label: str) -> list[ConversionMethod]:
    low = scale_label.lower()
    out = []
    if "5" in low and "point" in low:
        out.append(METHODS["kz5_to_us4_linear"])
    if "percent" in low or "/100" in low or "100" in low:
        out.append(METHODS["pct100_to_us4_linear"])
        out.append(METHODS["uk_class_to_us4"])
    return out


def propose_conversion(grade: GradeValue, method_key: str) -> GradeValue:
    """Return a *copy* carrying the converted value plus its provenance."""
    method = METHODS.get(method_key)
    if method is None:
        raise ValueError(f"Unknown conversion method '{method_key}'. Known: {sorted(METHODS)}")

    if method_key == "kz5_to_us4_linear":
        converted = _linear(grade.raw_value, 3.0, 5.0, 2.0, 4.0)
    elif method_key == "pct100_to_us4_linear":
        converted = _linear(grade.raw_value, 50.0, 100.0, 1.0, 4.0)
    elif method_key == "uk_class_to_us4":
        converted = _uk_bands(grade.raw_value)
    else:  # pragma: no cover - guarded above
        raise ValueError(method_key)

    return grade.model_copy(
        update={
            "converted_value": round(converted, 2),
            "converted_scale_label": method.to_scale,
            "method": f"{method.description} ({method.key})",
            "method_source": f"{method.source}. Caveat: {method.caveat}",
        }
    )


def _linear(v: float, lo_in: float, hi_in: float, lo_out: float, hi_out: float) -> float:
    if v <= lo_in:
        return lo_out
    if v >= hi_in:
        return hi_out
    return lo_out + (v - lo_in) * (hi_out - lo_out) / (hi_in - lo_in)


def _uk_bands(pct: float) -> float:
    for threshold, gpa in ((70, 4.0), (65, 3.7), (60, 3.3), (55, 3.0), (50, 2.7), (40, 2.0)):
        if pct >= threshold:
            return gpa
    return 0.0
