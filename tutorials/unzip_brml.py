from zipfile import ZipFile

files = [
    "./tests/data/D6Pm/A52-B128-S_20-140_0.008_4s_17h_D6Pm.brml",
    "./tests/data/D8A/SRM1976b_260105_D8A_20-155_0.008_4s_19hm.brml",
    "./tests/data/D8D/Si-Std_SRM640d_D8D_20-97_7_16hm.brml",
]

for f in files:
    with ZipFile(f, "r") as zip_ref:
        zip_ref.extractall("./tmp_brml")
