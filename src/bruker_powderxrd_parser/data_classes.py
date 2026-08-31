import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MetadataRule:
    """
    Dataclass to define how to extract a specific piece of metadata from the XML files.
        - `xml_file`: the XML file to look into (e.g., "DataContainer.xml")
        - `tag`: the XML tag to look for (e.g., "DeviceTypeDesc")
        - `method`: the method to extract the data (e.g., "text", "attribute", "attribute_with_filter")
        - `attribute`: if method is "attribute", the name of the attribute to extract
        - `filter_attribute` and `filter_value`: if method is "attribute_with_filter", the attribute and
            value to filter the elements (e.g., filter_attribute="Name", filter_value="SampleName")
    """

    xml_file: str
    tag: str
    method: str
    attribute: str | None = None
    filter_attribute: str | None = None
    filter_value: str | None = None


@dataclass
class BrukerExperiment:
    """
    Dataclass to represent a Bruker experiment.
        - `name`: the name of the experiment (e.g., "Experiment1")
        - `xml_roots`: a dictionary mapping XML file names to their parsed ElementTree roots
        - `metadata`: a dictionary to store extracted metadata
        - `two_theta` and `intensities`: lists to store the extracted PXRD data
        - `artifacts`: a dictionary to store paths to any extracted artifacts (e.g., plots)
    """

    name: str
    xml_roots: dict[str, ET.Element]

    metadata: dict = field(default_factory=dict)

    two_theta: list[float] = field(default_factory=list)
    intensities: list[float] = field(default_factory=list)

    artifacts: dict[str, Path] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "xml_roots": list(self.xml_roots.keys()),
            "metadata": self.metadata,
            "two_theta_points": len(self.two_theta),
            "intensity_points": len(self.intensities),
            "artifacts": {k: str(v) for k, v in self.artifacts.items()},
        }
