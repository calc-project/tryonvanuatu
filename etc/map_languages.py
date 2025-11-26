import csv
from pycldf import Dataset
from pyglottolog import Glottolog
from pathlib import Path


# assuming you have cloned the ABVD and Glottolog repo's under this directory
abvd = Dataset.from_metadata(Path(__file__).parent / "abvd" / "cldf" / "cldf-metadata.json")
languages = [l for l in abvd["LanguageTable"] if l["author"] == "Tryon (1976)"]
glottolog = Glottolog(Path(__file__).parent / "glottolog")

# if there are alternate names in ABVD, the names from the original source are in parentheses
lang_to_glottocode = {}
for l in languages:
    name = l["Name"]
    if "(" in name and ")" in name:
        name = name[name.index("(") + 1:name.index(")")]
    glottocode = l["Glottocode"]
    lang_to_glottocode[name] = glottocode

# manually name mapping for mismatches
lang_name_maps = {
    "Port R.": "Port Resolution",
    "Shark Bay I": "Shark Bay",
    "Shark Bay II": "Shark Bay",
    "Dixon Reef I": "Dixon Reef",
    "Dixon Reef II": "Dixon Reef",
    "Malo North": "North",
    "Malo South": "South",
    "North T.": "Tanna, North",
    "Lehalurup": "Löyöp",
    "Motlav": "Mwotlap",
    "Wusi-Valui": "Valui",
    "Wusi-Mana": "Mana",
    "Repanbitip": "Repanbitipmbangir",
    "Lapwang.": "Lapwangtoai",
    "Enfit.": "Enfitena",
    "Bonga.": "Bongabonga",
    "Tonga.": "Tongariki",
    "Vinmavis": "Neve'ei",
    "Burumba": "Baki",
    "Labo": "Ninde",
    "Lenau.": "Lenaukas",
    "Mae-Morae": "Maii",
    "Yatuk.": "Yatukwey",
    "Malfaxal": "Naha'ai",
    "Lonas.": "Lonasilian",
    "Malmariv": "Tiale",
    "Lingarak": "Neverver",
    "Fali": "Lonwolwol",
    "Lametin": "Merei"
}

# set manual exceptions to Glottocode mapping from ABVD
manual_glottomaps = {
    "Maxbaxo": "avok1244",
    "Vovo": "vaoo1237",
    "Toak": "toak1237",
    "Maat": "sout2859",
    "Pango": "sout2856"
}

# abbreviations used by Tryon in the tables, full names are given in the preface
language_abbreviations = {
    "Port R.": "Port Resolution",
    "North T.": "North Tanna",
    "Lapwang.": "Lapwangtoai",
    "Enfit.": "Enfitena",
    "Bonga.": "Bongabonga",
    "Tonga.": "Tongariki",
    "Lenau.": "Lenaukas",
    "Yatuk.": "Yatukwey",
    "Lonas.": "Lonasilian",
}

# manually include geocoordinates that can't be retrieved from Glottolog
missing_coordinates = {
    'Vetumboso': (-13.90299, 167.45138),
    'Merig': (-14.321628, 167.794533),
    'Nasawa': (-15.20185, 168.11301),
    'Narovorovo': (-15.18568, 168.10934),
    'Sesivi': (-16.30603, 167.98469),
    'Toak': (-16.33785, 168.29499),
    'Tongariki': (-17.00607, 168.62417),
    'Makura': (-17.13117, 168.43178),
    'Mataso': (-17.25681, 168.42964),
    'Sesake': (-17.04374, 168.3929),
    'Nguna': (-17.46104, 168.36187),
    'Fila': (-17.747931, 168.296138),
    'Mele': (-17.69099, 168.2681),
    'Aniwa': (-19.25407, 169.60007),
    'Futuna': (-19.52582, 170.21238)
}

for lang, glottocode in manual_glottomaps.items():
    lang_to_glottocode[lang] = glottocode

table = []

with open(Path(__file__).parent.parent / "raw" / "languages.tsv") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        row["Collector"] = row["Collector"].replace("DT", "D.T.Tryon")
        if not row["Group"]:
            assert row["SubFamily"] == "Polynesian" and not row["SubGroup"]
            row["Group"] = row["SubGroup"] = "Polynesian Outlier"
        name = row["Name"]
        row["FullName"] = language_abbreviations.get(name, name)
        name = lang_name_maps[name] if name in lang_name_maps else name
        if row["Region"] == "NULL":
            row["Region"] = ""
        try:
            glottocode = lang_to_glottocode[name]
            row["Glottocode"] = glottocode
            if name in missing_coordinates:
                row["Latitude"], row["Longitude"] = missing_coordinates[name]
            else:
                glottolog_entry = glottolog.languoid(glottocode)
                row["Latitude"], row["Longitude"] = glottolog_entry.latitude, glottolog_entry.longitude
            table.append(row)
        except KeyError:
            print(f"{name} not found!")

# sort by language number
table = sorted(table, key=lambda x: int(x["Number"]))

with open(Path(__file__).parent / "languages.tsv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=table[0].keys(), delimiter="\t")
    writer.writeheader()
    for row in table:
        writer.writerow(row)
