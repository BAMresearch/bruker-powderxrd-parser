import xml.etree.ElementTree as ET


def _strip_namespace(tag: str) -> str:
    """
    Remove the namespace from an XML tag.

    Args:
        tag (str): The XML tag, potentially with a namespace.

    Returns:
        str: The XML tag without the namespace.
    """
    return tag.split("}", 1)[1] if "}" in tag else tag


def find_elements(root: ET.Element, tag: str):
    """
    Find all elements in the XML tree with the specified tag, ignoring namespaces.

    Args:
        root (ET.Element): The root element of the XML tree.
        tag (str): The XML tag to search for, potentially with a namespace.

    Yields:
        ET.Element: The matching elements.
    """
    for elem in root.iter():
        if _strip_namespace(elem.tag) == tag:
            yield elem
