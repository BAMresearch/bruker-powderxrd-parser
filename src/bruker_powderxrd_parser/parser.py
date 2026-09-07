import xml.etree.ElementTree as ET
from pathlib import Path
from zipfile import ZipFile

import matplotlib

matplotlib.use("Agg")
import re
from datetime import datetime

import matplotlib.pyplot as plt
from bam_masterdata.datamodel.activities import PowderXRDMeasurement
from bam_masterdata.parsing import AbstractParser

from .data_classes import BrukerExperiment, MetadataRule
from .utils import find_elements


class BrukerPowderXRDParser(AbstractParser):
    """
    Parser for Bruker .brml powder XRD files.

    Architecture:
        BRML file
            -> multiple experiments in folders ExperimentX/
                -> XML roots
                -> metadata
                -> PXRD data
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

    # SerialNo to wavelength mapping based on tube configuration.
    INSTRUMENT_WAVELENGTH_MAPPING = {
        "251987": "WaveLengthAverage",  # D6Pm
        "205225": "WaveLengthAlpha1",  # D8D
        "210481": "WaveLengthAverage",  # D8A
    }

    # SerialNo to openBIS instrument permId mapping.
    INSTRUMENT_MAPPING = {
        "251987": "20260304131613732-46857",
        "210481": "20260304131613732-46856",
        "205225": "20260508154553650-51528",
    }

    def _group_xml_by_experiment(
        self,
        xml_files: list[str],
    ) -> dict[str, dict[str, str]]:
        """
        Group XML files by experiment. BRML files can contain an additional root
        directory before the ExperimentX directory, e.g.: SampleName/ Experiment0/ RawData0.xml D
        ataContainer.xml The returned dictionary uses the ExperimentX directory as key.
        """
        grouped = {}
        for xml_file in xml_files:
            path = Path(xml_file)
            # Find the ExperimentX directory anywhere in the path.

            experiment_parts = [
                part for part in path.parts if part.startswith("Experiment")
            ]

            if not experiment_parts:
                continue

            experiment_name = experiment_parts[-1]
            filename = path.name

            grouped.setdefault(experiment_name, {})

            grouped[experiment_name][filename] = xml_file

        return grouped

    def _get_instrument(
        self,
        experiment: BrukerExperiment,
    ) -> dict[str, str | None]:
        """Return the openBIS instrument identifier for an experiment."""
        serial_no = experiment.metadata.get("SerialNo")

        perm_id = self.INSTRUMENT_MAPPING.get(serial_no)

        if perm_id is None:
            self.logger.warning(
                "Unknown instrument serial number: %r",
                serial_no,
            )

        return {"perm_id": perm_id}

    def _extract_value(
        self,
        root: ET.Element,
        rule: MetadataRule,
    ):
        """
        Extract a value from an XML root based on a MetadataRule.
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

    def extract_metadata(
        self,
        experiment: BrukerExperiment,
    ) -> dict:
        """
        Extract metadata from all XML roots of an experiment.
        """
        metadata = {}

        for key, rule in self.METADATA_RULES.items():
            root = experiment.xml_roots.get(rule.xml_file)

            if root is None:
                continue

            value = self._extract_value(root, rule)

            if value is not None:
                metadata[key] = value

        # Dynamic metadata
        metadata["Optics"] = []

        raw_root = experiment.xml_roots.get("RawData0.xml")

        if raw_root is not None:
            for elem in find_elements(raw_root, "BeringInfo"):
                metadata["Optics"].append(elem.attrib.get("ClassPath", ""))

        return metadata

    def extract_xrd_data(
        self,
        experiment: BrukerExperiment,
        output_dir: str | Path | None = None,
    ) -> tuple[list[float], list[float], Path | None]:
        """
        Extract 2Theta and intensity values from RawData0.xml.
        """
        root = experiment.xml_roots.get("RawData0.xml")

        if root is None:
            return [], [], None

        intensities = []

        for datum in find_elements(root, "Datum"):
            if datum.text is None:
                continue

            values = datum.text.strip().split(",")

            try:
                intensities.append(float(values[-1]))
            except (ValueError, IndexError):
                continue

        if not intensities:
            return [], [], None

        metadata = experiment.metadata

        try:
            start = float(metadata["Start"])
            increment = float(metadata["Increment"])
        except (KeyError, ValueError, TypeError):
            return [], [], None

        two_theta = [start + (i * increment) for i in range(len(intensities))]

        sample_name = experiment.metadata.get(
            "SampleName",
            experiment.name,
        )

        filename = f"{sample_name}_{experiment.name}_PXRD.txt"

        if output_dir is None:
            output_dir = Path.cwd()
        else:
            output_dir = Path(output_dir)

        output_dir.mkdir(parents=True, exist_ok=True)

        outxypath = output_dir / filename

        with outxypath.open("w", encoding="utf-8") as xy_file:
            xy_file.write("two_theta\tintensity\n")

            for x_value, y_value in zip(two_theta, intensities):
                xy_file.write(f"{x_value}\t{y_value}\n")

        return two_theta, intensities, outxypath

    def generate_plot(
        self,
        experiment: BrukerExperiment,
        output_dir: str | Path,
        dpi: int = 300,
    ) -> Path | None:
        """
        Generate and save a PXRD plot.
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
        plt.plot(
            experiment.two_theta,
            experiment.intensities,
            linewidth=0.8,
        )

        plt.title(sample_name)
        plt.xlabel("2Theta (degrees)")
        plt.ylabel("Intensity (counts)")
        plt.tight_layout()
        plt.savefig(outpath, dpi=dpi)
        plt.close()

        experiment.artifacts["png"] = outpath

        return outpath

    def _safe_float(
        self,
        value,
        default: float | None = None,
    ) -> float | None:
        """Convert a value to float or return the default."""
        if value in [None, "", "None", "NaN"]:
            return default

        try:
            return float(value)
        except (ValueError, TypeError):
            return default

    def _safe_str(
        self,
        value,
        default: str | None = None,
    ) -> str | None:
        """Convert a value to str or return the default."""
        if value in [None, "", "None", "NaN"]:
            return default

        return str(value)

    def _normalize_iso_datetime(self, value: str, field_name: str) -> str:
        """Normalize ISO datetime strings to Python-compatible ISO format."""

        if not isinstance(value, str):
            raise ValueError(
                f"Invalid datetime format for '{field_name}': "
                f"Expected ISO format string, got {value!r}"
            )

        # Truncate fractional seconds to Python's maximum of 6 digits.
        value = re.sub(
            r"(\.\d{6})\d+([+-]\d{2}:\d{2}|Z)$",
            r"\1\2",
            value,
        )

        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).isoformat()
        except ValueError as exc:
            raise ValueError(
                f"Invalid datetime format for '{field_name}': "
                f"Expected ISO format string, got {value!r}"
            ) from exc

    def parse(self, files, collection, logger):
        self.logger = logger

        for file in files:
            if not file.endswith(".brml"):
                self.logger.error(
                    "File %s is not a .brml file. Skipping.",
                    file,
                )
                continue

            brml_file = Path(file)

            with ZipFile(brml_file, "r") as archive:
                xml_files = [
                    name for name in archive.namelist() if name.endswith(".xml")
                ]

                grouped_xmls = self._group_xml_by_experiment(xml_files)

                for experiment_name, xml_files in grouped_xmls.items():
                    # --------------------------------------------------
                    # Read XML files
                    # --------------------------------------------------
                    xml_roots = {}

                    for filename, archive_path in xml_files.items():
                        with archive.open(archive_path) as xml_file:
                            xml_roots[filename] = ET.parse(xml_file).getroot()

                    # --------------------------------------------------
                    # Create experiment
                    # --------------------------------------------------
                    experiment = BrukerExperiment(
                        name=experiment_name,
                        xml_roots=xml_roots,
                    )

                    experiment.metadata = self.extract_metadata(experiment)

                    (
                        experiment.two_theta,
                        experiment.intensities,
                        outxypath,
                    ) = self.extract_xrd_data(
                        experiment,
                        output_dir=brml_file.parent,
                    )

                    # --------------------------------------------------
                    # Generate plot
                    # --------------------------------------------------
                    plotpath = self.generate_plot(
                        experiment,
                        output_dir=brml_file.parent,
                    )

                    # --------------------------------------------------
                    # Prepare measurement metadata
                    # --------------------------------------------------
                    serial_no = experiment.metadata.get(
                        "SerialNo",
                        "",
                    )

                    wavelength_key = self.INSTRUMENT_WAVELENGTH_MAPPING.get(
                        serial_no,
                        "WaveLengthAverage",
                    )

                    xray_wavelength = self._safe_float(
                        experiment.metadata.get(wavelength_key)
                    )

                    measurement_data = {
                        "name": brml_file.stem,
                        "start_date": self._normalize_iso_datetime(
                            experiment.metadata.get("TimeStampStarted"),
                            "TimeStampStarted",
                        ),
                        "end_date": self._normalize_iso_datetime(
                            experiment.metadata.get("TimeStampFinished"),
                            "TimeStampFinished",
                        ),
                        "rotation_speed": self._safe_float(
                            experiment.metadata.get("RotationSpeed")
                        ),
                        "voltage": self._safe_float(experiment.metadata.get("Voltage")),
                        "current": self._safe_float(experiment.metadata.get("Current")),
                        "tube_material": self._safe_str(
                            experiment.metadata.get("TubeMaterial")
                        ),
                        "xray_wavelength": xray_wavelength,
                        "tube_configuration_name": self._safe_str(
                            experiment.metadata.get("TubeConfig")
                        ),
                        "goniometer_type": self._safe_str(
                            experiment.metadata.get("GoniometerType")
                        ),
                        "start_2theta": self._safe_float(
                            experiment.metadata.get("Start")
                        ),
                        "end_2theta": self._safe_float(experiment.metadata.get("Stop")),
                        "step_size_2theta": self._safe_float(
                            experiment.metadata.get("Increment")
                        ),
                    }

                    time_per_step = self._safe_float(
                        experiment.metadata.get("TimePerStep")
                    )

                    if time_per_step is not None:
                        measurement_data["time_per_step"] = time_per_step

                    measurement = PowderXRDMeasurement(**measurement_data)

                    # --------------------------------------------------
                    # Add datasets
                    # --------------------------------------------------
                    if plotpath is not None:
                        measurement.add_dataset(plotpath)

                    if outxypath is not None:
                        measurement.add_dataset(outxypath)

                    measurement.add_dataset(file)

                    # --------------------------------------------------
                    # Add measurement to collection
                    # --------------------------------------------------
                    measurement_id = collection.add(measurement)

                    self.logger.info(
                        "Added measurement %s to collection.",
                        measurement_id,
                    )

                    # --------------------------------------------------
                    # Add instrument relationship
                    # --------------------------------------------------
                    instrument = self._get_instrument(experiment)

                    collection.add_relationship(
                        instrument,
                        measurement_id,
                    )

                    self.logger.info("Added instrument as parent.")
