#!/usr/bin/env python3
"""
Execution script for parsing Bruker BRML files.

This script uses the BrmlParser library to extract metadata and PXRD data 
from a provided BRML file, and generates JSON, TXT, and PNG outputs.
"""

import argparse
import os
import sys
from brml_parser import BrmlParser

def main():
    """
    Main execution entry point. Parses command line arguments and runs the BRML parser.
    """
    parser = argparse.ArgumentParser(
        description="Parse Bruker BRML files to extract metadata and PXRD data.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter
    )
    
    parser.add_argument(
        "filepath", 
        nargs="?", 
        default="AM09_PZA_PA_80Cfor24h.brml",
        help="Path to the .brml file to parse"
    )
    
    args = parser.parse_args()
    
    if not os.path.exists(args.filepath):
        print(f"Error: The file '{args.filepath}' does not exist.")
        sys.exit(1)
        
    print(f"Processing '{args.filepath}'...")
    
    # Initialize the parser from the library module
    brml_parser = BrmlParser(args.filepath)
    
    # Run the full processing pipeline (extracts metadata, data, and exports files)
    brml_parser.process_all()
    
    print(f"Processing complete for '{args.filepath}'.")

if __name__ == "__main__":
    main()
