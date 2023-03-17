import io
import re
import pdf2docx
import camelot
import string
import tabula
import mammoth
import pdfplumber
import joblib
import pandas as pd
import numpy as np
from langid import classify
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from laserembeddings import Laser
from pdf2docx import parse, Converter
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import warnings
import tempfile

from .excel_processing import *

warnings.filterwarnings("ignore")

# ------------------------------------------------------------------------------

# Laser Embedding
# path_to_bpe_codes = r'/Users/manirathinams/opt/anaconda3/lib/python3.9/site-packages/laserembeddings/data/93langs.fcodes'
# path_to_bpe_vocab = r'/Users/manirathinams/opt/anaconda3/lib/python3.9/site-packages/laserembeddings/data/93langs.fvocab'
# path_to_encoder = r'/Users/manirathinams/opt/anaconda3/lib/python3.9/site-packages/laserembeddings/data/bilstm.93langs.2018-12-26.pt'
# laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)
# Load classifier model for nutrition
# classifier = joblib.load(cocacola_austria_model)

# ------------------------------------------------------------------------------

header = {"market": 'OTHER_INSTRUCTIONS', "brand": 'BRAND_NAME', "flavour": 'VARIANT', "sub-brand": 'SUB_BRAND',
          "sub brand": 'SUB_BRAND', "pack type": 'OTHER_INSTRUCTIONS',
          "languages": 'OTHER_INSTRUCTIONS', "translation language(s)": 'OTHER_INSTRUCTIONS',
          "size": 'NET_CONTENT_STATEMENT', "no. units": 'SERVING_SIZE',
          "number of units": 'SERVING_SIZE', "number of servings": 'NUMBER_OF_SERVINGS_PER_PACKAGE',
          "product description": 'OTHER_INSTRUCTIONS', "ean barcode": 'OTHER_INSTRUCTIONS',
          "address": 'CONTACT_INFORMATION', "pack size": 'NET_CONTENT_STATEMENT', "functional name": 'FUNCTIONAL_NAME',
          "ingredients list": 'INGREDIENTS_DECLARATION',
          "product name": 'VARIANT', "legal denomination": 'FUNCTIONAL_NAME', "durability indicator": 'EXPIRATION_DATE',
          "storage instructions": 'STORAGE_INSTRUCTIONS',
          "marketing claims": 'MARKETING_CLAIM', "reference intakes": 'DECLARATION_CONTEXT_FOOTNOTE',
          "website": 'WEBSITE', "recycling other text": 'RECYCLE_STATEMENT',
          "additional sra requirements": 'OTHER_INSTRUCTIONS', "mandatory warnings": 'WARNING_STATEMENTS',
          "nutritional claim": 'OTHER_INSTRUCTIONS',
          "short description": 'OTHER_INSTRUCTIONS', "product claim": 'MARKETING_CLAIM',
          "other claims": 'OTHER_INSTRUCTIONS', "instruction for use": 'USAGE_INSTRUCTIONS'}


# ------------------------------------------------------------------------------
def classifier(model_location):
	return joblib.load(model_location)

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
        return document_location + input_file

def bs4_soup(file_path, pgs,docx_location):
    # PDF-(pdf2docx)-> DOCX-(mammoth)-> HTML-(bs4)->soup
    docx_file = docx_location
    cv = Converter(file_path)
    cv.convert(docx_file, pages=[pgs - 1])
    cv.close()
    html = mammoth.convert_to_html(docx_file).value
    soup = BeautifulSoup(html, "html.parser")
    return soup


# ------------------------------------------------------------------------------

def general_infor_title_table(soup):
    # extracting_all_tables using beautifulsoup
    all_tables = []
    for tables in soup.find_all('table'):
        rows = []
        for row in tables.find_all('tr'):
            cols = []
            for cell in row.find_all('td'):
                if cell.text:
                    temp = str(cell).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace("<br>",
                                                                                                                '\n').replace(
                        "<br/>", '\n')
                    cols.append(
                        (BeautifulSoup(temp, 'html.parser').text).replace('start_bold', '&lt;b&gt;').replace('end_bold',
                                                                                                             '&lt;/b&gt;').replace(
                            '\xa0', '').strip())
            if len(cols) > 0:
                rows.append(cols)
        if len(rows) > 0:
            all_tables.append(rows)
    # identifying particular title table and appending key value pair
    key = []
    val = []
    for x in range(len(all_tables)):
        for ind, value in enumerate(all_tables[x]):
            # print(value)
            if ind == 0 and 'ATLAS BBN' in value[0] and len(value) == 4:
                data = pd.DataFrame(all_tables[x])
                ky = data.iloc[:, 0::2].values.tolist()
                key = [r.lower().replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '') for row in ky for r in row if
                       r != None]
                vl = data.iloc[:, 1::2].values.tolist()
                val = [{classify(str(r))[0]: r} for row in vl for r in row if r != None]
    return key, val


