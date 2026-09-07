from pathlib import Path
from unittest.mock import MagicMock

import pytest
from bam_masterdata.logger import logger

from bruker_powderxrd_parser.parser import BrukerPowderXRDParser

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

TEST_DATA = Path(__file__).parent / "data"

D6PM_FILE = TEST_DATA / "D6Pm" / "A52-B128-S_20-140_0.008_4s_17h_D6Pm.brml"

D8A_FILE = TEST_DATA / "D8A" / "SRM1976b_260105_D8A_20-155_0.008_4s_19hm.brml"

D8D_FILE = TEST_DATA / "D8D" / "Si-Std_SRM640d_D8D_20-97_7_16hm.brml"


BRML_FILES = [
    D6PM_FILE,
    D8A_FILE,
    D8D_FILE,
]


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def parser():
    return BrukerPowderXRDParser()


@pytest.fixture
def collection():
    """
    Mock collection.

    The parser should add measurements and relationships to this
    collection without actually communicating with openBIS.
    """
    collection = MagicMock()

    collection.add.side_effect = lambda measurement: f"/TEST/{measurement.name}"

    return collection


# ---------------------------------------------------------------------------
# Test files
# ---------------------------------------------------------------------------
from zipfile import ZipFile


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_brml_xml_grouping(parser, brml_file):
    with ZipFile(brml_file, "r") as archive:
        xml_files = [name for name in archive.namelist() if name.endswith(".xml")]

    grouped = parser._group_xml_by_experiment(xml_files)

    assert "Experiment0" in grouped

    assert "RawData0.xml" in grouped["Experiment0"]
    assert "DataContainer.xml" in grouped["Experiment0"]


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_brml_file_exists(brml_file):
    """All BRML test files exist."""
    assert brml_file.exists(), f"Test file does not exist: {brml_file}"


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_brml_file_is_file(brml_file):
    """All BRML test paths point to files."""
    assert brml_file.is_file()


# ---------------------------------------------------------------------------
# Complete parser tests
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_parse_brml_file(parser, collection, brml_file):
    """A BRML file can be parsed successfully."""
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    assert collection.add.called
    assert collection.add_relationship.called


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_parse_creates_measurement(parser, collection, brml_file):
    """Parsing creates at least one measurement."""
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    assert collection.add.call_count >= 1

    measurement = collection.add.call_args.args[0]

    assert measurement is not None
    assert measurement.name


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_measurement_contains_datasets(
    parser,
    collection,
    brml_file,
):
    """The created measurement contains datasets."""
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    measurement = collection.add.call_args.args[0]

    assert measurement.datasets
    assert len(measurement.datasets) >= 1


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_measurement_contains_xrd_metadata(
    parser,
    collection,
    brml_file,
):
    """The measurement contains the basic XRD metadata."""
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    measurement = collection.add.call_args.args[0]

    assert measurement.start_2theta is not None
    assert measurement.end_2theta is not None
    assert measurement.step_size_2theta is not None

    assert measurement.xray_wavelength is not None


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_measurement_has_expected_name(
    parser,
    collection,
    brml_file,
):
    """The measurement name is derived from the BRML filename."""
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    measurement = collection.add.call_args.args[0]

    assert measurement.name == brml_file.stem


# ---------------------------------------------------------------------------
# Generated files
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_generated_files_exist(
    parser,
    collection,
    brml_file,
):
    """

    Parsing creates the PXRD TXT file and PNG plot.

    The parser currently writes these files next to the BRML file.

    """

    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    output_dir = brml_file.parent

    txt_files = list(output_dir.glob("*_PXRD.txt"))

    png_files = list(output_dir.glob("*_PXRD.png"))

    assert txt_files

    assert png_files


@pytest.mark.parametrize("brml_file", BRML_FILES)
def test_measurement_contains_generated_datasets(
    parser,
    collection,
    brml_file,
):
    """The measurement contains the generated PXRD files."""
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    measurement = collection.add.call_args.args[0]

    # PNG + TXT + original BRML
    assert len(measurement.datasets) >= 3


