######################################    Coke Word Format     ########################################

# ---- Packages Used
import re
import joblib
import mammoth
import pandas as pd
from langid import classify
from bs4 import BeautifulSoup
import warnings
import tempfile
from .excel_processing import *

warnings.filterwarnings("ignore")

# ---- Loading MLP Classifier for classification keys
# classifier = joblib.load(open(r'/Users/sakthivel/Document# s/SGK/Coke-docx/Coke.sav', 'rb'))
# document_location = r"/Users/sakthivel/Documents/SGK/Coke-docx/"
classifier = joblib.load(cocacola_docx_model_location)


# --------------------------------------------------------------------------------
# Cleaning and Classification
def cleaning_classifiction(key_id, classifier):
    temp = key_id.replace("&lt;b&gt;", '').replace("&lt;/b&gt;", '').replace("&lt;/b&gt;", '').replace('&lt;',
                                                                                                       '').replace(
        '&gt;', '').strip()
    # temp=re.sub('[\W_]+',' ',temp)
    prob = classifier.predict_proba(laser.embed_sentences(temp.strip(), lang='en'))[0]
    prob.sort()
    classified = str(classifier.predict(laser.embed_sentences(temp, lang='en'))[0])
    return temp, prob, classified


# --------------------------------------------------------------------------------
def get_input(input_file, input_docx_location):
    if input_file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_docx_location, 'wb') as docx:
                    docx.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_docx_location, 'wb') as docx:
                    docx.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_docx_location
    else:
        return document_location + input_file


# --------------------------------------------------------------------------------
# Extracting all the tables

def table_extraction(Path):
    # ---- Converting to HTML file
    html = mammoth.convert_to_html(Path).value

    # ---- Creating Beautiful object
    soup = BeautifulSoup(html, "html.parser")

    tables = []
    for i in soup.find_all('table'):
        rows = []
        for j in i.find_all('tr'):
            cells = []
            for k in j.find_all('td'):
                if k.text:
                    temp = str(k).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace("<br>",
                                                                                                             '\n').replace(
                        "<br/>",
                        '\n')  # There might be new line in a cell and to capture it we need to replace the break tag
                    cells.append(
                        (BeautifulSoup(temp, 'html.parser').text).replace('start_bold', '&lt;b&gt;').replace('end_bold',
                                                                                                             '&lt;/b&gt;').replace(
                            '\u200b', '').replace('\xa0', '').strip())
            if len(cells) > 0:
                rows.append(cells)
        if len(rows) > 0:
            tables.append(rows)

    return tables, soup


# --------------------------------------------------------------------------------
# Extracting General Information Tables

def general_tabel(tables):
    temp_keys = []
    values = []
    for i in tables:
        if i[0][0].replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '') in ['General Information', 'Bulgarian', 'English',
                                                                          'Italian', 'Ukrainian']:
            for j in i[1:]:
                # Key and Value rows
                if len(j) == 2:
                    temp_keys.append(j[0])
                    values.append([{classify(j[1])[0]: j[1]}])
                # Keys and Multiple values rows
                elif len(j) > 2:
                    sub = []
                    for k in range(len(j)):
                        if k == 0:
                            temp_keys.append(j[k])
                        else:
                            sub.append({classify(j[k])[0]: j[k]})

                        if len(sub) == len(j[1:]):
                            values.append(sub)

    keys = []
    for i in temp_keys:
        temp, prob, classified = cleaning_classifiction(i, classifier)
        # print('\n',temp,prob[-1],classified)
        if prob[-1] > 0.75:
            keys.append(classified)
        else:
            keys.append('UNMAPPED')

    return keys, values


# --------------------------------------------------------------------------------
# Allergen Table

def allergen_table(tables):
    values = []
    keys = []
    for i in tables:
        if "Allergen Information" in i[0][0]:
            keys.append('ALLERGEN_STATEMENT')
            temp = []
            for j in i[1:]:
                for k in j:
                    temp.append({classify(k)[0]: k})
            values.append(temp)
        elif "Reference intake" in i[0][0] or 'Assunzioni di' in i[0][0]:
            keys.append('NUTRITION_TABLE_CONTENT')
            temp = []
            for j in i:
                for k in j:
                    temp.append({classify(k)[0]: k})
            values.append(temp)

    return keys, values


