import csv
from pycldf import Dataset
from pathlib import Path


# assuming you have cloned the ABVD repo under this directory
abvd = Dataset.from_metadata(Path(__file__).parent / "abvd" / "cldf" / "cldf-metadata.json")
languages = [l for l in abvd["LanguageTable"] if l["author"] == "Tryon (1976)"]

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
    "Port R": "Port Resolution",
    "Shark Bay I": "Shark Bay",
    "Shark Bay II": "Shark Bay",
    "Dixon Reef I": "Dixon Reef",
    "Dixon Reef II": "Dixon Reef",
    "Malo North": "North",
    "Malo South": "South",
    "North T": "Tanna, North",
    "Lehalurup": "Löyöp",
    "Motlav": "Mwotlap",
    "Wusi-Valui": "Valui",
    "Wusi-Mana": "Mana",
    "Repanbitip": "Repanbitipmbangir",
    "Lapwang": "Lapwangtoai",
    "Enfit": "Enfitena",
    "Bonga": "Bongabonga",
    "Tonga": "Tongariki",
    "Vinmavis": "Neve'ei",
    "Burumba": "Baki",
    "Labo": "Ninde",
    "Lenau": "Lenaukas",  # ?
    "Mae-Morae": "Maii",
    "Yatuk": "Yatukwey",  # ?
    "Malfaxal": "Naha'ai",
    "Lonas": "Lonasilian",
    "Malmariv": "Tiale",
    "Lingarak": "Neverver",
    "Fali": "Lonwolwol",
    "Lametin": "Merei"
}

table = []

with open(Path(__file__).parent / "languages.tsv") as f:
    reader = csv.DictReader(f, delimiter="\t")
    for row in reader:
        name = row["Name"]
        name = lang_name_maps[name] if name in lang_name_maps else name
        if row["SubGroup"] == "NULL":
            row["SubGroup"] = ""
        try:
            glottocode = lang_to_glottocode[name]
            row["Glottocode"] = glottocode
            table.append(row)
        except KeyError:
            print(f"{name} not found!")

with open(Path(__file__).parent / "languages.tsv", "w") as f:
    writer = csv.DictWriter(f, fieldnames=table[0].keys(), delimiter="\t")
    writer.writeheader()
    for row in table:
        writer.writerow(row)