# ---------------------------------------------------------------------------
# Instrument mapping
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    (
        "brml_file",
        "expected_serial",
        "expected_perm_id",
    ),
    [
        (
            D6PM_FILE,
            "251987",
            "20260304131613732-46857",
        ),
        (
            D8A_FILE,
            "210481",
            "20260304131613732-46856",
        ),
        (
            D8D_FILE,
            "205225",
            "20260508154553650-51528",
        ),
    ],
)
def test_instrument_mapping(
    parser,
    collection,
    brml_file,
    expected_serial,
    expected_perm_id,
):
    """
    The BRML file contains the expected instrument serial number
    and the parser resolves it to the correct openBIS permId.
    """
    parser.parse(
        files=[str(brml_file)],
        collection=collection,
        logger=logger,
    )

    measurement = collection.add.call_args.args[0]

    assert measurement is not None

    assert collection.add_relationship.call_count >= 1

    parent, child = collection.add_relationship.call_args.args

    assert isinstance(parent, dict)
    assert parent["perm_id"] == expected_perm_id
    assert child is not None


# ---------------------------------------------------------------------------
# Helper methods
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("1.234", 1.234),
        ("0", 0.0),
        ("10", 10.0),
        (1.5, 1.5),
        (None, None),
        ("", None),
        ("None", None),
        ("NaN", None),
        ("not-a-number", None),
    ],
)
def test_safe_float(parser, value, expected):
    """_safe_float converts valid values and handles invalid values."""
    assert parser._safe_float(value) == expected


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("test", "test"),
        ("123", "123"),
        (123, "123"),
        (1.5, "1.5"),
        (None, None),
        ("", None),
        ("None", None),
        ("NaN", None),
    ],
)
def test_safe_str(parser, value, expected):
    """_safe_str converts valid values and handles empty values."""
    assert parser._safe_str(value) == expected


# ---------------------------------------------------------------------------
# XML grouping
# ---------------------------------------------------------------------------


def test_group_xml_by_experiment(parser):
    """XML files are correctly grouped by experiment."""
    xml_files = [
        "Experiment0/RawData0.xml",
        "Experiment0/DataContainer.xml",
        "Experiment1/RawData0.xml",
        "Experiment1/DataContainer.xml",
        "Other/file.xml",
        "not_an_experiment.xml",
    ]

    result = parser._group_xml_by_experiment(xml_files)

    assert result == {
        "Experiment0": {
            "RawData0.xml": "Experiment0/RawData0.xml",
            "DataContainer.xml": "Experiment0/DataContainer.xml",
        },
        "Experiment1": {
            "RawData0.xml": "Experiment1/RawData0.xml",
            "DataContainer.xml": "Experiment1/DataContainer.xml",
        },
    }


# ---------------------------------------------------------------------------
# Instrument helper
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("serial_no", "expected_perm_id"),
    [
        (
            "251987",
            "20260304131613732-46857",
        ),
        (
            "210481",
            "20260304131613732-46856",
        ),
        (
            "205225",
            "20260508154553650-51528",
        ),
    ],
)
def test_get_instrument(parser, serial_no, expected_perm_id):
    """Known serial numbers resolve to the correct instrument."""
    experiment = MagicMock()
    experiment.metadata = {
        "SerialNo": serial_no,
    }

    result = parser._get_instrument(experiment)

    assert result == {
        "perm_id": expected_perm_id,
    }


def test_get_instrument_unknown_serial(parser):
    """Unknown serial numbers return None as perm_id."""
    parser.logger = logger
    experiment = MagicMock()
    experiment.metadata = {
        "SerialNo": "UNKNOWN",
    }

    result = parser._get_instrument(experiment)

    assert result == {
        "perm_id": None,
    }


# ---------------------------------------------------------------------------
# Invalid input
# ---------------------------------------------------------------------------


def test_non_brml_file_is_skipped(
    parser,
    collection,
    tmp_path,
):
    """Non-BRML files are skipped."""
    txt_file = tmp_path / "test.txt"
    txt_file.write_text("test")

    parser.parse(
        files=[str(txt_file)],
        collection=collection,
        logger=logger,
    )

    collection.add.assert_not_called()
    collection.add_relationship.assert_not_called()


# ---------------------------------------------------------------------------
# Missing XML data
# ---------------------------------------------------------------------------


def test_extract_xrd_data_without_raw_data(parser):
    """Missing RawData0.xml results in empty XRD data."""
    experiment = MagicMock()
    experiment.xml_roots = {}
    experiment.metadata = {}

    two_theta, intensities, output_path = parser.extract_xrd_data(experiment)

    assert two_theta == []
    assert intensities == []
    assert output_path is None


def test_generate_plot_without_data(parser, tmp_path):
    """No plot is generated when no XRD data exists."""
    experiment = MagicMock()
    experiment.two_theta = []
    experiment.intensities = []

    result = parser.generate_plot(
        experiment,
        tmp_path,
    )

    assert result is None
