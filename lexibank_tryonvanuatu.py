import pathlib
import attr
from clldutils.misc import slug
from pylexibank import Dataset as BaseDataset
from pylexibank import progressbar as pb
from pylexibank import Language
from pylexibank import FormSpec

import xml
import codecs

RECREATE = True

def extract_table(fname):
    """
    Extract table from Transkribus annotation.
    """

    with codecs.open(fname, "r", "utf-8") as f:
        page = xml.dom.minidom.parseString(f.read())

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
            value = text.firstChild.toxml().strip()
        else:
            value = ''
        table[-1] += [value]
    return table


def get_language(row):

    LANG = {
            "1. Fali (OC) (AM)": ["1", "Fali (OC)", "Am"],
            }
    if row.strip() in LANG:
        return LANG[row.strip()]
    
    number = row[:row.index(".")]
    name_ = row[row.index(".") + 2:].strip()
    if "(" in name_:
        name = name_[:name_.index("(")].strip()
        group = name_[name_.index("("):].strip()[1:-1]
    else:
        name = name_
        group = ""
    name = name.strip("*").strip(".")
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


class Dataset(BaseDataset):
    dir = pathlib.Path(__file__).parent
    id = "tryonvanuatu"
    language_class = CustomLanguage
    form_spec = FormSpec(
            separators="~;,/", 
            missing_data=[], 
            first_form_only=True
            )

    def cmd_download(self, args):

        xmlfiles = sorted(self.raw_dir.glob("tryonvanuatu-wordlist/page/*.xml"))
        concepts = []
        languages = []
        data = []
        for fname in xmlfiles:
            args.log.info("Working on {0}...".format(fname))
            img = fname.name + ".jpg"
            page = int(fname.name.split("_p")[1].split(".")[0]) + 171
            table = extract_table(fname)
            current_concepts = table[0]
            current_languages = [row[0] for row in table[1:]]
            concepts += current_concepts[1:]
            languages += current_languages

            # add entries to individual tables
            for row in table[1:]:
                number, name, group = get_language(row[0])
                for concept_, value in zip(current_concepts[1:], row[1:]):
                    cnum, concept = get_concept(concept_)
                    data += [[row[0].strip(), number, name, group,
                              concept_.strip(), cnum, concept, value, str(page), img]]
        
        if RECREATE:
            with codecs.open(self.etc_dir / "concepts.tsv", "w", "utf-8") as f:
                f.write("NUMBER\tENGLISH\n")
                visited = set()
                for row in concepts:
                    number, concept = get_concept(row)
                    if (number, concept) in visited:
                        pass
                    else:
                        visited.add((number, concept))
                        f.write(number + "\t" + concept + "\n")


            with codecs.open(self.etc_dir / "languages.tsv", "w", "utf-8") as f:
                f.write("ID\tNumber\tName\tSubGroup\n")
                for row in languages:
                    number, name, group = get_language(row)
                    f.write(slug(name) + "\t" + number + "\t" + name + "\t" + group + "\n")
            args.log.info("wrote concepts and languages")

        
        with codecs.open(self.raw_dir / "data.tsv", "w", "utf-8") as f:
            f.write("\t".join(
                ["LanguageInSource", "LanguageNumber", 
                 "Language", "Group", 
                 "ConceptInSource",
                 "ConceptNumber", "Concept", 
                 "Value",
                 "Page",
                 "Image"
                 ]
                ) + "\n")
            for row in data:
                f.write("\t".join(row) + "\n")
        args.log.info("wrote data")
        



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
                    #Concepticon_ID=concept["CONCEPTICON_ID"],
                    #Concepticon_Gloss=concept["CONCEPTICON_GLOSS"]
                    )
            concepts[concept["NUMBER"]] = idx
        args.log.info("added concepts")

        # add language
        languages = args.writer.add_languages(lookup_factory="Name")
        args.log.info("added languages")

        # read in data
        data = self.raw_dir.read_csv(
            "data.tsv", delimiter="\t", dicts=True
        )
        # add data
        for entry in pb(data, desc="cldfify", total=len(data)):
            if entry["ENGLISH"] in concepts.keys():
                for key, val in languages.items():
                    args.writer.add_forms_from_value(
                        Language_ID=val,
                        Parameter_ID=concepts[entry["ENGLISH"]],
                        Value=entry[key],
                        Source=["Bodt2019b"],
                    )
