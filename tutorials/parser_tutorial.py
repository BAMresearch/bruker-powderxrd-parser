from bam_masterdata.logger import logger
from bam_masterdata.metadata.entities import CollectionType

from bruker_powderxrd_parser.parser import BrukerPowderXRDParser

files = [
    "./tests/data/D6Pm/A52-B128-S_20-140_0.008_4s_17h_D6Pm.brml",
    "./tests/data/D8A/SRM1976b_260105_D8A_20-155_0.008_4s_19hm.brml",
    "./tests/data/D8D/Si-Std_SRM640d_D8D_20-97_7_16hm.brml",
]


parser = BrukerPowderXRDParser()
parser.parse(files=files, collection=CollectionType(), logger=logger)
