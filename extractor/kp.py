
import mammoth
from bs4 import BeautifulSoup
import pandas as pd
from langid import classify
import re
import pandas as pd
from sklearn.neural_network import MLPClassifier
from laserembeddings import Laser
from docx import Document
from pathlib import Path
import joblib
from .excel_processing import *
import tempfile

# kp_model_location = r"/Users/sakthivel/Documents/SGK/KP/KP_snacks.sav"
# document_location = r"/Users/sakthivel/Documents/SGK/KP/"

classifier = joblib.load(kp_model_location)



def get_input(input_file, input_docx_location):
    if input_file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_docx_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_docx_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_docx_location
    else:
        return document_location + input_file


# get input and split general category and nutrition table information
def html(path):
    with open(path, "rb") as docx_file:
        html1 = mammoth.convert_to_html(docx_file).value
        html_gen = re.sub(r'<table>.*?<\/table>', '', html1)
        Nutrition_table_soup = BeautifulSoup(html1, "html.parser")  # Nutrition table filtered
        General_para_soup = BeautifulSoup(html_gen, "html.parser")  # general category filtered
    return Nutrition_table_soup, General_para_soup


# get nutrition information in list of list
def nutrition_extraction(Nutrition_table_soup):
    nutri = []
    for table in Nutrition_table_soup.find_all('table'):
        _table = []
        for row in table.find_all('tr'):
            _row = []
            for column in row.find_all('td'):
                #             print("-------"*20)
                #             print("hahahahahahaha---->",column)
                #             print("-------"*20)
                if not _row:
                    col = re.sub(r'<(?!b|\/b).*?>', '', str(column))
                    col = re.sub(r'\<\/?br\/?\>', '\n', str(col))
                    _row.append(col)
                else:
                    column = str(column).replace("</p>", "</p>\n").strip()
                    col = re.sub(r'<(?!b|\/b).*?>', '', str(column))
                    col = re.sub(r'\<\/?br\/?\>', '\n', str(col))
                    col = col.strip()
                    _row.append(col)
            _table.append(_row)
        nutri.append(_table)
    return nutri


# feed classifier in nutrtion table information
def nutrtion_structure(nutri):
    total_nut = []
    for nut1, nut2 in enumerate(nutri):
        dict_nutri3 = {}
        if len(nut2) == 3:
            df = pd.DataFrame(nut2)
            ky = df.T
            conlist = ky.values.tolist()
            for line1 in conlist:
                key_cont = line1[0]
                x3len = classifier.predict_proba(laser.embed_sentences(key_cont, lang="en"))[0]
                x3len.sort()
                classified = classifier.predict(laser.embed_sentences(key_cont, lang="en"))[0]
                if x3len[-1] > 0.65:
                    classi_key = classified
                else:
                    classi_key = "Unmapped"
                for lis in range(1, len(line1)):
                    value = line1[lis]
                    value1 = value.replace("kJ", "kJ\n")
                    if "%" in value1:
                        value_header = "PDV"
                    else:
                        value_header = "Value"
                    if classi_key in dict_nutri3:
                        dict_nutri3[classi_key].append({value_header: {classify(value1)[0]: value1}})
                    else:
                        dict_nutri3[classi_key] = [{value_header: {classify(value1)[0]: value1}}]
            total_nut.append(dict_nutri3)
        if len(nut2) > 4:
            for iter1 in nut2:
                key_it2 = iter1[0]
                x = classifier.predict_proba(laser.embed_sentences(key_it2, lang='en'))[0]
                x.sort()
                x_classified = classifier.predict(laser.embed_sentences(key_it2, lang='en'))[0]
                if x[-1] > 0.65:
                    x_key = x_classified
                    for sed in range(1, len(iter1)):
                        sed_value = iter1[sed]
                        if "%" in sed_value:
                            sed_header = "PDV"
                        else:
                            sed_header = "Value"
                        if x_key in dict_nutri3:
                            dict_nutri3[x_key].append({sed_header: {classify(sed_value)[0]: sed_value}})
                        else:
                            dict_nutri3[x_key] = [{sed_header: {classify(sed_value)[0]: sed_value}}]
            total_nut.append(dict_nutri3)

    nutri_diction = {}
    nutri_diction["NUTRITION_FACTS"] = total_nut
    return nutri_diction


