import pathlib
import attr
from clldutils.misc import slug
from pylexibank import Dataset as BaseDataset
from pylexibank import progressbar as pb
from pylexibank import Language
from pylexibank import FormSpec
from csv import DictReader

import xml
import codecs
import re

RECREATE_CONCEPTS = False
RECREATE_LANGUAGES = True
VALIDATE = False

def extract_table(fname):
    """
    Extract table from Transkribus annotation.
    """

    with codecs.open(fname, "r", "utf-8") as f:
        page = xml.dom.minidom.parseString(f.read())

    # parse footnotes
    # TODO handle the other case where footnotes are different textlines in the SAME region
    footnotes = {}
    footnote_pattern = re.compile(r"^\W*([¹²³⁴⁵])\W*")
    footnote_regions = page.childNodes[0].getElementsByTagName("TextRegion")
    # two possible XML representations for multiple footnotes:
    # 1. under different <TextRegion> nodes,
    # 2. different <TextLine> nodes under the same <TextRegion> node
    for region in footnote_regions:
        textlines = region.getElementsByTagName("TextLine")
        for textline in textlines:
            try:
                footnote = textline.getElementsByTagName("TextEquiv")[0].getElementsByTagName("Unicode")[0].firstChild.toxml().strip()
                if footnote == "* Polynesian Outliers":
                    # this is handled in the language table
                    continue
                footnote_index = re.search(footnote_pattern, footnote).group(1)
                footnote_text = re.sub(footnote_pattern, "", footnote)
                footnotes[footnote_index] = footnote_text
            except IndexError:
                print("Problem with parsing footnote XML:")
                print(region.toxml())
            except AttributeError:
                print("Problem with parsing footnote string:")
                print(footnote)

    # must sort correctly (!)
    cells = sorted(
            page.childNodes[0].getElementsByTagName("TableCell"),
            key = lambda x: (int(x.getAttribute("row")), int(x.getAttribute("col")))
            )
    table = []
    previous_row = -1
    for cell in cells:
        row = int(cell.getAttribute("row"))
        col = int(cell.getAttribute("col"))
        textlines = cell.getElementsByTagName("TextLine")
        if row != previous_row:
            table += [[]]
            previous_row = row
        if textlines:
            textequiv = textlines[0].getElementsByTagName("TextEquiv")[0]
            text = textequiv.getElementsByTagName("Unicode")[0]
            try:
                value = text.firstChild.toxml().strip()
            except AttributeError:
                print(cell.toxml())
                # input()
                value = ""
        else:
            value = ''
        table[-1] += [value]

    return table, footnotes


def get_language(row):
    # handle typos/inconsistencies from the original document
    REPLACEMENTS = {
        "1. Hiw (To": "1. Hiw (To)",
        "9. Verumboso (Ba)": "9. Vetumboso (Ba)",
        "13. Koro (Ba)": "13. Dorig (Ba)",
        "17. Merig": "17. Merig (Ba)",
        "21. Nevenevene (Ma)": "21. Navenevene (Ma)",
        "31. Apma (Pe": "31. Apma (Pe)",
        "52. Akei (Pilipili)": "52. Akei",  # not sure if this one should be here; i think Tryon gives an alternative name in the first instance
        "70 Tutuba": "70. Tutuba",
        "7 . Malo South": "73. Malo South",
        "86. Repanbitip.": "86. Repanbitip",
        "91. Karbol": "91. Katbol",
        "99. Wala": "99. Rano",
        "121. Fali(CC) (Am)": "121. Fali (Am)",
        "132. Mae-Morae(Ep)": "132. Mae-Morae (Ep)",
        "133. Nukaura (Ep)": "133. Nikaura (Ep)",
        "144. Vowa(Ep)": "144. Vowa (Ep)",
        "144. Vovo (Ep)": "144. Vowa (Ep)",
        "161. Sie": "161. Sie (Er)",
        "161. Sie (Ef)": "161. Sie (Er)",
        "162. Ura": "162. Ura (Er)",
        "162. Ura (Ef)": "162. Ura (Er)",
        "170. Lenau (Ta)": "170. Lenau. (Ta)",
    }

    row = REPLACEMENTS.get(row, row)

    # LANG = {
    #        "1. Fali (OC) (AM)": ["1", "Fali (OC)", "Am"],
            #"89 Timbembe": ["89", "Timbembe", ""],
            #"117 Windua (Ma)": ["117", "Windua", "Ma"],
            #"149 Makatea (Sh)": ["149", "Makatea", "Sh"],
            #"177 Aneityum": ["177", "Aneityum", ""],
            #"70 Tutuba": ["70", "Tutuba", ""],
    #        }
    # if row.strip() in LANG:
    #    return LANG[row.strip()]

    if not '.' in row:
        raise ValueError(row)
    
    number = row[:row.index(".")]
    name_ = row[row.index(".") + 2:].strip()
    if "(" in name_:
        name = name_[:name_.index("(")].strip()
        group = name_[name_.index("("):].strip()[1:-1]
    else:
        name = name_
        group = ""
    name = name.strip("*") # .strip(".")
    return number, name, group


