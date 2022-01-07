#!/usr/bin/env python3
import argparse

from help_functions import *
from sub_orgs import *
from sub_occs import *
from sub_arts import *
from qwikidata.qwikidata.json_dump import WikidataJsonDump
import time

"""
GENERAL
Hľadané atribúty:   id [ID]: samotny item
                    type [Type]: P2308 (trieda = qualifier to define a property constraint in combination with "property
                                 constraint")
                                 P31 (je = tato položka je jedna konretna vec exemplar)
                                 P279 (podtrieda = tento objekt je podtriedou...)
                    name [Name]: item["labels"]["cs"]["value"] 
                    d_name [Display_name]: pri wikidata to reprezentuje ID
                    alias [Aliases]: v poli entity_d["aliases"]["cs"] 
                    descrpt [Description]:  entity["descriptions"]["en/cs"] 
                    roles [roles]: P2868 (subject has role) 
                                 P3831 (object has role)   
                    fictional [fictional]:  P1080 - (from narrative universe) subject's fictional entity is in the 
                                                    object narrative.
                                                    See also P1441 (present in work) and P1445
                                            P1434 - (takes place in fictional universe) the subject is a work describing
                                                    a fictional universe,
                                                    i.e. whose plot occurs in this universe.
                                            P1074 - (fictional analog of) used to link an entity or class of entities 
                                                    appearing in a creative
                                                    work with the analogous entity or class of entities in the real 
                                                    world
                                            P1445 - (fictional universe described in) to link a fictional universe with 
                                                    a work that
                                                    describes it: <universe> "described in the work:" <work>
                                            P1441 - (present in work) this (fictional) entity or person is present in 
                                                    the story of that work
                                                    (use P2860 for works citing other works, P361/P1433
                                                    for works being part of / published in other works,
                                                    P1343 for entities described in non-fictional accounts)
                    wiki_url [Wikipedia URL]: Spojenim "https://cs.wikipedia.org/wiki/" 
                                                                        + 
                                                        entity_d["sitelinks"]["cswiki"]["title"]
                    wikidata_url [wikidata_url]:    https://www.wikidata.org/wiki/ID
                    dbpedia_url [dbpedia_url]       http://dbpedia.org/page/Nintendo/english_meno
                    imgs [Images]: P18 (obrazok = odkaz na subor)
                                   meno obrazku spolu z jeho hashom hladame v /mnt/data/kb/images/wikimedia/
                                   ak sa meno nenajde hladame ho na internete pomocou requests kniznice
                                   stiahneme ho a ulozime do prislusneho adresara pomocou hashu
                    
Organisation
Hladane atributy:   inception [Inception]: P571 (cas kdy byl objekt zalozeny)
                    cancelled [Cancelled]: P576 (datum zaniku = datum kdy byla organizace rozpustena nebo 
                    budova zborena, datum záaiku veci)
                    org_type [Organization type]: item["claims"]["P31"][0]["mainsnak"]["datavalue"]["value"]["id"]
                    location [Location]:   P625 (zemepisne suradnice)
                                           P276 (miesto = umiestnenie polozky predmetu ci udalosti)
                                   
Occurence
Hladane atributy:   beginning [Beginning]: P580 (start time = pociatok nejakeho stavu)
                    end [End]: P582 (end time = koniec nejakeho stavu)
                    location [Location]:   P625 (zemepisne suradnice)
                                           P276 (miesto = umiestnenie polozky predmetu ci udalosti)
"""


def parse_arguments():
    """
    Parses arguments from command line
    :return: True if arguments are valid and False if invalid
    """
    dump = "/mnt/minerva1/nlp/datasets/wikipedia/wikidata-20200727/wikidata-20200720-all.json"
    parser = argparse.ArgumentParser()
    parser.add_argument('-D', '--dump', default=dump, type=str, help='Path to json dump')
    parser.add_argument('-F', '--final', action='store_true', help='If calling from start_parsing.sh to save '
                                                                   'results in directory "final"')
    parser.add_argument('-T', '--test', action='store_true', help='If calling for testing and development purposes of '
                                                                  'ent_parser.py use this option')
    console_args = parser.parse_args()
    if console_args.final:
        return console_args.dump, "final/"
    elif console_args.test:
        return console_args.dump, "test/"
    else:
        return console_args.dump, ""


# ===============   Start of the main function   ===============


if __name__ == "__main__":
    wjd_dump_path, where = parse_arguments()
    # Create an instance of WikidataJsonDump
    # wjd_dump_path = "/mnt/minerva1/nlp/datasets/wikipedia/wikidata-20200803-all.json"
    wjd = WikidataJsonDump(wjd_dump_path)

    i = open("images", "w")
    i.close()
    orgs = []
    occs = []
    arts = []
    t1 = time.time()
    p: int = 0
    ii: int = 0
    dt: float = 0
    t: float = 0
    not_cs_label: int = 0

    udalosti = open(where + "udalosti", "w", encoding='utf-8', newline='')
    organizace = open(where + "organizace", "w", encoding='utf-8', newline='')
    umelci = open(where + "vizual_umelci", "w", encoding='utf-8', newline='')
    l_f = where + "log_file"

    for ii, entity_dict in enumerate(wjd):
        # TIME STATS PRINT
        if ii % 1000 == 0:
            t2 = time.time()
            dt = t2 - t1
            t = t1 - t2
            print(
                "{}s: found {} orgs and {} occs and {} arts and {} without cs label among {} entities [entities/s: {"
                ":.2f}]".format(
                    int(abs(t)), len(orgs), len(occs), len(arts), not_cs_label, ii, ii / dt
                )
            )

        # ENTITY VALIDITY CHECK
        try:
            p = entity_dict["labels"]["cs"]["value"]  # If entity does not have czech label
        except KeyError:
            not_cs_label = not_cs_label + 1
            continue
        try:
            l = entity_dict["claims"]["P279"]  # If entity is also subclass
            continue
        except KeyError:
            pass
        try:
            entity = WikidataItem(entity_dict)  # If valid item
        except ValueError:
            continue

        # DATA EXTRACTION
        get_atr(organizace, entity_dict, sub_of_organisation, orgs)
        get_atr(udalosti, entity_dict, sub_of_occurence, occs)
        get_atr(umelci, entity_dict, sub_of_artist, arts)

    # LOG INFO WRITING
    write_log_file(orgs, occs, arts, ii, not_cs_label, dt, t, l_f)
    udalosti.close()
    organizace.close()
    umelci.close()