# ------------------------------------------------------------------------------

def general_infor_para_extraction(soup):
    # extracting a title pragraph text using bs4 soup
    temp = [str(tag).replace('<p>', '').replace('</p>', '') for tag in soup.find_all('p')]

    # slicing the information
    a = 0
    b = 0
    for ind, row in enumerate(temp):
        # print(row)
        if 'label sheet name' in row.lower():
            a = ind
        elif 'label sheet status' in row.lower():
            b = ind
    result = temp[a:b]

    # spliting a single list of infor to key val pair
    splt = 0
    for x in range(len(result)):
        if 'ean barcode' in result[x].lower():
            splt = x
    ky = result[:splt + 1]
    key = [x.lower().replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '') for x in ky if len(x) > 2]
    vl = result[splt + 1:]
    val = [{classify(str(y))[0]: y} for y in vl]
    return key, val


# ------------------------------------------------------------------------------

def general_inform_table_extraction(file_path, pgs):
    tables = tabula.read_pdf(file_path, pages=str(pgs), lattice=True)
    keys = []
    vals = []
    col = 0
    for x in range(len(tables)):
        data = tables[x].T.reset_index().T
        for r in range(len(data)):
            for c in range(len(data.columns)):
                if (str(data.iloc[r, c]).lower().replace('\r', '') in ['romance copy document name',
                                                                       'product description', 'reference intakes',
                                                                       'website']) and (
                        'instance' in str(data.iloc[r, c + 1]).lower() or str(data.iloc[r, c + 1]).isdigit()):
                    col = c
                    if len(data.columns) == 5:
                        dfs = tables[x].iloc[:, 1::2].T.reset_index().T
                        dfs = dfs.dropna()
                        # keys.append(dfs.iloc[:,0].tolist())
                        keys = [x.lower() for x in dfs.iloc[:, 0]]
                        vals = [{classify(str(y))[0]: y} for y in dfs.iloc[:, 1]]
                    else:
                        dfs = tables[x].iloc[:, col::2].T.reset_index().T
                        keys = [x.lower() for x in dfs.iloc[:, 0]]
                        vals = [{classify(str(y))[0]: y} for y in dfs.iloc[:, 1]]
    return keys, vals


# ------------------------------------------------------------------------------

def bold_convertion(soup, keys, values):
    l = []
    for i in soup.find_all('p'):
        l.append(str(i))
    para = []
    for i in l:
        temp = i.replace('<p>', '').replace('</p>', '').split('</strong>')
        temp = [k.replace('\t1', '').strip() for k in temp if k.replace('\t1', '').strip()]
        if len(temp) > 1:
            for j in temp:
                if '<strong>' in j:
                    para.append(j + '</strong>')
                else:
                    para.append(j)
        else:
            para.append(i)
    bold = []
    matches = ['INGREDIENTS_DECLARATION', 'FUNCTIONAL_NAME', 'WARNING_STATEMENTS']
    for i in range(len(keys)):
        if any(True for m in matches if keys[i] == m):
            bold.append(i)

    for j in bold:
        for i in para:
            if '<strong>' in i:
                cleaned_text = re.sub('\<.*?\>', '', i)
                score = fuzz.ratio(list(values[j].values())[0], cleaned_text)
                if score > 90:
                    org = i.replace('<strong>', '&lt;b&gt;').replace('</strong>', '&lt;/b&gt;')
                    org = re.sub('\<.*?\>', '', org)
                    #                     print(list(values[j].values())[0],'\n',i,'\n',score)
                    values[j] = {classify(org)[0]: org}
                elif score > 20:
                    #                     print(cleaned_text,':',score)
                    pass
                else:
                    #                     print(i)
                    pass
    return values


# ------------------------------------------------------------------------------

