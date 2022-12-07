# -------------------------------------------- Aldi Equator -----------------------------------------------#

# Packages used
import io
import re
import joblib
import tabula
import camelot
import pdfplumber
import numpy as np
import pandas as pd
from langid import classify
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from laserembeddings import Laser
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import tempfile
# for language detection

from .mongo_interface import MongoSearch

from .excel_processing import *

# --------------------------------------------------------------------------------


# document_location = r"/Users/sakthivel/Documents/SGK/ALDI PDF/"
# temp_directory = tempfile.TemporaryDirectory(dir=document_location)

# Loading MLP Classifier for classification keys
classifier = joblib.load(aldi_pdf_model)
# --------------------------------------------------------------------------------
nutri_keys = ['Beta Glucan', 'Fructans', 'Resistant Starch', 'Sugar',
              'Carbohydrate', 'Fibre', 'Total Fibre', 'Energy', 'Fat', 'Iron', 'Potassium', 'Protein',
              'Saturated Fat', 'Sodium', 'Vitamin B1', 'Vitamin B3', 'Vitamin B6', 'Vitamin E', 'Zinc', 'Fibre', 'Salt']


# --------------------------------------------------------------------------------

# path=r"/Users/praveen/Documents/Study/Projects/Aldi/Ice Creams/443343.pdf"

def custom_language_detection(text):
    if text and str(text).strip():
        language = MongoSearch(text=text).detect_language()
        if language:
            return language
        with GoogleTranslate(text) as output:
            return output['language']
    else:
        return "en"

def get_input(input_file, input_pdf_location):
    if input_file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location+input_file


def data_extraction(path, page):
    joined_tables = []
    plumb = pdfplumber.open(path)
    tables = plumb.pages[page - 1].extract_tables()

    for table in tables:
        txt_list = table
        for row in txt_list:
            _row = []
            for value in row:
                if isinstance(value, str) and str(value).strip():
                    _row.append(value)
            if _row:
                joined_tables.append(_row)
    return joined_tables


# --------------------------------------------------------------------------------
# Cleaning and Classification
def cleaning_classifiction(key_id):
    temp = key_id.replace("&lt;b&gt;", '').replace("&lt;/b&gt;", '').replace("&lt;/b&gt;", '').replace('&lt;',
                                                                                                       '').replace(
        '&gt;', '').strip()
    temp = re.sub('[\W_]+', ' ', temp)
    prob = classifier.predict_proba(laser.embed_sentences(temp.strip(), lang='en'))[0]
    prob.sort()
    classified = str(classifier.predict(laser.embed_sentences(temp, lang='en'))[0])
    return temp, prob, classified


# --------------------------------------------------------------------------------
# Extracting data from rows which single value
def single_content(tables):
    keys=[]
    values=[]
    for i in tables:
        for j in i:
            if len(j)==1:
                temp,prob,classified = cleaning_classifiction(j[0])
                if prob[-1]>0.7 and classified in ['MANUFACTURING_SITE','CONSUMER_GUARANTEE','SERVING_SIZE'] and len(temp)<250:
                    keys.append(classified)
                    values.append([{classify(j[0])[0]:j[0]}])
                elif "Reference Intake" in j[0].strip():
                    for y in j[0].split('\n'):
                        if "reference intake" in y.lower().strip() or 'typical values' in y.lower().strip():
                            keys.append("NUTRITION_TABLE_CONTENT")
                            values.append([{classify(y)[0]:y}])#.split('\n')[1]}])
                else:
                    keys.append('UNMAPPED')
                    values.append([{classify(j[0])[0]:j[0]}])
    return keys,values

# --------------------------------------------------------------------------------
# Extracting data from rows which has single key and value
def key_values_rows(tables):
    nkeys = []
    nvalues = []
    keys = []
    values = []
    for table in tables:
        for row in table:
            if len(row) == 2:
                key_id = re.sub(r"\([^()]*\)", "", row[0]).replace('of which',
                                                                   '').strip()  # Removing text within bracket along with bracket
                key_id = re.sub(r'[^a-zA-Z]', ' ', key_id)  # Keeping only alphabets
                temp, prob, classified = cleaning_classifiction(key_id.strip())
                row_value = row[1].replace('<', '&lt;').replace('>', '&gt;').replace('(text only)', '').strip()
                if prob[-1] > 0.65 and classified in nutri_keys:
                    nkeys.append(classified)
                    sub_val = []
                    sub_val.append({'copy_notes': {'en': row[0].replace('<', '&lt;').replace('>', '&gt;').strip()}})
                    if '%' in row[1]:
                        sub_val.append({'PDV': {'en': row_value}})
                    else:
                        sub_val.append({'Value': {'en': row_value}})
                    nvalues.append(sub_val)

                elif prob[-1] > 0.7:
                    keys.append(classified)
                    values.append([{classify(row[1])[0]: row_value}])
                else:
                    keys.append('UNMAPPED')
                    values.append([{classify(row[1])[0]: row_value}])

    return keys, values, nkeys, nvalues


