#!/usr/bin/env python3
from qwikidata.qwikidata.sparql import (return_sparql_query_results)
from qwikidata.qwikidata.entity import WikidataItem
from qwikidata.qwikidata import typedefs
from sub_arts import sub_of_artist
from sub_orgs import sub_of_organisation
from sub_occs import sub_of_occurence
import regex
import hashlib
import subprocess
from urllib.parse import unquote
import requests
import re


"""
Autor: xreset00 (René Rešetár) private: renco.resetar@gmail.com, school: xreset00@fit.vutbr.cz
Project: Vytvoření znalostní báze entit z české Wikipedie (shortcut: entity_kb_czech9)

Contains: help functions for "ent_parser.py"
"""

names = {

}

locations = {

}

d_repeat = [

]


# Pocitadlo entit bez ceskeho labelu
not_cs_label: int = 0

# property instance (čeho) : tato položka je jedna konkrétní věc (exemplář, příklad) patřící do této třídy,
#                            kategorie nebo skupiny předmětů
IS_A_THING: typedefs.PropertyId = 'P31'
IS_AN_OCCUPATION: typedefs.PropertyId = 'P106'


def is_concrete_entity(item: WikidataItem, q_item, decide, truthy: bool = True) -> bool:
    """Return True if the Wikidata Item is instance of q_item"""
    if truthy:
        claim_group = item.get_truthy_claim_group(decide)
    else:
        claim_group = item.get_claim_group(decide)

    occupation_qids = [
        claim.mainsnak.datavalue.value["id"]
        for claim in claim_group
        if claim.mainsnak.snaktype == "value"
    ]
    return q_item in occupation_qids


def check_lower_case(name: str):
    if re.findall(r"^[^A-ZÚČŠŽŘÉ]", name):
        return True
    else:
        return False


# Funkcia vypise do suboru druhy hladany argument (typ entity)
def write_type_of_ent(file_) -> None:
    if "organizace" in file_.name:
        file_.write("organisation\t")
    elif "udalosti" in file_.name:
        file_.write("event\t")
    elif "umelci" in file_.name:
        file_.write("person\t")
    else:
        file_.write("\t")


# Funkcia vypise do suboru meno entity
def write_name_of_ent(file_, entity_d) -> None:
    try:
        file_.write(entity_d["labels"]["cs"]["value"] + "\t")  # d_name
    except KeyError:
        file_.write("\t")


# Funkcia vypise do suboru aliasy entity
def write_aliases_of_ent(file_, entity_d) -> None:
    control = True
    try:
        for i, ie in enumerate(entity_d["aliases"]["cs"]):
            if not regex.search(r'\p{IsLatin}', str(entity_d["aliases"]["cs"][int(i)]["value"])):
                if i + 1 == len(entity_d["aliases"]["cs"]):
                    file_.write("0\t")
                continue
            else:
                if i + 1 < len(entity_d["aliases"]["cs"]):
                    control = False
                    if i == 0:
                        file_.write(entity_d["aliases"]["cs"][int(i)]["value"])
                    else:
                        file_.write("|" + entity_d["aliases"]["cs"][int(i)]["value"])
                else:
                    if control:
                        file_.write(entity_d["aliases"]["cs"][int(i)]["value"] + "\t")
                    else:
                        file_.write("|" + entity_d["aliases"]["cs"][int(i)]["value"] + "\t")
    except KeyError:
        file_.write("\t")


# Funkcia vypise do suboru datum zalozenie/zacatia/... entity
def write_start_of_ent(file_, entity_d) -> None:
    was: bool = True
    if file_.name == "organizace":
        try:
            file_.write(entity_d["claims"]["P571"][0]["mainsnak"]["datavalue"]["value"]["time"] + "\t")
            was = False
        except Exception as e:
            pass
    elif file_.name == "udalosti":
        try:
            file_.write(entity_d["claims"]["P580"][0]["mainsnak"]["datavalue"]["value"]["time"] + "\t")
            was = False
        except Exception as e:
            pass
    if was:
        file_.write("\t")