# --------------------------------------------------------------------------------
def main_nutrition(tables):
    df = []
    for i in tables:
        if 'Nutritional value' in i[0][0]:
            df = pd.DataFrame(i)
            df = ((df.iloc[:, 2:]).values.tolist())[1:]

        elif 'Informazioni nutrizionali' in i[0][0] or 'NUTRITIVNE VRIJEDNOSTI' in i[0][0]:
            df = i[1:]

    return df


# --------------------------------------------------------------------------------
def multi_values(keys, values):
    file = {}
    for i in range(len(keys)):
        file.setdefault(keys[i], []).extend(values[i])
    return file


# --------------------------------------------------------------------------------
def nutrition_table(df):
    nkeys = []
    nvalues = []
    for i in df:
        sub_val = []
        for j in range(len(i)):
            if j > 0:
                if '%' in i[j]:
                    sub_val.append({'PDV': {
                        classify(i[j])[0]: i[j].replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n').strip()}})
                else:
                    sub_val.append({'Value': {
                        classify(i[j])[0]: i[j].replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n').strip()}})
                if len(sub_val) == len(i[1:]):
                    nvalues.append(sub_val)
            else:
                key_id = i[0].replace("от които", '').replace('di cui', '').replace('з них', '').replace('of which',
                                                                                                         '').replace(
                    ':', '').replace('din care', '').replace('Od kojih', '').strip()
                temp, prob, classified = cleaning_classifiction(key_id, classifier)
                nkeys.append(classified)
    nutrition = multi_values(nkeys, nvalues)
    return nutrition


# --------------------------------------------------------------------------------
def nutrition_text(soup):
    # Removing table content from the whole soup value, as we only values outside the table related to nutrition
    a = str(soup)
    for i in soup.find_all('table'):
        a = a.replace(str(i), '')

    # Making the Nutrition text into each nutrition table paragragh
    nutrition_para = (
        a.replace('<p>', '').replace('</p>', '').replace('<br>', '\n').replace('<br/>', '\n').strip()).split('\n\n')

    all_tables = []
    for i in nutrition_para:
        nutri = []

        try:
            # Checking the condition on 1st line of each paragraph and how it starts
            if ((i.split('\n')[0]).split('/')[0]).startswith('Nutritional value') and "Energy" in i.split('\n')[1]:
                temp = i.split('\n')
                for j in temp[1:]:
                    nutri.append([(j.split(":")[0]).split('/')[0], j.split(":")[1]])

            elif 'Nutritional value' in ((i.split('\n')[0]).split('/')[1]) and "Energy" in i.split('\n')[1]:
                temp = i.split('\n')
                for j in temp[1:]:
                    nutri.append([(j.split(":")[0]).split('/')[1], j.split(":")[1]])

            # Italian files
            elif 'Informazioni nutrizionali' in i:
                temp = (i.split(":", 1)[1]).split(";")
                for j in temp:
                    nutri.append([j.split(":")[0], j.split(":")[1]])

            # Crotian files
            elif 'NUTRITIVNE VRIJEDNOSTI' in i.split('\n')[0]:
                temp = i.split('\n')
                for j in temp[1:]:
                    nutri.append([(j.split(":")[0]).split('/')[0], j.split(":")[1]])

        except:
            if 'Nutritional value' in i.split('\n')[0] and "Energy" in i.split('\n')[0]:
                temp = (i.split(":", 1)[1]).split(";")
                for j in temp:
                    nutri.append([(j.split(":")[0]).split("/")[1], j.split(":")[1]])

        all_tables.append(nutri)

    return all_tables


# --------------------------------------------------------------------------------
def coke_main(path):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_docx_location = f'{temp_directory.name}/input_docx.docx'
    docx_file = get_input(path, input_docx_location)
    tables, soup = table_extraction(docx_file)
    keys1, values1 = general_tabel(tables)
    keys2, values2 = allergen_table(tables)
    keys = keys1 + keys2
    values = values1 + values2
    all_nutrition_tables = [main_nutrition(tables)] + nutrition_text(soup)
    file = multi_values(keys, values)

    nutri_list = []
    for i in all_nutrition_tables:
        if i:
            nutri_list.append(nutrition_table(i))
    if nutri_list:
        file['NUTRITION_FACTS'] = nutri_list

    return file