# --------------------------------------------------------------------------------
# Nutritional Information

def main_nutrition_table(tables):
    nkeys = []
    nvalues = []
    keys = []
    values = []
    # others=[]
    for i in tables:
        for r in i:
            if len(r) > 2:
                key_id = re.sub("[\(\[].*?[\)\]]", "", r[0]).replace('of which', '').strip()
                key_id = re.sub(r'[^a-zA-Z]', ' ', key_id)  # Keeping only alphabets
                temp, prob, classified = cleaning_classifiction(key_id.strip())
                second_element = (r[1]).replace("&lt;b&gt;", '').replace("&lt;/b&gt;", '').replace("&lt;/b&gt;",
                                                                                                   '').replace('&lt;',
                                                                                                               '').replace(
                    '&gt;', '').replace('<', '').replace('>', '').strip()

                try:
                    # print(int(second_element))
                    # Checking for the pattern where in the list 1st element is nutrition key and 2nd element is value
                    if prob[-1] > 0.65 and classified in nutri_keys and (
                            float(second_element) or float(second_element) == 0.0):
                        nkeys.append(classified)
                        sub_val = []
                        sub_val.append({'copy_notes': {'en': r[0].replace('<', '&lt;').replace('>', '&gt;').strip()}})
                        values_list = r[1:]
                        for j in range(len(values_list)):
                            row_value = values_list[j].replace('<', '&lt;').replace('>', '&gt;').replace('\r',
                                                                                                         '\n').strip()
                            if '%' in values_list[j]:
                                sub_val.append({'PDV': {'en': row_value}})
                            else:
                                sub_val.append({'Value': {'en': row_value}})
                        nvalues.append(sub_val)
                except:
                    # pass
                    # When Ingredients has multiple values
                    if 'Ingredients Declaration' in r[0]:
                        ingre_val = '\n'.join(r[1:])
                        keys.append('INGREDIENTS_DECLARATION')
                        values.append([{classify(ingre_val)[0]: ingre_val}])
                    else:
                        keys.append('UNMAPPED')
                        values.append([{classify(r[1])[0]: r[1]}])
                    # others.append(r)

    return keys, values, nkeys, nvalues


# --------------------------------------------------------------------------------
# Nutritional Information

