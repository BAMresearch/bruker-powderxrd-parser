"""
Bruker BRML Parser Library.

This module provides the BrmlParser class to extract metadata, PXRD 
(Powder X-Ray Diffraction) data, and generate plots from Bruker BRML files.
"""

import zipfile
import xml.etree.ElementTree as ET
import json
import os
import matplotlib.pyplot as plt
from typing import Dict, Any, Optional

class BrmlParser:
    """
    Parses Bruker BRML files to extract metadata, PXRD data, and generate plots.

    Attributes:
        filepath (str): Path to the BRML file.
        base_name (str): The base name of the file, used for output generation.
        config (dict): Configuration dictionary defining metadata mappings and output suffixes.
        metadata (dict): Dictionary storing extracted metadata.
        two_theta (list): List of 2Theta values calculated or extracted from the data.
        intensities (list): List of intensity values extracted from the data.
    """
    
    DEFAULT_CONFIG = {
        "output_suffix_json": "_PXRDmeta.json",
        "output_suffix_txt": "_PXRDxy.txt",
        "output_suffix_png": "_PXRDdiff.png",
        
        # Mapping definition: 
        # "Output Key": ("XML File", "XML Tag", "Extraction Method", "Attribute Name" (Optional), "Filter Attribute Name" (Optional), "Filter Attribute Value" (Optional))
        "metadata_mapping": {
            "DeviceTypeDesc": ("DataContainer.xml", "DeviceTypeDesc", "text"),
            "SerialNo": ("DataContainer.xml", "SerialNo", "text"),
            "AppType": ("RawData0.xml", "AppType", "text"),
            "SampleName": ("RawData0.xml", "InfoItem", "attribute_with_filter", "Value", "Name", "SampleName"),
            "TimeStampStarted": ("RawData0.xml", "TimeStampStarted", "text"),
            "TimeStampFinished": ("RawData0.xml", "TimeStampFinished", "text"),
            "Unit": ("RawData0.xml", "Unit", "attribute", "Base"),
            "Start": ("RawData0.xml", "Start", "text"),
            "Stop": ("RawData0.xml", "Stop", "text"),
            "Increment": ("RawData0.xml", "Increment", "text"),
            "TimePerStep": ("RawData0.xml", "TimePerStep", "text"),
            "RotationSpeed": ("RawData0.xml", "RotationSpeed", "attribute", "Value"),
            "Voltage": ("RawData0.xml", "Voltage", "attribute", "Value"),
            "Current": ("RawData0.xml", "Current", "attribute", "Value"),
            "Tube": ("RawData0.xml", "Tube", "attribute", "LogicName"),
            "GoniometerType": ("RawData0.xml", "GoniometerType", "text"),
            # BeringInfo and Recording are handled dynamically due to multiple occurrences
        }
    }

    def __init__(self, filepath: str, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the BrmlParser.

        Args:
            filepath (str): The path to the Bruker BRML zip/archive file.
            config (dict, optional): Custom configuration for metadata mapping. 
                                     Defaults to BrmlParser.DEFAULT_CONFIG.
        """
        self.filepath = filepath
        self.base_name = os.path.splitext(self.filepath)[0]
        self.config = config if config else self.DEFAULT_CONFIG
        self.metadata = {}
        self.two_theta = []
        self.intensities = []

    def _strip_namespace(self, tag: str) -> str:
        """
        Removes the XML namespace from a tag for easier searching.

        Args:
            tag (str): The original XML tag possibly containing a namespace.

        Returns:
            str: The tag name without the namespace.
        """
        return tag.split('}', 1)[1] if '}' in tag else tag

    def _parse_xml_file(self, archive: zipfile.ZipFile, xml_filename: str) -> Optional[ET.Element]:
        """
        Extracts and parses a specific XML file from the BRML archive.

        Args:
            archive (zipfile.ZipFile): The opened zipfile archive of the BRML file.
            xml_filename (str): The name of the XML file to search for and parse.

        Returns:
            ET.Element or None: The root element of the parsed XML, or None if not found.
        """
        target_file = next((f for f in archive.namelist() if f.endswith(xml_filename)), None)
        if not target_file:
            return None
        
        with archive.open(target_file) as file:
            tree = ET.parse(file)
            return tree.getroot()

    def parse_metadata(self):
        """
        Extracts metadata based on the configuration mapping and populates self.metadata.

        Reads from statically mapped fields defined in the configuration, and dynamically 
        extracts information like Optics and Detectors.
        """
        with zipfile.ZipFile(self.filepath, 'r') as archive:
            xml_roots = {
                "DataContainer.xml": self._parse_xml_file(archive, "DataContainer.xml"),
                "RawData0.xml": self._parse_xml_file(archive, "RawData0.xml")
            }

            # 1. Parse statically mapped metadata
            for key, rules in self.config["metadata_mapping"].items():
                xml_file, tag, method = rules[0], rules[1], rules[2]
                root = xml_roots.get(xml_file)
                
                if root is None:
                    continue

                for elem in root.iter():
                    if self._strip_namespace(elem.tag) == tag:
                        if method == "text":
                            self.metadata[key] = elem.text
                            break # Stop after finding the first match
                        elif method == "attribute":
                            attr_name = rules[3]
                            self.metadata[key] = elem.attrib.get(attr_name, "")
                            break # Stop after finding the first match
                        elif method == "attribute_with_filter":
                            attr_name = rules[3]
                            filter_attr = rules[4]
                            filter_val = rules[5]
                            if elem.attrib.get(filter_attr) == filter_val:
                                self.metadata[key] = elem.attrib.get(attr_name, "")
                                break # Stop after finding the first match

            # 2. Parse dynamic lists (BeringInfo, Recording)
            if xml_roots["RawData0.xml"] is not None:
                self.metadata["Optics"] = []
                self.metadata["Detectors"] = []
                
                for elem in xml_roots["RawData0.xml"].iter():
                    tag = self._strip_namespace(elem.tag)
                    if tag == "BeringInfo":
                        self.metadata["Optics"].append(elem.attrib.get("ClassPath", ""))
                    elif tag == "Recording":
                        self.metadata["Detectors"].append(elem.attrib.get("VisibleName", ""))

    def parse_data(self):
        """
        Extracts the 2Theta and Intensity arrays from raw data.

        Reads 'RawData0.xml', extracts intensities from Datum tags, and calculates the
        corresponding 2Theta values based on the 'Start' and 'Increment' metadata.
        """
        with zipfile.ZipFile(self.filepath, 'r') as archive:
            root = self._parse_xml_file(archive, "RawData0.xml")
            if root is None:
                print("Could not find RawData0.xml")
                return

            intensities = []
            for datum in root.iter():
                if self._strip_namespace(datum.tag) == "Datum":
                    if datum.text:
                        vals = datum.text.strip().split(',')
                        try:
                            # The intensity is consistently the last value in the list
                            intensities.append(float(vals[-1]))
                        except ValueError:
                            # Skip any empty or malformed datum tags safely
                            continue

        self.intensities = intensities
        
        # Calculate 2Theta array using Start and Increment metadata
        if self.intensities and "Start" in self.metadata and "Increment" in self.metadata:
            try:
                start = float(self.metadata["Start"])
                increment = float(self.metadata["Increment"])
                self.two_theta = [start + (i * increment) for i in range(len(self.intensities))]
            except ValueError:
                print("Error calculating 2Theta values. Invalid Start or Increment metadata.")
        else:
            print("Missing Start or Increment metadata. Please run parse_metadata first if not already done.")

    def _get_output_path(self, suffix: str) -> str:
        """
        Constructs the output file path, incorporating the SampleName if available.
        """
        sample_name = str(self.metadata.get('SampleName', '')).strip()
        if sample_name:
            clean_name = "".join([c if c.isalnum() else "_" for c in sample_name])
            return f"{self.base_name}_{clean_name}{suffix}"
        return self.base_name + suffix

    def export_json(self):
        """
        Exports the extracted metadata to a formatted JSON file.
        """
        out_path = self._get_output_path(self.config["output_suffix_json"])
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(self.metadata, f, indent=4)
        print(f"Saved metadata to {out_path}")

    def export_txt(self):
        """
        Exports the 2Theta and Intensity data to a tab-separated text file.
        """
        out_path = self._get_output_path(self.config["output_suffix_txt"])
        with open(out_path, 'w', encoding='utf-8') as f:
            f.write("2Theta\tIntensity (Counts)\n")
            for x, y in zip(self.two_theta, self.intensities):
                f.write(f"{x:.5f}\t{y}\n")
        print(f"Saved data to {out_path}")

    def export_plot(self):
        """
        Generates and saves a PNG plot of the PXRD pattern.
        """
        if not self.two_theta or not self.intensities:
            print("No data to plot.")
            return

        out_path = self._get_output_path(self.config["output_suffix_png"])
        plt.figure(figsize=(10, 5))
        plt.plot(self.two_theta, self.intensities, color='b', linewidth=0.8)
        
        sample_name = self.metadata.get('SampleName', 'Unknown')
        plt.title(f"PXRD Pattern - {sample_name}")
        plt.xlabel("2Theta (Degrees)")
        plt.ylabel("Intensity (Counts)")
        plt.grid(True, alpha=0.3)
        plt.tight_layout()
        
        plt.savefig(out_path, dpi=300)
        plt.close()
        print(f"Saved plot to {out_path}")

    def process_all(self):
        """
        Runs the full extraction and export pipeline:
        Reads metadata, extracts data, and exports JSON, TXT, and PNG outputs.
        """
        self.parse_metadata()
        self.parse_data()
        self.export_json()
        self.export_txt()
        self.export_plot()
