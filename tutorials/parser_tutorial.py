from decouple import config as environ
from pybis import Openbis

# Connect to openBIS
openbis = Openbis(environ("OPENBIS_URL"))
openbis.login(environ("OPENBIS_USERNAME"), environ("OPENBIS_PASSWORD"), save_token=True)


from bam_masterdata.cli.run_parser import run_parser

from bruker_powderxrd_parser.parser import BrukerPowderXRDParser

# Define which parser to use and which files to parse
files_parser = {
    BrukerPowderXRDParser(): [
        "./tests/data/D6Pm/A52-B128-S_20-140_0.008_4s_17h_D6Pm.brml",
        "./tests/data/D8A/SRM1976b_260105_D8A_20-155_0.008_4s_19hm.brml",
        "./tests/data/D8D/Si-Std_SRM640d_D8D_20-97_7_16hm.brml",
    ]
}

# Run the parser
run_parser(
    openbis=openbis,
    space_name="JPIZARRO_ADM",
    project_name="BRUKER_PXRD_TEST_PROJECT",
    collection_name="BRUKER_PXRD_TEST_COLLECTION",
    files_parser=files_parser,
)
print("Parsing completed.")
