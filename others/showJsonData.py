#!/usr/bin/env python3
# Project: Wikidata
# Author: Pavel Raur

import re
import json
import sys
import os

# usage: ./showJsonData.py path first_entity last_entity
# to display first entity of file.json use:
# python3 showJsonData.py file.json 0 1


# Recursivly parses and prints json entities
# entities are stored in dict (loaded by json.loads(json_line))
# format is "key" : "value"
def parseEntity(entity, num):
    if type(entity) == dict:
        for key in entity: # for each record in given data
            if type(entity[key]) == dict:
                print(num * "\t" + str(key) + " :") # print key name
                parseEntity(entity[key], num+1) # recurse into each value
            elif type(entity[key]) == list:
                print(num * "\t" + str(key) + " :") # print list name
                if len(entity[key]) > 0: # if list is not empty
                    for i in range(0, len(entity[key])): # recurse into each value
                        parseEntity(entity[key][i], num+1)
                else: # if list is empty - print emty line
                    print((num+1) * "\t")
            else: # print key : value - if there is no need to recurse into value
                print(num * "\t" + str(key) + " : " + str(entity[key]))
    else: # if given data are not dictionary, just print it - usually when recursing into list
        print(num * "\t" + str(entity))
    # parseEntity - end of function

def help():
    print("Usage:")
    print("python3 showJsonData.py path first_entity last_entity\n")
    print("To display first entity of file.json use:")
    print("python3 showJsonData.py file.json 0 1\n")

def main():
    if len(sys.argv) > 1:
        if sys.argv[1] == "--help":
            help()
            return 0
    if len(sys.argv) != 4:
        print("Bad args!\nUse \"--help\" option for more info!")
        return 1

    line_max = int(sys.argv[3])
    line_min = int(sys.argv[2])
    with open(sys.argv[1], "r") as f:
        #remove [
        beginChar = f.readline()
        counter = 0
        while counter < line_min:
            line = f.readline()
            counter+=1
        while counter < line_max:
            line = f.readline()
            if line[0]==']':
                print("File end reached!")
                sys.exit(0)
            if line[-2] == ',':
                line = line[:-2]
            entity = json.loads(line)
            
            parseEntity(entity, 0)
            counter+=1
    return 0

if __name__ == "__main__":
    sys.exit(main())