# TODO ANI TRY ANI EXCEPT...
# Funkcia vypise do suboru koniec/zrusenie/... entity
def write_end_of_ent(file_, entity_d) -> None:
    was: bool = False
    if file_.name == "organizace":
        try:
            file_.write(entity_d["claims"]["P576"][0]["mainsnak"]["datavalue"]["value"]["time"] + "\t")
            was = True
        except KeyError:
            pass
    elif file_.name == "udalosti":
        try:
            file_.write(entity_d["claims"]["P582"][0]["mainsnak"]["datavalue"]["value"]["time"] + "\t")
            was = True
        except KeyError:
            pass
    if not was:
        file_.write("\t")


# Funkcia vypise konkretnejsi typ entity napr. pre organisation => company
def write_type_of_type(file_, e_type) -> None:
    try:
        ent_type = str(e_type)
        if ent_type:
            file_.write(ent_type)
    except Exception as e:
        pass


# Funkcia vypise do suboru lokaciu entity
# Najprv skusy zemepisne suradnice, potom mennu lokaciu
def write_location_of_ent(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]["latitude"]) + ", ")
        file_.write(str(entity_d["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]["longitude"]) + "\t")
        # file_.write(str(entity_d["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]["altitude"]) + "|")
        # file_.write(str(entity_d["claims"]["P625"][0]["mainsnak"]["datavalue"]["value"]["precision"]) + "\t")
    except KeyError:
        try:
            location = get_location_from_id(
                str(entity_d["claims"]["P159"][0]["mainsnak"]["datavalue"]["value"]["id"]))
            file_.write(location + "\t")
        except Exception as e:
            try:
                location = get_location_from_id(
                    str(entity_d["claims"]["P276"][0]["mainsnak"]["datavalue"]["value"]["id"]))
                file_.write(location + "\t")
            except Exception as e:
                file_.write("\t")


# Funkcia vypise do suboru popis entity
def write_descrpt_of_ent(file_, entity_d) -> None:
    change = False
    try:
        file_.write(entity_d["descriptions"]["cs"]["value"] + "\t")
        change = True
    except KeyError:
        pass
    if not change:
        file_.write("\t")


# Funkcia vypise do suboru url obrazku z wikidata stranky entity
def write_img_of_ent(file_, entity_d) -> bool:
    output = ""
    folders = ["en", "commons", "fr", "it", "ja", "pl", "pt", "ru", "ca"]

    try:
        img_end = str(entity_d["claims"]["P18"][0]["mainsnak"]["datavalue"]["value"])
    except KeyError:
        file_.write("\t")
        return False

    img_end = img_end.replace(" ", "_")
    for folder in folders:
        try:
            img_end_hash = hashlib.md5(img_end.encode('utf-8')).hexdigest()
            path = "/mnt/data/kb/images/wikimedia/" + folder + "/" + img_end_hash[0] + "/" + img_end_hash[:2]
            bash_command = ["find", path, "-name", img_end]
            output = subprocess.check_output(bash_command, universal_newlines=True, stderr=subprocess.STDOUT)
        except subprocess.CalledProcessError:
            continue
    try:
        img_end_hash = hashlib.md5(img_end.encode('utf-8')).hexdigest()
        if output != "":
            file_.write(output[20:].strip() + "\t")
        else:
            img_url = "https://upload.wikimedia.org/wikipedia/!/{}/{}/{}".format(img_end_hash[0],
                                                                                 img_end_hash[:2], img_end)
            img_url = img_url.replace(" ", "_")
            img_path = "wikimedia/!/{}/{}/{}".format(img_end_hash[0], img_end_hash[:2], img_end)
            img_path = img_path.replace(" ", "_")
            file_.write(img_path.strip() + "\t")
            if "arts" not in file_.name or "occs" not in file_.name or "orgs" not in file_.name:
                with open("images", "a", encoding='utf-8') as f:
                    f.write(unquote(img_url) + "\t" + img_path + "\n")
                    f.close()
    except UnboundLocalError:
        file_.write("\t")
        return False


# Funkcia vypise do suboru url wikipedie stranky pre entitu
def write_wiki_url_of_ent(file_, entity_d) -> None:
    try:
        url_end = str(entity_d["sitelinks"]["cswiki"]["title"])
        url_start = str("https://cs.wikipedia.org/wiki/")
        url_whole = requests.get(url_start + url_end)
        file_.write(unquote(url_whole.url) + "\t")
    except KeyError:
        file_.write("\t")


# Funkcia vypise do suboru rolu entity, ak nejaku ma
def write_roles_of_ent(file_, entity_d) -> None:
    change = False
    try:
        file_.write(entity_d["claims"]["P2868"][0]["mainsnak"]["datavalue"]["value"]["time"] + "\t")
        change = True
    except KeyError:
        try:
            file_.write(entity_d["claims"]["P3831"][0]["mainsnak"]["datavalue"]["value"]["time"] + "\t")
            change = True
        except KeyError:
            change = False
    if not change:
        file_.write("\t")


# Funkcia vypise pravdivostnu hodnotu o fikcionalite entity (1 ak je fiktivna a 0 ak je skutocna)
def write_fictional_of_ent(file_, entity_d) -> None:
    fictional = ""
    try:
        fictional = entity_d["claims"]["P1434"][0]["mainsnak"]["datavalue"]["value"]
    except KeyError:
        try:
            fictional = entity_d["claims"]["P1080"][0]["mainsnak"]["datavalue"]["value"]
        except KeyError:
            try:
                fictional = entity_d["claims"]["P1074"][0]["mainsnak"]["datavalue"]["value"]
            except KeyError:
                try:
                    fictional = entity_d["claims"]["P1445"][0]["mainsnak"]["datavalue"]["value"]
                except KeyError:
                    try:
                        fictional = entity_d["claims"]["P1441"][0]["mainsnak"]["datavalue"]["value"]
                    except KeyError:
                        file_.write("0\t")

    if fictional != "":
        file_.write("1\t")


# Funkcia vypise do suboru url entity z wikidata stranky
def write_wikidata_url_of_ent(file_, entity_d) -> None:
    file_.write("https://www.wikidata.org/wiki/" + entity_d["id"] + "\t")


# Funkcia vypise do suboru url entity u dbpedia stranky
def write_dbpedia_url_of_ent(file_, entity_d) -> None:
    try:
        en_name = entity_d["labels"]["en"]["value"]
        en_name = en_name.replace(" ", "_")
        file_.write("https://dbpedia.org/page/" + en_name + "\t")
    except Exception as e:
        print(e)
        file_.write("\t")


def write_d_name_of_ent(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["sitelinks"]["cswiki"]["title"]) + "\t")
    except KeyError:
        file_.write("\t")


def write_influenced_by(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["claims"]["P737"][0]["mainsnak"]["datavalue"]["value"]["id"]) + "\t")
    except KeyError:
        file_.write("\t")


# TODO student?
def write_influenced(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["claims"]["P737"][0]["mainsnak"]["datavalue"]["value"]["id"]) + "\t")
    except KeyError:
        file_.write("\t")


