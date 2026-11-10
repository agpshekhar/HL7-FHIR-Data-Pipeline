"""Tests for the reference ranges and the computed abnormal flag."""

import pytest

from labpipe.lis.reference_ranges import RANGES, abnormal_flag
from labpipe.lis.sample import ANALYTES


def test_every_analyte_has_a_range():
    assert set(RANGES) == set(ANALYTES)


@pytest.mark.parametrize(
    ("value", "flag"),
    [("135.9", "L"), ("136", "N"), ("140.0", "N"), ("144", "N"), ("144.1", "H")],
)
def test_sodium_flags_and_limits_count_as_normal(value, flag):
    assert abnormal_flag("2951-2", value, "mmol/L") == flag


def test_range_text_is_written_as_hl7_expects():
    assert RANGES["2160-0"].text == "0.8-1.2"
    assert RANGES["2951-2"].text == "136-144"


def test_a_unit_that_does_not_match_the_range_is_refused():
    with pytest.raises(ValueError, match="does not match"):
        abnormal_flag("2345-7", "5.5", "mmol/L")
