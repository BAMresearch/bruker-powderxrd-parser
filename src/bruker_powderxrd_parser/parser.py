# import json
import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import matplotlib.pyplot as plt
from bam_masterdata.datamodel.object_types import PowderXRDMeasurement
from bam_masterdata.parsing import AbstractParser

from bruker_powderxrd_parser.dataclasses import BrukerExperiment, MetadataRule
from bruker_powderxrd_parser.utils import find_elements


class BrukerPowderXRDParser(AbstractParser):
    """
    Parser for Bruker .brml powder XRD files.

    Architecture:
        BRML file
            -> multiple experiments in folders ExperimentX/
                -> XML roots
                -> metadata
                -> PXRD data (extracted from RawData0.xml)
                -> artifacts (e.g., generated plots)
    """

    METADATA_RULES = {
        "DeviceTypeDesc": MetadataRule(
            xml_file="DataContainer.xml",
            tag="DeviceTypeDesc",
            method="text",
        ),
        "SerialNo": MetadataRule(
            xml_file="DataContainer.xml",
            tag="SerialNo",
            method="text",
        ),
        "AppType": MetadataRule(
            xml_file="RawData0.xml",
            tag="AppType",
            method="text",
        ),
        "SampleName": MetadataRule(
            xml_file="RawData0.xml",
            tag="InfoItem",
            method="attribute_with_filter",
            attribute="Value",
            filter_attribute="Name",
            filter_value="SampleName",
        ),
        "TimeStampStarted": MetadataRule(
            xml_file="RawData0.xml",
            tag="TimeStampStarted",
            method="text",
        ),
        "TimeStampFinished": MetadataRule(
            xml_file="RawData0.xml",
            tag="TimeStampFinished",
            method="text",
        ),
        "Unit": MetadataRule(
            xml_file="RawData0.xml",
            tag="Unit",
            method="attribute",
            attribute="Base",
        ),
        "Start": MetadataRule(
            xml_file="RawData0.xml",
            tag="Start",
            method="text",
        ),
        "Stop": MetadataRule(
            xml_file="RawData0.xml",
            tag="Stop",
            method="text",
        ),
        "Increment": MetadataRule(
            xml_file="RawData0.xml",
            tag="Increment",
            method="text",
        ),
        "TimePerStep": MetadataRule(
            xml_file="RawData0.xml",
            tag="TimePerStep",
            method="text",
        ),
        "RotationSpeed": MetadataRule(
            xml_file="RawData0.xml",
            tag="RotationSpeed",
            method="attribute",
            attribute="Value",
        ),
        "Voltage": MetadataRule(
            xml_file="RawData0.xml",
            tag="Voltage",
            method="attribute",
            attribute="Value",
        ),
        "Current": MetadataRule(
            xml_file="RawData0.xml",
            tag="Current",
            method="attribute",
            attribute="Value",
        ),
        "TubeConfig": MetadataRule(
            xml_file="RawData0.xml",
            tag="Tube",
            method="attribute",
            attribute="LogicName",
        ),
        "TubeMaterial": MetadataRule(
            xml_file="RawData0.xml",
            tag="TubeMaterial",
            method="text",
        ),
        "WaveLengthAlpha1": MetadataRule(
            xml_file="RawData0.xml",
            tag="WaveLengthAlpha1",
            method="attribute",
            attribute="Value",
        ),
        "WaveLengthAlpha2": MetadataRule(
            xml_file="RawData0.xml",
            tag="WaveLengthAlpha2",
            method="attribute",
            attribute="Value",
        ),
        "WaveLengthAverage": MetadataRule(
            xml_file="RawData0.xml",
            tag="WaveLengthAverage",
            method="attribute",
            attribute="Value",
        ),
        "WaveLengthBeta": MetadataRule(
            xml_file="RawData0.xml",
            tag="WaveLengthBeta",
            method="attribute",
            attribute="Value",
        ),
        "GoniometerType": MetadataRule(
            xml_file="RawData0.xml",
            tag="GoniometerType",
            method="text",
        ),
    }

    # SerialNo to wavelength mapping based on tube configuration (needs to be extended with more tube types)
    INSTRUMENT_WAVELENGTH_MAPPING = {
        "251987": "WaveLengthAverage",  # D6Pm
        "205225": "WaveLengthAlpha1",  # D8D
        "210481": "WaveLengthAverage",  # D8A
    }

    def _group_xml_by_experiment(self, xml_files: list[str]) -> dict[str, dict]:
        """
        Returns:

        {
            "Experiment0": {
                "RawData0.xml": "full/archive/path/RawData0.xml",
                ...
            }
        }
        """
        grouped = {}
        for xml_file in xml_files:
            path = Path(xml_file)
            # remove top-level archive directory
            parts = path.parts[1:]

            if len(parts) < 2:
                continue

            experiment_name = parts[0]
            filename = parts[-1]

            if not experiment_name.startswith("Experiment"):
                continue

            grouped.setdefault(experiment_name, {})
            grouped[experiment_name][filename] = xml_file

        return grouped

    def _extract_value(self, root: ET.Element, rule: MetadataRule):
        """
        Extracts a value from the XML root based on the provided MetadataRule.

        Args:
            root (ET.Element): The XML root element to extract from
            rule (MetadataRule): The rule defining how to extract the value

        Returns:
            Any: The extracted value or None if not found
        """
        for elem in find_elements(root, rule.tag):
            if rule.method == "text":
                return elem.text

            if rule.method == "attribute":
                return elem.attrib.get(rule.attribute)

            if rule.method == "attribute_with_filter":
                if elem.attrib.get(rule.filter_attribute) == rule.filter_value:
                    return elem.attrib.get(rule.attribute)

        return None

    def extract_metadata(self, experiment: BrukerExperiment) -> dict:
        """
        Extracts metadata from the XML roots of an experiment based on the defined METADATA_RULES and
        stores it in the experiment.metadata dictionary.

        Args:
            experiment (BrukerExperiment): The experiment object containing XML roots and where metadata will be stored.

        Returns:
            dict: The extracted metadata.
        """
        metadata = {}
        for key, rule in self.METADATA_RULES.items():
            root = experiment.xml_roots.get(rule.xml_file)

            if root is None:
                continue

            value = self._extract_value(root, rule)
            if value is not None:
                metadata[key] = value

        # Dynamic metadata examples
        metadata["Optics"] = []
        raw_root = experiment.xml_roots.get("RawData0.xml")
        if raw_root is not None:
            for elem in find_elements(raw_root, "BeringInfo"):
                metadata["Optics"].append(elem.attrib.get("ClassPath", ""))

        return metadata

    def extract_xrd_data(
        self, experiment: BrukerExperiment
    ) -> tuple[list[float], list[float]]:
        """
        Extracts the 2Theta and intensity values from the RawData0.xml file of the experiment. It uses the metadata
        to calculate the 2Theta values based on the Start and Increment values.

        Args:
            experiment (BrukerExperiment): The experiment object containing XML roots and where metadata is stored.

        Returns:
            tuple[list[float], list[float]]: The extracted 2Theta and intensity values.
        """
        root = experiment.xml_roots.get("RawData0.xml")
        if root is None:
            return [], []

        # Extract intensities from Datum tags
        intensities = []
        for datum in find_elements(root, "Datum"):
            if datum.text is None:
                continue

            vals = datum.text.strip().split(",")

            try:
                intensities.append(float(vals[-1]))
            except ValueError:
                continue

        # Extract Start and Increment from metadata to calculate 2Theta values
        if not intensities:
            return [], []
        metadata = experiment.metadata
        try:
            start = float(metadata["Start"])
            increment = float(metadata["Increment"])
        except (KeyError, ValueError):
            return [], []
        two_theta = [start + (i * increment) for i in range(len(intensities))]

        return two_theta, intensities

    def generate_plot(
        self, experiment: BrukerExperiment, output_dir: str | Path, dpi: int = 300
    ) -> Path | None:
        """
        Generates a plot of the PXRD data (2Theta vs Intensity) for the given experiment and saves it as a PNG
        file in the specified output directory. The filename is constructed using the sample name and experiment name.

        Args:
            experiment (BrukerExperiment): The experiment object containing the PXRD data.
            output_dir (str | Path): The directory where the plot will be saved.
            dpi (int, optional): The resolution of the saved plot. Defaults to 300.

        Returns:
            Path | None: The path to the saved plot file, or None if the plot could not be generated.
        """
        if not experiment.two_theta or not experiment.intensities:
            return None

        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        sample_name = experiment.metadata.get(
            "SampleName",
            experiment.name,
        )

        filename = f"{sample_name}_{experiment.name}_PXRD.png"
        outpath = output_dir / filename

        plt.figure(figsize=(10, 5))
        plt.plot(experiment.two_theta, experiment.intensities, linewidth=0.8)
        plt.title(sample_name)

        plt.xlabel("2Theta (degrees)")
        plt.ylabel("Intensity (counts)")

        plt.tight_layout()
        plt.savefig(outpath, dpi=dpi)
        plt.close()

        experiment.artifacts["png"] = outpath
        return outpath

    def _safe_float(self, value, default=None):
        if value in [None, "", "None", "NaN"]:
            return default
        try:
            return float(value)
        except ValueError:
            return default

    def _safe_str(self, value, default=None):
        if value in [None, "", "None", "NaN"]:
            return default
        return str(value)

    def parse(self, files, collection, logger):
        self.logger = logger

        for file in files:
            if not file.endswith(".brml"):
                logger.error(f"File {file} is not a .brml file. Skipping.")
                continue
            brml_file = Path(file)

            with ZipFile(brml_file, "r") as archive:
                xml_files = [f for f in archive.namelist() if f.endswith(".xml")]
                grouped_xmls = self._group_xml_by_experiment(xml_files)
                for experiment_name, xml_fs in grouped_xmls.items():
                    xml_roots = {}
                    for filename, archive_path in xml_fs.items():
                        with archive.open(archive_path) as f:
                            xml_roots[filename] = ET.parse(f).getroot()

                    experiment = BrukerExperiment(
                        name=experiment_name,
                        xml_roots=xml_roots,
                    )
                    experiment.metadata = self.extract_metadata(experiment)
                    experiment.two_theta, experiment.intensities = (
                        self.extract_xrd_data(experiment)
                    )

                    # Generating plot
                    _ = self.generate_plot(experiment, output_dir=brml_file.parent)

                    # Adding metadata to openBIS data model
                    serial_no = experiment.metadata.get("SerialNo", "")
                    wavelength_key = self.INSTRUMENT_WAVELENGTH_MAPPING.get(
                        serial_no, "WaveLengthAverage"
                    )
                    xray_wavelength = self._safe_float(
                        experiment.metadata.get(wavelength_key)
                    )
                    measurement = PowderXRDMeasurement(
                        name=self._safe_str(experiment.name),
                        start_date=self._safe_str(
                            experiment.metadata.get("TimeStampStarted")
                        ),
                        end_date=self._safe_str(
                            experiment.metadata.get("TimeStampFinished")
                        ),
                        time_per_step=self._safe_float(
                            experiment.metadata.get("TimePerStep")
                        ),
                        rotation_speed=self._safe_float(
                            experiment.metadata.get("RotationSpeed")
                        ),
                        voltage=self._safe_float(experiment.metadata.get("Voltage")),
                        current=self._safe_float(experiment.metadata.get("Current")),
                        tube_material=self._safe_str(
                            experiment.metadata.get("TubeMaterial")
                        ),
                        xray_wavelength=xray_wavelength,
                        tube_configuration_name=self._safe_str(
                            experiment.metadata.get("TubeConfig")
                        ),
                        goniometer_type=self._safe_str(
                            experiment.metadata.get("GoniometerType")
                        ),
                        start_2theta=self._safe_float(experiment.metadata.get("Start")),
                        end_2theta=self._safe_float(experiment.metadata.get("Stop")),
                        step_size_2theta=self._safe_float(
                            experiment.metadata.get("Increment")
                        ),
                    )
                    measurement_id = collection.add(measurement)
                    logger.info(f"Added measurement {measurement_id} to collection.")