def write_genres(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["claims"]["P136"][0]["mainsnak"]["datavalue"]["value"]["id"]) + "\t")
    except KeyError:
        file_.write("\t")


def write_ulan_id(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["claims"]["P245"][0]["mainsnak"]["datavalue"]["value"]) + "\t")
    except KeyError:
        file_.write("\t")


def write_other_urls(file_, entity_d) -> None:
    try:
        file_.write(str(entity_d["claims"]["P854"][0]["mainsnak"]["datavalue"]["value"]))
    except KeyError:
        pass


def generic(file, ent, array, entity) -> None:
    """Function writes generic attributes of entities"""
    array[1] = array[1] + 1
    file.write(entity.entity_id + "\t")  # ID
    write_type_of_ent(file)  # type
    # file.write(array[i][0] + "\t")
    write_name_of_ent(file, ent)  # name
    write_d_name_of_ent(file, ent)  # d_name
    write_aliases_of_ent(file, ent)  # aliases
    write_descrpt_of_ent(file, ent)  # description
    write_roles_of_ent(file, ent)  # roles
    write_fictional_of_ent(file, ent)  # fictional
    write_wiki_url_of_ent(file, ent)  # wikipedia_url
    write_wikidata_url_of_ent(file, ent)  # wikidata_url
    write_dbpedia_url_of_ent(file, ent)  # dbpedia
    write_img_of_ent(file, ent)  # images