def get_concept(row):
   number = row[:row.index(".")]
   concept = row[row.index(".") + 2:].strip()
   return number, concept



@attr.s
class CustomLanguage(Language):
    Location = attr.ib(default=None)
    Remark = attr.ib(default=None)
    Number = attr.ib(default=None)
    Region = attr.ib(default=None)
    FullName = attr.ib(default=None)


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "tryonvanuatu"
    language_class = CustomLanguage
    form_spec = FormSpec(
            separators="~;,/", 
            missing_data=[], 
            first_form_only=True,
            replacements=[(" ", "_")]
            )

    def cmd_download(self, args):
        xmlfiles = sorted(self.raw_dir.glob("tryonvanuatu-wordlist/page/*.xml"))
        concepts = []
        languages = []
        data = []
        errors = set()
        for fname in xmlfiles:
            args.log.info("Working on {0}...".format(fname))
            img = fname.name + ".jpg"
            page = int(fname.name.split("_p")[1].split(".")[0]) + 171
            table, footnotes = extract_table(fname)
            current_concepts = table[0]
            current_languages = [row[0] for row in table[1:]]
            concepts += current_concepts[1:]
            languages += current_languages

            # add entries to individual tables
            for row in table[1:]:
                try:
                    number, name, group = get_language(row[0])
                    for concept_, value in zip(current_concepts[1:], row[1:]):
                        footnotes_pattern = re.compile(r"[¹²³⁴⁵]")
                        match = re.search(footnotes_pattern, value)
                        if match:
                            footnote_index = match.group()
                            value = re.sub(footnotes_pattern, "", value)
                            if footnote_index not in footnotes:
                                args.log.warning(f"Footnote {footnote_index} not in footnotes ({fname})")
                            footnote = footnotes.get(footnote_index, "")
                        else:
                            footnote = ""
                        cnum, concept = get_concept(concept_)
                        data += [[row[0].strip(), number, name, group,
                                  concept_.strip(), cnum, concept, value, str(page), img, footnote]]
                except ValueError:
                    args.log.info("Problem with entry '{0} / {1}'".format(fname, row))
                    errors.add((fname, row[0]))


        if RECREATE_CONCEPTS:
            with codecs.open(self.etc_dir / "concepts.tsv", "w", "utf-8") as f:
                f.write("NUMBER\tENGLISH\n")
                visited = set()
                for row in concepts:
                    try:
                        number, concept = get_concept(row)
                        if (number, concept) in visited:
                            pass
                        else:
                            visited.add((number, concept))
                            f.write(number + "\t" + concept + "\n")
                    except ValueError:
                        args.log.warning(f"Problem with parsing concept: {row}")


        if RECREATE_LANGUAGES:
            language_triples = set()  # triples of (number, name, region)
            for row in set(languages):
                try:
                    number, name, region = get_language(row)
                    language_triples.add((number, name, region))
                except ValueError:
                    args.log.warning(f"Problem with parsing language: {row}")

            with codecs.open(self.raw_dir / "languages.tsv", "w", "utf-8") as f:
                f.write("ID\tNumber\tName\tRegion\n")
                for number, name, region in language_triples:
                    f.write(slug(name) + "\t" + number + "\t" + name + "\t" + region + "\n")

            args.log.info("wrote concepts and languages")

        
        with codecs.open(self.raw_dir / "data.tsv", "w", "utf-8") as f:
            f.write("\t".join(
                ["LanguageInSource",
                 "LanguageNumber",
                 "Language",
                 "Region",
                 "ConceptInSource",
                 "ConceptNumber",
                 "Concept",
                 "Value",
                 "Page",
                 "Image",
                 "Footnote"
                 ]
                ) + "\n")
            for row in data:
                f.write("\t".join(row) + "\n")
        args.log.info("wrote data")

        if VALIDATE:
            # collect concepts
            concepts = set()
            with open(self.etc_dir / "concepts.tsv") as f:
                reader = DictReader(f, delimiter="\t")
                for row in reader:
                    concepts.add((row["NUMBER"], row["ENGLISH"]))

            # collect languages
            languages = set()
            with open(self.etc_dir / "languages.tsv") as f:
                reader = DictReader(f, delimiter="\t")
                for row in reader:
                    group = row["Region"] or ""
                    languages.add((row["Number"], row["Name"], group))

            visited_issues = set()
            for row in data:
                page = str(int(row[8]) - 171)
                # validate concepts
                concept_number, concept = row[5], row[6]
                if (concept_number, concept) not in concepts and (page, concept_number, concept) not in visited_issues:
                    args.log.warning(f"{page}: {concept_number}. {concept}")
                    visited_issues.add((page, concept_number, concept))
                # validate languages
                language_num, language, group = row[1], row[2], row[3]
                if (language_num, language, group) not in languages and (page, language_num, language, group) not in visited_issues:
                    msg = f"{page}: {language_num}. {language}"
                    if group:
                        msg += f" ({group})"
                    args.log.warning(msg)
                    visited_issues.add((page, language_num, language, group))

            with (open(self.etc_dir / "concepts-issues.tsv", "w") as concept_file,
                  open(self.etc_dir / "languages-issues.tsv", "w") as language_file):
                concept_file.write("PAGE\tNUMBER\tCONCEPT\n")
                language_file.write("PAGE\tNUMBER\tLANGUAGE\tGROUP\n")
                for issue in visited_issues:
                    if len(issue) == 3:
                        concept_file.write("\t".join(issue) + "\n")
                    else:
                        language_file.write("\t".join(issue) + "\n")

        #for a, b in errors:
        #    args.log.info("problem: {0} / {1}".format(a, b))


    def cmd_makecldf(self, args):
        # add bib
        args.writer.add_sources()
        args.log.info("added sources")

        # add concept
        concepts = {}
        for concept in self.concepts:
            idx = concept["NUMBER"] + "_" + slug(concept["ENGLISH"])
            args.writer.add_concept(
                    ID=idx,
                    Name=concept["ENGLISH"],
                    Concepticon_ID=concept.get("CONCEPTICON_ID"),
                    Concepticon_Gloss=concept.get("CONCEPTICON_GLOSS")
                    )
            concepts[concept["NUMBER"]] = idx
        args.log.info("added concepts")

        # add language
        languages = args.writer.add_languages(lookup_factory="Number")
        args.log.info("added languages")

        # read in data
        data = self.raw_dir.read_csv(
            "data.tsv", delimiter="\t", dicts=True
        )
        # add data
        for entry in pb(data, desc="cldfify", total=len(data)):
            if entry["ConceptNumber"] in concepts and entry["LanguageNumber"] in languages:
                args.writer.add_forms_from_value(
                    Language_ID=languages[entry["LanguageNumber"]],
                    Parameter_ID=concepts[entry["ConceptNumber"]],
                    Value=entry["Value"],
                    Source="Tryon1976",
                    Comment=entry["Footnote"]
                )
