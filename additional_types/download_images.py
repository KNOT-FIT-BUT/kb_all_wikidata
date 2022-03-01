"""
Author: René Rešetár (xreset00)
Projekt: Vytvoření znalostní báze entit z české Wikipedie (skratka: entity_kb_czech9)

Obsahuje: Skript na stiahnutie obrázkov z "images"
"""

from help_functions import *
import os
import time
import shutil
folders = ["commons", "en", "fr", "it", "ja", "pl", "pt", "ru", "ca"]

"""
    ----------------- ZACIATOK MAIN --------------------
"""

if __name__ == '__main__':

    try:
        l = open("images_processed", "a")
        f = open("images", "r")
    except IOError as e:
        print(e)
    counter = 0
    for c, i in enumerate(f):
        try:
            t = i.split()
        except IndexError as e:
            l.write(i + e)
        for folder in folders:
            url = t[0].replace("!", folder)
            path = t[1].replace("!", folder)
            if folder == "commons":
                path_test_1 = path[:39]
                path_test_2 = path[:42]
            else:
                path_test_1 = path[:34]
                path_test_2 = path[:47]
            try:
                url = url.replace(",", "%2C")
                url = url.rstrip()
                time.sleep(1)
                response = requests.head(url)
                # content = requests.get(url).content
                r = requests.get(url, stream=True)
                counter += 1
                time.sleep(1)
                if response.headers.get('content-type') == "image/jpeg":
                    print(counter, "\t", path)
                    if not os.path.exists(path_test_1):
                        os.mkdir(path_test_1)
                    if not os.path.isdir(path_test_2):
                        os.mkdir(path_test_2)
                    try:
                        l.write(path + "\t" + str(r.status_code) + "\t" + str(r.raw) + "\n")
                        if r.status_code == 200:
                            r.raw.decode_content = True
                            f = open(path, "wb")
                            shutil.copyfileobj(r.raw, f)
                            l.write(url + "\t" + path)
                            f.close()
                        break
                    except Exception as e:
                        l.write(str(path) + "\te\t" + str(e))
                        continue
                    break
                else:
                    p = open("NF_images", "a")
                    p.write(str(path) + "\n")
            except Exception as e2:
                l.write(str(path) + "\te2\t" + str(e2))
                continue
    l.close()