def nutrition_transpose(path, page_number):
    b = tabula.read_pdf(path, lattice=True, pages=page_number)
    aws = []
    aqs = []
    for l in range(len(b)):
        #  Making each table into list
        w = (b[l].dropna(how='all', axis=1)).T.reset_index().T.fillna('').values.tolist()

        for i in w:
            temp = []
            for j in i:
                if j:
                    temp.append(j)

            if len(temp) > 1:
                # print(temp[0])
                # Checking for the pttern where in the list 1st element is nutrition key and 2nd element is nutrition key
                fst = re.sub("[\(\[].*?[\)\]]", "", temp[0])
                fst = re.sub("[^0-9]", '', fst)
                # print(fst)
                try:
                    snd = re.sub("[^0-9]", '', temp[1])
                    # print(fst,snd)
                    if temp[0] in nutri_keys and temp[1] in nutri_keys and len(temp[0])<30:
                        # print(temp)
                        aws.append(temp)
                    elif float(fst) and float(snd) and ':' not in temp[0] and 'Time' not in temp[0] and len(temp[0])<30:
                        # print(temp)
                        aws.append(temp)
                except:
                    pass
            else:
                # When there is only 1 nutrition element is there (Energy)
                aqs.append(temp)

    nkeys = []
    nvalues = []
    # Transposing the nutrition table to make key and value in the same row
    aws = (pd.DataFrame(aws).T).values.tolist()

    nt = []
    for i in aws:
        aws_temp = []
        for j in i:
            if j != None and j != '':
                aws_temp.append(j)
        if aws_temp:
            nt.append(aws_temp)

    for i in nt:
        temp, prob, classified = cleaning_classifiction(i[0])
        if prob[-1] > 0.65:
            nkeys.append(classified)
            sub_val = []
            sub_val.append({'copy_notes': {'en': i[0].replace('<', '&lt;').replace('>', '&gt;').strip()}})
            vl = i[1:]

            for j in range(len(vl)):
                row_value = str(vl[j]).replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n').strip()
                if '%' in row_value:
                    sub_val.append({'PDV': {'en': row_value}})
                else:
                    sub_val.append({'Value': {'en': row_value}})
            nvalues.append(sub_val)
        else:
            nkeys.append(i[0])
            sub_val = []
            sub_val.append({'copy_notes': {'en': i[0].replace('<', '&lt;').replace('>', '&gt;').strip()}})
            vl = i[1:]
            for j in range(len(vl)):
                row_value = str(vl[j]).replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n').strip()
                if '%' in row_value:
                    sub_val.append({'PDV': {'en': row_value}})
                else:
                    sub_val.append({'Value': {'en': row_value}})
            nvalues.append(sub_val)
    # Usually the single element is Energy
    for i in range(len(aqs)):
        try:
            if aqs[i][0] == 'Energy' and 'kJ' in aqs[i + 1][0] and '%' in aqs[i + 2][0]:
                nkeys.append('Energy')
                nvalues.append([{'Value': {
                    "en": str(aqs[i + 1][0]).replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n')}},
                                {'PDV': {'en': str(aqs[i + 2][0]).replace('<', '&lt;').replace('>', '&gt;')}}])
                # print(ing)
        except:
            pass
    nutri = [{}]
    if nkeys and nvalues:
        nutri = [multi_key_value(nkeys, nvalues)]

    return nutri


# --------------------------------------------------------------------------------
# Separate multiple nutrition present in a page
def separate_nutrition(nutrition_keys, nutrition_values):
    st_id = []
    for i in range(len(nutrition_keys)):
        if nutrition_keys[i] == 'Energy' and nutrition_keys[i - 1] != 'Energy':
            st_id.append(i)

    nutrition_tables = []
    if st_id:
        for i in range(len(st_id)):
            try:
                temp_keys = nutrition_keys[st_id[i]:st_id[i + 1]]
                temp_values = nutrition_values[st_id[i]:st_id[i + 1]]
                nutrition_tables.append(multi_key_value(temp_keys, temp_values))
            except IndexError:
                temp_keys = nutrition_keys[st_id[i]:]
                temp_values = nutrition_values[st_id[i]:]
                nutrition_tables.append(multi_key_value(temp_keys, temp_values))
    else:
        nutrition_tables.append(multi_key_value(nutrition_keys, nutrition_values))

    return nutrition_tables


# --------------------------------------------------------------------------------
# Function to create dict with same key with multiple values in list
def multi_key_value(keys, values):
    file = {}
    for i in range(len(keys)):
        file.setdefault(keys[i], []).extend(values[i])
    return file


# --------------------------------------------------------------------------------
# Bold Attributes
def get_contents_with_attributes(path, pages):
    output_io = io.StringIO()
    with open(path, 'rb') as input:
        extract_text_to_fp(input, output_io,
                           laparams=LAParams(line_margin=0.21, line_overlap=0.4, all_texts=False),
                           output_type='html', page_numbers=[pages], codec=None)
    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    final_content = []
    for div in html.find_all("div"):
        temp_div = []
        for span in div.find_all("span"):
            if 'bold' in span['style'].lower():
                if span.text.strip():
                    temp_div.append(f'<b>{span.text.strip()}</b>')
            if 'bold' not in span['style'].lower():
                if span.text.strip():
                    temp_div.append(span.text.strip())
        if temp_div:
            final_content.append(" ".join(temp_div))
    output_io.close()
    return final_content


# --------------------------------------------------------------------------------

def bold_convertion(path, keys, values, pages):
    l = get_contents_with_attributes(path, pages - 1)
    bold = []
    for i in range(len(keys)):
        if keys[i] == 'INGREDIENTS_DECLARATION' or keys[i] == 'ALLERGEN_STATEMENT':
            bold.append(i)

    for j in bold:
        for i in l:
            cleaned_text = re.sub('\<.*?\>', '', i)
            cleaned_text = re.sub(' +', ' ', cleaned_text)
            score = fuzz.ratio(list(values[j][0].values())[0], cleaned_text)
            if score > 90:
                org = i.replace('<b>', '&lt;b&gt;').replace('</b>', '&lt;/b&gt;')
                org = re.sub('\<.*?\>', '', org)
                values[j] = [{classify(org)[0]: org}]
    return values


# --------------------------------------------------------------------------------
def alternate_nutrition_table(path, page):
    t = camelot.read_pdf(path, pages=str(page), copy_text=['v'])  # t = tabula.read_pdf(path,lattice=True,pages=1)
    tables = []
    for i in range(len(t)):
        tables.append(t[i].df.fillna("").T.reset_index().T.values.tolist())

    joined_tables = []
    for i in tables:
        for j in i:
            cell = []
            for k in j:
                if k:
                    cell.append(k)
            if len(cell) >= 2:
                joined_tables.append(cell)
    nkeys = []
    nvalues = []
    # others=[]
    for r in joined_tables:
        if len(r) >= 2:
            key_id = re.sub("[\(\[].*?[\)\]]", "", str(r[0])).replace('of which', '').strip()
            key_id = re.sub(r'[^a-zA-Z]', ' ', key_id)  # Keeping only alphabets
            temp, prob, classified = cleaning_classifiction(key_id.strip())
            second_element = str(r[1]).replace("&lt;b&gt;", '').replace("&lt;/b&gt;", '').replace("&lt;/b&gt;",
                                                                                                  '').replace('&lt;',
                                                                                                              '').replace(
                '&gt;', '').replace('<', '').replace('>', '').strip()

            try:
                # Checking for the pttern where in the list 1st element is nutrition key and 2nd element is value
                if prob[-1] > 0.65 and classified in nutri_keys and (
                        float(second_element) or float(second_element) == 0.0):
                    nkeys.append(classified)
                    sub_val = []
                    sub_val.append({'copy_notes': {'en': r[0].replace('<', '&lt;').replace('>', '&gt;').strip()}})
                    values_list = r[1:]
                    for j in range(len(values_list)):
                        row_value = values_list[j].replace('<', '&lt;').replace('>', '&gt;').replace('\r', '\n').strip()
                        if '%' in values_list[j]:
                            sub_val.append({'PDV': {'en': row_value}})
                        else:
                            sub_val.append({'Value': {'en': row_value}})
                    nvalues.append(sub_val)
            except:
                pass
                # others.append(r)
    nutri = multi_key_value(nkeys, nvalues)
    return nutri


# --------------------------------------------------------------------------------
def nutri_header(tables):
    keys=[]
    values=[]
    for i in tables:
        for r in i:
            if len(r)>=2:
                key_id=re.sub("[\(\[].*?[\)\]]", "",r[0]).replace('of which','').strip()
                key_id=re.sub(r'[^a-zA-Z]',' ',key_id).lower().strip() # Keeping only alphabets
                if 'nutrition typical values' in key_id or 'nutrition nutrition' in key_id:
                    for i in r:
                        keys.append("NUTRI_TABLE_HEADERS")
                        values.append([{classify(i)[0]:i}])
    return keys,values


# --------------------------------------------------------------------------------
def unmapped_nutrition(tables):
    unmapping = []
    for table in tables:
        for r in range(len(table)):
            if len(table[r]) > 2:
                if r == 0:
                    if 'kJ' in table[r][0] and 'g' in table[r][1] and 'g' in table[r][2]:
                        unmapping.append(table[r])

                    elif '%' in table[r][0] and '%' in table[r][1] and '%' in table[r][2]:
                        unmapping.append(table[r])
                elif r == 1:
                    if '%' in table[r][0] and '%' in table[r][1] and '%' in table[r][2]:
                        unmapping.append(table[r])
    keys = []
    values = []
    for i in unmapping:
        keys.append('UNMAPPED')
        temp = []
        for j in i:
            temp.append({classify(str(j))[0]: j})
        if len(i) == len(temp):
            values.append(temp)
    return keys, values


# --------------------------------------------------------------------------------
def nested_tables(path, page):
    tables = camelot.read_pdf(path, pages=str(page), flavor='lattice')

    keys = []
    values = []
    for table in tables:
        df = table.df.replace(r'^\s*$', np.nan, regex=True)
        df.dropna(axis=1, how='all', inplace=True)  # Dropping all rows where all values are nan
        df.dropna(axis=0, how='all', inplace=True)  # Dropping all columns where all values are nan
        df.iloc[:, 0].ffill(
            inplace=True)  # Same key might have values in multiple rows and to make it key values pair forward fill is used

        for i in range(len(df)):
            temp = list(df.iloc[i, :].dropna())
            if 'Cooking Instructions' in temp[0].replace('\n', ' '):
                # print('\n',list(temp[:]))
                # values.append(list(temp[1:]))
                r = []
                for k in list(temp[1:]):
                    # print(k)
                    r.append({classify(k)[0]: k})
                if r:
                    values.append(r)
                    keys.append('USAGE_INSTRUCTIONS')
            # Sometimes the durability might break into new page so we need more than 3 values/ 3 new lines to be considered
            elif 'Durability Codes' in temp[0].replace('\n', ' ').strip() and len(str(temp[1]).strip().split('\n')) > 3:
                # print('\n',list(temp[:]))
                # values.append(list(temp[1:]))
                r = []
                for k in list(temp[1:]):
                    for s in k.split('\n'):
                        # print(k)
                        r.append({classify(s)[0]: s})
                if r:
                    values.append(r)
                    keys.append('OTHER_INSTRUCTIONS')
    return keys, values


# --------------------------------------------------------------------------------
def aldi_new_main(path, page):
  temp_directory = tempfile.TemporaryDirectory(dir=document_location)
  input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
  path = get_input(path,input_pdf_location)
  with pdfplumber.open(path) as pdf:
    if int(page) <= len(pdf.pages):
        tables = [data_extraction(path, page)]
        keys1, values1, nkeys1, nvalues1 = key_values_rows(tables)
        keys2, values2, nkeys2, nvalues2 = main_nutrition_table(tables)
        keys3, values3 = single_content(tables)
        keys4, values4 = nutri_header(tables)
        keys5, values5 = unmapped_nutrition(tables)
        keys6, values6 = nested_tables(path, page)
        general_keys = keys1 + keys2 + keys3 + keys4 + keys5 + keys6
        general_values = values1 + values2 + values3 + values4 + values5 + values6
        general_values = bold_convertion(path, general_keys, general_values, page)
        file = multi_key_value(general_keys, general_values)
        nutrition_table1 = nutrition_transpose(path, page)
        plumb = pdfplumber.open(path)
        pdf_height = float(plumb.pages[0].height)
        if pdf_height < 1000:
            if nutrition_table1[0]:
                nutri_facts = [alternate_nutrition_table(path, page)] + nutrition_table1
            else:
                nutri_facts = [alternate_nutrition_table(path, page)]
        else:
            if nkeys1 and nvalues1 and nutrition_table1[0]:
                nutrition_keys = nkeys1 + nkeys2
                nutrition_values = nvalues1 + nvalues2
                nutrition_table2 = [multi_key_value(nutrition_keys, nutrition_values)]
                nutri_facts = nutrition_table1 + nutrition_table2

            elif nkeys1 and nvalues1:
                nutrition_keys = nkeys1 + nkeys2
                nutrition_values = nvalues1 + nvalues2
                nutri_facts = [multi_key_value(nutrition_keys, nutrition_values)]

            elif nutrition_table1[0]:
                nutrition_table2 = separate_nutrition(nkeys2, nvalues2)
                if nutrition_table2[0]:
                    nutri_facts = nutrition_table1 + nutrition_table2
                else:
                    nutri_facts = nutrition_table1
            else:
                nutri_facts = separate_nutrition(nkeys2, nvalues2)
        final_cleaned_dict = {}
        for category, value_list in file.items():
            final_cleaned_dict[category] = list(
                {frozenset(list_element.items()): list_element for list_element in value_list}.values())

        if nutri_facts[0]:
            final_cleaned_dict['NUTRITION_FACTS'] = nutri_facts

        return final_cleaned_dict
    else:
        return {}

def aldi_page_routing(pdf_file, pages):
    final_dict = {}
    for page in pages.split(","):
      page_response = aldi_new_main(pdf_file, int(page))
      final_dict[page] = page_response
    final_dict = language_correction_based_on_max_occurance(final_dict)
    return final_dict

from collections import Counter
from .utils import GoogleTranslate
def language_correction_based_on_max_occurance(page_dict,percentage_threshold=35):
    recreated_page_dict = {}
    counter = Counter()
    for page_no , value_dict in page_dict.items():
        for gs1 , values_list in value_dict.items():
            if gs1 not in ("NUTRITION_FACTS"):
                for value in values_list:
                    for lang , content in value.items():
                        counter[lang] += 1
    max_lang_count = counter.most_common(1)[0][1]
    for page_no , value_dict in page_dict.items():
        for gs1 , values_list in value_dict.items():
            re_value_list = []
            if gs1 not in ("NUTRITION_FACTS"):
                for value in values_list:
                    for lang, content in value.items():
                        if dict(counter)[lang] < float(max_lang_count)*percentage_threshold/100:
                            print(value)
                            # with GoogleTranslate(content) as output:
                            #     lang  = output['language']
                            lang = custom_language_detection(content)
                            print({lang:content})
                            re_value_list.append({lang:content})
                        else:
                            re_value_list.append(value)
                recreated_page_dict.setdefault(page_no, {})[gs1] = re_value_list
            else:
                recreated_page_dict.setdefault(page_no,{})[gs1] = values_list

    print(recreated_page_dict)
    print(counter)
    return recreated_page_dict
