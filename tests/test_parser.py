from pathlib import Path

from bam_masterdata.logger import logger
from bam_masterdata.metadata.entities import CollectionType

TEST_FILE = Path("tests") / "data" / "D6Pm" / "A52-B128-S_20-140_0.008_4s_17h_D6Pm.brml"


class TestBrukerPowderXRDParser:
    def test_parse(self, parser):
        collection = CollectionType()
        parser.parse([], collection, logger)

        assert len(collection.attached_objects) == 0
        assert len(collection.relationships) == 0


class TestBrukerFileXRDParser:
    def test_parse(self, parser):
        collection = CollectionType()
        parser.parse(
            [TEST_FILE],
            collection,
            logger,
        )

        assert len(collection.attached_objects) == 1
        objects = list(collection.attached_objects.values())
        assert objects[0].name == "Experiment0"
        assert objects[0].voltage == 40
        assert len(collection.relationships) == 0
