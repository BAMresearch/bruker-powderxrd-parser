from .parser import BrukerPowderXRDParser

# Add more metadata if needed
bruker_powderxrd_parser_entry_point = {
    "name": "BrukerPowderXRDParser",
    "description": "A parser for Bruker instrumentation for Powder X-ray diffraction (XRD).",
    "parser_class": BrukerPowderXRDParser,
}