def general_main(file_path, pgs,docx_location):  # general information main function
    soup = bs4_soup(file_path, pgs,docx_location)
    key, val = general_infor_title_table(soup)
    key1, val1 = general_infor_para_extraction(soup)
    key2, val2 = general_inform_table_extraction(file_path, pgs)
    old_keys = key + key1 + key2
    vals = val + val1 + val2

    keys = []
    for i in old_keys:
        if i in header:
            keys.append(header[i])
        else:
            keys.append('UNMAPPED')

    # vals, para=bold_convertion(file_path,keys,vals,pgs)
    vals = bold_convertion(soup, keys, vals, )
    # replacing keys with header dict values instead of classifier prediction
    gen_dict = {}
    for i in range(len(keys)):
        gen_dict.setdefault(keys[i], []).append(vals[i])
    return gen_dict


# ------------------------------------------------------------------------------

def nutrition_value_pdv_split_func(df):
    df.columns = ['Key', 'Value1', 'Value2']
    df['PDV'] = df['Value2'].apply(lambda x: ('(' + x.split('(')[1]) if '(' in x else '')
    df[df.columns[2]] = df[df.columns[2]].apply(lambda x: (x.split('(')[0]) if '(' in x else x)
    return df


# ------------------------------------------------------------------------------

def nutrition_extraction(file_path, pgs):
    tables = camelot.read_pdf(file_path, pages=str(pgs), flavor='stream')
    df = pd.DataFrame([])
    for x in range(len(tables)):
        data = tables[x].df
        for r in range(len(data)):
            for c in range(len(data.columns)):
                if 'nährwertdeklaration per' in data.iloc[r, c].lower().replace(':', '').replace('/',
                                                                                                 '') or 'brennwert' in data.iloc[r, c].lower().replace(':', ''):
                    df = tables[x].df

    try:
        # forward fill the 1st column
        df.iloc[:, 0].replace(to_replace='', method='ffill', inplace=True)

        # Adding energy in header for kcal values
        for s in range(len(df)):
            for t in range(len(df.columns)):
                if 'kcal' in str(df.iloc[s, t]):
                    df.iloc[s, t - 1] = 'Energy'
                    break

        # no of cols is 3 then nutrition_value_pdv split func will execute
        if len(df.columns) == 3:
            df = nutrition_value_pdv_split_func(df)
        else:
            df = df
    except:
        df = []
    return df


# ------------------------------------------------------------------------------

def nutrition_table(dfs):
    key = []
    val = []
    # if len(df)!=0:
    for s in range(len(dfs)):
        if dfs.iloc[s, 0] != '':
            ky_cln = (dfs.iloc[s, 0].replace(':', '').replace('/',
                                                              '')).strip().lower()  # split key based on '/' & taken 1st val
            proba = classifier(cocacola_austria_model).predict_proba(laser.embed_sentences(ky_cln, lang='en'))[0]
            proba.sort()
            content = []
            for t in range(1, len(dfs.columns)):
                if dfs.iloc[s, t] != '' and '%' in str(dfs.iloc[s, t]):
                    content.append({'PDV': {str(classify(str(dfs.iloc[s, t]))[0]): dfs.iloc[s, t]}})
                elif dfs.iloc[s, t] != '':
                    content.append({'Value': {str(classify(str(dfs.iloc[s, t]))[0]): dfs.iloc[s, t]}})
            if content:
                val.append(content)
                if proba[-1] > 0.80:
                    key.append((classifier(cocacola_austria_model).predict(laser.embed_sentences(ky_cln, lang='en')))[0])
                else:
                    key.append('UNMAPPED')

    # appending keys and vals in dictionary
    nutr_infor = {}
    for k in range(len(key)):
        if key[k] != 'UNMAPPED':
            nutr_infor.setdefault(key[k], []).extend(val[k])

    return nutr_infor


# ------------------------------------------------------------------------------

def nutrition_main(file_path, pgs):
    dfs = nutrition_extraction(file_path, pgs)
    if len(dfs) > 1:
        out = nutrition_table(dfs)
        fnl = {"NUTRITION_FACTS": out}
    else:
        fnl = {}
    return fnl


# ------------------------------------------------------------------------------

def coca_cola_austria_main(file_path, pages):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_docx_location = f'{temp_directory.name}/input_docx.docx'
    # input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    # file_path = get_input(file_path,input_pdf_location)
    page_no = [int(pg) for pg in pages.split(',')]
    all_pages = {}
    for pgs in page_no:
        out1 = general_main(file_path, pgs,input_docx_location)
        out2 = nutrition_main(file_path, pgs)
        output = {**out1, **out2}
        all_pages[str(pgs)] = output
    return all_pages
# ------------------------------------------------------------------------------
