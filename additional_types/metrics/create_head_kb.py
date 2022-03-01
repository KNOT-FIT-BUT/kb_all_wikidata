#!/usr/bin/env python

# artist
head_kb = "<person>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
           "{m}ART FORMS\t{m}INFLUENCERS\t{m}INFLUENCEES\tULAN ID\t{mu}OTHER URLS\t" \
           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"

# organisation
head_kb += "<organisation>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
           "FOUNDED\tCANCELLED\tLOCATION\tORGANIZATION TYPE\t" \
           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"

# event
head_kb += "<event>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
           "START DATE\tEND DATE\t{m}LOCATIONS\tEVENT TYPE\t" \
           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"

# person
# head_kb += "<person>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
#           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
#           "GENDER\t{e}DATE OF BIRTH\tPLACE OF BIRTH\t{e}DATE OF DEATH\tPLACE OF DEATH\t{m}NATIONALITIES\t" \
#           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"
# group
head_kb += "<group>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
           "{m}INDIVIDUAL NAMES\t{m}GENDERS\t{me}DATES OF BIRTH\t{m}PLACES OF BIRTH\t{me}DATES OF DEATH\t" \
           "{m}PLACES OF DEATH\t{m}NATIONALITIES\t" \
           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"

# geographical
head_kb += "<geographical>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
           "LATITUDE\tLONGITUDE\t{m}GEOTYPES\tCOUNTRY POPULATION\tELEVATION\tAREA\t{m}TIMEZONES\tFEATURE CODE\t" \
           "{m}GEONAMES IDS\t" \
           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"

head_kb += "<settlement>ID\tTYPE\tNAME\tDISAMBIGUATION NAME\t{m}ALIASES\tDESCRIPTION\t{m}ROLES\tFICTIONAL\t" \
           "{u}WIKIPEDIA URL\t{u}WIKIDATA URL\t{u}DBPEDIA URL\t{gm[http://athena3.fit.vutbr.cz/kb/images/]}IMAGES\t" \
           "LATITUDE\tLONGITUDE\t{m}GEOTYPES\tCOUNTRY POPULATION\tELEVATION\tAREA\t{m}TIMEZONES\tFEATURE CODE\t" \
           "{m}GEONAMES IDS\t" \
           "WIKI BACKLINKS\tWIKI HITS\tWIKI PRIMARY SENSE\tSCORE WIKI\tSCORE METRICS\tCONFIDENCE\n"

if __name__ == "__main__":
    print("Creating HEAD-KB...")
    with open("HEAD-KB", "w") as f:
        f.write(head_kb)
    print("HEAD-KB created")
