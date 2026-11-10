"""Public adult reference ranges for the eight BMP analytes, and the abnormal flag.

Source: MedlinePlus Medical Encyclopedia, "Basic metabolic panel", U.S. National
Library of Medicine, https://medlineplus.gov/ency/article/003462.htm (review date
5/19/2025). The page gives one adult range per analyte and notes that ranges vary
slightly between laboratories. mEq/L equals mmol/L for these monovalent ions, so the
sodium and potassium ranges are used as mmol/L, the unit Synthea reports.

These go into OBX-7 (reference range) and drive OBX-8 (abnormal flag). The mock LIS
computes the flag the way a lab system does: below the low limit is L, above the
high limit is H, otherwise N.
"""

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class ReferenceRange:
    low: Decimal
    high: Decimal
    unit: str

    @property
    def text(self) -> str:
        """The range as HL7 v2 writes it in OBX-7, for example '136-144'."""
        return f"{self.low}-{self.high}"


# Decimals are built from strings so 0.8 stays exactly 0.8, and '1.2' prints as '1.2'.
RANGES: dict[str, ReferenceRange] = {
    "2951-2": ReferenceRange(Decimal("136"), Decimal("144"), "mmol/L"),  # Sodium
    "2823-3": ReferenceRange(Decimal("3.7"), Decimal("5.2"), "mmol/L"),  # Potassium
    "2075-0": ReferenceRange(Decimal("96"), Decimal("106"), "mmol/L"),  # Chloride
    "2028-9": ReferenceRange(Decimal("23"), Decimal("29"), "mmol/L"),  # CO2, total
    "3094-0": ReferenceRange(Decimal("6"), Decimal("20"), "mg/dL"),  # Urea nitrogen (BUN)
    "2160-0": ReferenceRange(Decimal("0.8"), Decimal("1.2"), "mg/dL"),  # Creatinine
    "2345-7": ReferenceRange(Decimal("64"), Decimal("100"), "mg/dL"),  # Glucose
    "17861-6": ReferenceRange(Decimal("8.5"), Decimal("10.2"), "mg/dL"),  # Calcium
}

# HL7 table 0078 (interpretation codes): the three this pipeline uses.
LOW, HIGH, NORMAL = "L", "H", "N"


def abnormal_flag(loinc: str, value: str, unit: str) -> str:
    """Return L, H or N for one result. The limits themselves count as normal.

    Raises ValueError if the unit is not the one the range is written in: comparing
    a value against a range in another unit would give a wrong flag, so it is refused.
    """
    ref = RANGES[loinc]
    if unit != ref.unit:
        raise ValueError(f"{loinc}: unit {unit!r} does not match the range unit {ref.unit!r}")
    number = Decimal(value)
    if number < ref.low:
        return LOW
    if number > ref.high:
        return HIGH
    return NORMAL