# get general category information in list of list and feed classifier
def general_content(General_soup):
    a1_list = []
    for a1 in General_soup.find_all("p"):
        pa1 = re.sub(r'<.*?>', '', str(a1).replace("<strong>", "&lt;b&gt;").replace("</strong>", "&lt;/b&gt;").strip())
        a1_list.append(pa1)
    er = {}
    for l1, l2 in enumerate(a1_list):
        l2_value = l2[0:]
        if "Legal Name:" in l2_value:
            val = l2_value.replace("Legal Name:", "").replace("Ingredients: ", "").strip()
            key = "Legal Name:"
            legal_gen = classifier.predict_proba(laser.embed_sentences(key, lang="en"))[0]
            legal_gen.sort()
            classified_legal = classifier.predict(laser.embed_sentences(key, lang="en"))[0]
            if legal_gen[-1] > 0.65:
                classi_gen = classified_legal
            else:
                classi_gen = "UNMAPPED"
            if classi_gen in er:
                er[classi_gen].append({classify(val)[0]: val})
            else:
                er[classi_gen] = [{classify(val)[0]: val}]
        elif "pack" in l2_value.lower() or "serving" in l2_value.lower() or "servings" in l2_value.lower():
            key_serv1 = "SERVING_PER_PACK"
            value_serv1 = l2_value
            if key_serv1 in er:
                er[key_serv1].append({classify(value_serv1)[0]: value_serv1})
            else:
                er[key_serv1] = [{classify(value_serv1)[0]: value_serv1}]
        elif "adult" in l2_value.lower() or "kcal" in l2_value.lower() and "kj" in l2_value.lower():
            if l1 < len(a1_list) - 1:
                if "kcal" in a1_list[l1 + 1].lower() and "kj" in a1_list[l1 + 1].lower():
                    key_adultref = "NUTRITION_TABLE_CONTENT"
                    value_adultref = a1_list[l1], "\n", a1_list[l1 + 1]
                    value_adultref1 = ''.join(value_adultref)
                    if key_adultref in er:
                        er[key_adultref].append({classify(value_adultref1)[0]: value_adultref1})
                    else:
                        er[key_adultref] = [{classify(value_adultref1)[0]: value_adultref1}]
        else:
            key1 = l2_value
            legal_gen2 = classifier.predict_proba(
                laser.embed_sentences(key1.replace("&lt;b&gt;", '').replace("&lt;/b&gt;", ''), lang="en"))[0]
            legal_gen2.sort()
            classified_legal_gen2 = \
            classifier.predict(laser.embed_sentences(key1.replace("&lt;b&gt;", '').replace("&lt;/b&gt;", ''), lang="en"))[
                0]
            if legal_gen2[-1] > 0.90:
                classi_legal = classified_legal_gen2
            else:
                classi_legal = "UNMAPPED"
            if classi_legal in er:
                er[classi_legal].append({classify(key1)[0]: key1})
            else:
                er[classi_legal] = [{classify(key1)[0]: key1}]
    return er


def main(path):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_docx_location = f'{temp_directory.name}/input_docx.docx'
    file = get_input(path, input_docx_location)
    Nutrition_table_soup, General_soup = html(file)
    nutri = nutrition_extraction(Nutrition_table_soup)
    nutri_diction = nutrtion_structure(nutri)
    er = general_content(General_soup)
    # merging two dictionaries
    kp_merge = {**er, **nutri_diction}
#     output = {path: kp_merge}
    return kp_merge








