# Running `tutorials/parser_tutorial.py`

This tutorial shows how to run the Bruker Powder XRD parser from a fresh clone of the repository using a `conda` environment.

The script:

- connects to openBIS
- loads three example `.brml` files from `tests/data/`
- parses them with `BrukerPowderXRDParser`
- uploads the parsed results to openBIS with `bam_masterdata`

## Prerequisites

Before starting, make sure you have:

- `git`
- `conda`
- access to an openBIS instance
- an openBIS username and password

## 1. Clone the repository

```bash
git clone https://github.com/BAMresearch/bruker-powderxrd-parser.git
cd bruker-powderxrd-parser
```

All commands below assume you are in the repository root `bruker-powderxrd-parser/`. We also use Linux synthax for paths; in Windows, directories are separated with `\` instead of `/`, and commands might be slightly different. In case of doubt, debug with ChatGPT.

## 2. Create a conda environment

Create and activate a new environment with Python 3.11:

```bash
conda create -n bruker-pxrd-parser python=3.11 -y
conda activate bruker-pxrd-parser
```

Python 3.10 or newer is required, but Python 3.11 is a good default.

## 3. Install the package

Install the repository and its dependencies into the active conda environment:

```bash
python -m pip install -e .
```

The `-e` flag means "editable install". This is useful when running code directly from a cloned repository.

## 4. Configure your openBIS connection

The tutorial script reads these environment variables:

- `OPENBIS_URL`
- `OPENBIS_USERNAME`
- `OPENBIS_PASSWORD`

You can set them by copy-pastying the `.env.example` file and rename it `.env`. Then, change the values to the ones you will be using.

**IMPORTANT**:

- keep this file private and never commit to your public repository!
- do not print `OPENBIS_PASSWORD` to the terminal or in a notebook!

## 5. Review the target openBIS location

The tutorial currently writes to this location in openBIS:

```python
space_name="YOUR_SPACE_NAME"
project_name="BRUKER_PXRD_TEST_PROJECT"
collection_name="BRUKER_PXRD_TEST_COLLECTION"
```

These values are defined in `tutorials/parser_tutorial.py`.

If the user running the tutorial should write to a different space, project, or collection, update those values before running the script.

## 6. Run the tutorial

From the repository root, run:

```bash
python tutorials/parser_tutorial.py
```

If everything works, the script should finish with:

```text
Parsing completed.
```

## Why the script must be run from the repository root

The tutorial uses relative paths such as:

```text
./tests/data/D6Pm/A52-B128-S_20-140_0.008_4s_17h_D6Pm.brml
```

If you run the script from another directory, Python may not find the example files.

## What the tutorial does

The script:

1. creates an `Openbis` connection using the environment variables
2. logs in to openBIS
3. creates a `BrukerPowderXRDParser`
4. parses three example `.brml` files
5. sends created objects and datasets to openBIS using `bam_masterdata.cli.run_parser`
