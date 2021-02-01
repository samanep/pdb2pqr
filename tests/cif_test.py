"""Basic tests to see if the code raises exceptions."""
import logging
from pathlib import Path
import pytest
import common


_LOGGER = logging.getLogger(__name__)
INPUT_PATH = Path("tests/data")


_LOGGER.warning("Need functional and regression test coverage for --userff")
_LOGGER.warning("Need functional and regression test coverage for --usernames")
_LOGGER.warning(
    "Need functional and regression test coverage for --apbs-input"
)


@pytest.mark.parametrize("input_cif", ["1FAS.cif", "3U7T.cif"], ids=str)
def test_basic_cif(input_cif, tmp_path):
    """Non-regression tests on CIF-format biomolecules without ligands."""
    args = "--log-level=DEBUG --ff=AMBER --drop-water --apbs-input=apbs.in"
    input_path = INPUT_PATH / input_cif
    output_pqr = Path(input_cif).stem + ".cif"
    common.run_pdb2pqr(
        args=args,
        input_pdb=input_path,
        output_pqr=output_pqr,
        tmp_path=tmp_path,
    )