def others(file, ent, array) -> None:
    """Function writes the unique attributes of entities"""
    if file.name.split("/")[-1] == "organizace" or file.name.split("/")[-1] == "udalosti":
        write_start_of_ent(file, ent)  # inception
        # print("write_start_of_ent")
        write_end_of_ent(file, ent)  # cancelled
        # print("write_end_of_ent")
        write_location_of_ent(file, ent)  # location
        # print("write_location_of_ent")
        write_type_of_type(file, array[0])  # org_type
        # print("write_type_of_type")

    elif file.name.split("/")[-1] == "vizual_umelci":
        write_genres(file, ent)         # art forms
        write_influenced_by(file, ent)  # influencers
        write_influenced(file, ent)     # influencees
        write_ulan_id(file, ent)        # ulan id
        write_other_urls(file, ent)     # other urls

    """New line for new entity"""
    file.write("\n")


SORT = False


# Funkcia hlada zhodu entity v poli entit urciteho typu
# Ak najde zhodu postupne vola funkcie na vypisovanie alebo sama vypisuje
def get_atr(file, ent, array, help_array) -> None:
    entity = WikidataItem(ent)
    if array == sub_of_artist:
        p = IS_AN_OCCUPATION
    else:
        p = IS_A_THING

    for i in array:
        if is_concrete_entity(entity, i, p) and ent not in help_array:
            if check_lower_case(entity.get_label(lang="cs")):
                if check_lower_case(entity.get_label()):
                    break
            try:
                help_array.append(ent)
                generic(file, ent, array[i], entity)
                others(file, ent, array[i])
                # break

                # if array == sub_of_artist and str(array[i][0]) != "udalosti" and str(array[i][0]) != "organizace":
                #     sort = open("arts/" + str(array[i][0]), "a")
                #     generic(sort, ent, array[i], entity)
                #     others(sort, ent, array[i])
                #     sort.close()

            except Exception as e:
                continue


def write_log_file(org, occ, art, i, ncl, d_time, f_time, log_file):
    ff = open(log_file, "w", encoding='utf-8')
    ff.write("{}s: Found {} organisations among {} entities [entities/s: {:.2f}]\n".format(
        int(abs(f_time)), len(org), i, i / d_time))
    ff.write("{}s: Found {} events among {} entities [entities/s: {:.2f}]\n".format(
        int(abs(f_time)), len(occ), i, i / d_time))
    ff.write("{}s: Found {} artists among {} entities [entities/s: {:.2f}]\n".format(
        int(abs(f_time)), len(art), i, i / d_time))
    if int(abs(f_time)) > 3600:
        ff.write("Trvanie parsovania: {:.0f} h\n".format(int(abs(f_time)) / 3600))
    elif int(abs(f_time)) > 60:
        ff.write("Trvanie parsovania: {:.0f} m\n".format(int(abs(f_time)) / 60))
    ff.write("Počet entít bez českého labelu: {}\n".format(str(ncl)))
    ff.write("Počet entít z českým labelom: {}\n".format(str(i - ncl)))
    ff.close()

    var = {k: v for k, v in sorted(sub_of_organisation.items(), key=lambda item: item[1][1], reverse=True)}
    with open("log_organizace", "w") as ff:
        for v in var:
            ff.write(str(sub_of_organisation[v][0]) + "\t" + str(sub_of_organisation[v][1]) + "\n")
    ff.close()

    var = {k: v for k, v in sorted(sub_of_occurence.items(), key=lambda item: item[1][1], reverse=True)}
    with open("log_udalosti", "w") as ff:
        for v in var:
            ff.write(str(sub_of_occurence[v][0]) + "\t" + str(sub_of_occurence[v][1]) + "\n")
    ff.close()

    var = {k: v for k, v in sorted(sub_of_artist.items(), key=lambda item: item[1][1], reverse=True)}
    with open("log_artist", "w") as ff:
        for v in var:
            ff.write(str(sub_of_artist[v][0]) + "\t" + str(sub_of_artist[v][1]) + "\n")
    ff.close()


