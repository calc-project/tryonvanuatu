# Mapping languages to Glottolog

This directory contains a short script that automatically maps the languages to Glottolog via ABVD, where all languages from this source have already been assigned previously.

To recreate the language mapping, the following steps must be followed:

## 1. Create a list of languages from the raw data

In the script `lexibank_tryonvanuatu.py`, set `RECREATE=True` and run the following command (from the base directory):

```bash
cldfbench download lexibank_tryonvanuatu.py
```

This will recreate the file `etc/languages.tsv` from scratch.

(Depending on the stage of the project, you might need to clean up the resulting file to weed out duplicates resulting from typo's)

## 2. Clone ABVD locally

From this directory (`etc`), simply run the following command to clone the ABVD database from Lexibank:

```bash
git clone https://github.com/lexibank/abvd/ --depth 1
```

## 3. Map languages automatically via ABVD

Now you can run the Python script to automatically obtain the mappings from ABVD:

```bash
python map_languages.py
```

Note that there are some mismatches in the exact language names; those are handled by a dictionary within the script that was manually created. If you encounter any issues with the current language mappings, please let us know by opening a GitHub issue!
