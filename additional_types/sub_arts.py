#!/usr/bin/env python3
sub_of_artist = {
    "Q1028181":  ["malíř", 0],
    "Q42973":    ["architekt", 0],
    "Q2526255":  ["filmový režisér", 0],
    "Q33231":    ["fotograf", 0],
    "Q1281618":  ["sochař", 0],
    "Q3391743":  ["výtvarník", 0],
    "Q1925963":  ["grafik", 0],
    "Q5322166":  ["designér", 0],
    "Q15296811": ["kreslíř", 0],
    "Q627325":   ["grafický designér", 0],
    "Q7541856":  ["keramik", 0],
    "Q10694573": ["textilní výtvarník", 0],
    "Q2865798":  ["sklářský výtvarník", 0],
    "Q2914170":  ["pouliční umělec", 0],
    "Q2815948":  ["zahradní architekt", 0],
    "Q739437":   ["autor plakátů", 0],
    "Q935666":   ["make-up umělec", 0],
    "Q2133309":  ["návrhář interiérů", 0],
    "Q12166078": ["umělecký fotograf", 0],
    "Q22811707": ["dekorátor", 0],
    "Q282718":   ["mozaikář", 0],
    "Q18074503": ["instalační umělec", 0],
    "Q59823990": ["betlemář", 0],
    "Q3400050":  ["hrnčíř", 0],
    "Q21550489": ["konceptuální umělec", 0],
    "Q22343478": ["kolážista", 0],
    "Q15095148": ["autor graffiti", 0],
    "Q18216771": ["video umělec", 0],
    "Q1861368":  ["tetovač", 0],
    "Q21694268": ["amatérský fotograf", 0],
    "Q21178131": ["portrétista", 0],
    "Q47494964": ["miniaturista", 0],
    "Q22343406": ["mediální umělec", 0],
    "Q7016454":  ["umělec nových médií", 0],
    "Q28552423": ["matný malíř", 0],
    "Q40309200": ["umělec siluety", 0],
    "Q56073161": ["origamista", 0],
    "Q63346805": ["komerční umělec", 0],
    "Q1825525":  ["limner", 0],
    "Q29167172": ["architektonický kolorista", 0],
    "Q58423832": ["Heraldický umělec", 0],
    "Q21403281": ["astrofotograf", 0],
    "Q65265332": ["divadelná maskérka", 0],
    "Q3337743":  ["negafa", 0],
    "Q98552221": ["umělec z plastu", 0],
    "Q2223407":  ["advertising artist", 0],
    "Q18510097": ["brusič", 0],
    "Q21000481": ["kinetický umělec", 0],
    "Q56578471": ["umělec pietra dura", 0],
    "Q56884373": ["knižní umělec", 0],
    "Q59922524": ["dvorní umělec", 0],
    "Q59939361": ["amatérský umělec", 0],
    "Q69320328": ["environmentální umělec", 0],
    "Q70585076": ["výrobce diorámy", 0],
    "Q96044701": ["umělec květin", 0],
    "Q101190967":["Letecký fotograf", 0],
    "Q104236974":["Fotograf Bílého domu", 0],

}

"""
Autor: xreset00 (René Rešetár)
Projekt: Vytvoření znalostní báze entit z české Wikipedie (skratka: entity_kb_czech9)

Obsahuje: zoznam entít, ktoré sú podtriedou "artist = Q3391743", alebo by mohli predstavovat udalosť
"""

if __name__ == "__main__":
    for n in sub_of_artist:
        print(sub_of_artist[n][0])