def get_name_from_id(id) -> str:
    res = {}
    if id:
        sparql_query = 'SELECT  *\
                        WHERE {\
                        wd:%s rdfs:label ?label .\
                        FILTER (lang(?label) = "cs")\
                        }\
                        LIMIT 1\
                        ' % id
        try:
            res = return_sparql_query_results(sparql_query)
        except ValueError as e:
            print("ValueError" + str(e) + str(res))
            if id not in names and id not in d_repeat:
                d_repeat.append(id)
                return ""
            else:
                return ""
        if res is not {}:
            try:
                return str(res["results"]["bindings"][0]["label"]["value"])
            except IndexError or UnboundLocalError:
                if id not in names and id not in d_repeat:
                    d_repeat.append(id)
                    return ""
                else:
                    return ""
    else:
        return ""


def get_location_from_id(id) -> str:
    res = {}
    if id:
        sparql_query = 'SELECT  *\
                        WHERE {\
                        wd:%s rdfs:label ?label .\
                        FILTER (langMatches( lang(?label), "cs" ) )\
                        }\
                        LIMIT 1\
                        ' % id
        try:
            res = return_sparql_query_results(sparql_query)
        except ValueError:
            if id not in locations and id not in d_repeat:
                d_repeat.append(id)
                return ""
            else:
                return ""
        if res is not {}:
            try:
                return str(res["results"]["bindings"][0]["label"]["value"])
            except IndexError or UnboundLocalError:
                if id not in locations and id not in d_repeat:
                    d_repeat.append(id)
                    return ""
                else:
                    return ""
    else:
        return ""  # id


if __name__ == "__main__":
    print("This file implements: get_name_from_id(string: id)\n"
          "                      get_location_from_id(string: id)\n"
          "                      is_concrete_entity(item: WikidataItem, q_item, truthy: bool = True)\n"
          "                      write_type_of_ent(file: file_, array: array)\n"
          "                      write_name_of_ent(file: file_, entity: entity_d)\n"
          "                      write_aliases_of_ent(file: file_, entity: entity_d)\n"
          "                      write_start_of_ent(file: file_, array: array, entity: entity_d)\n"
          "                      write_type_of_type(file: file_, string: e_type)\n"
          "                      write_location_of_ent(file: file_, entity: entity_d)\n"
          "                      write_descrpt_of_ent(file: file_, entity: entity_d)\n"
          "                      write_img_of_ent(file: file_, entity: entity_d) -> bool\n"
          "                      write_wiki_url_of_ent(file: file_, entity: entity_d)\n"
          "                      write_roles_of_ent(file: file_, entity: entity_d)\n"
          "                      write_fictional_of_ent(file: file_, entity: entity_d)\n"
          "                      write_wikidata_url_of_ent(file: file_, entity: entity_d)\n"
          "                      write_dbpedia_url_of_ent(file: file_, entity: entity_d)\n"
          "                      write_d_name_of_ent(file: file_, entity: entity_d)\n"
          "                      check_lower_case(string: name)\n")
