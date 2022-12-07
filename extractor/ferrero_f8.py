import pandas as pd
import numpy as np
from langid import classify
import time
from laserembeddings import Laser
import warnings

warnings.filterwarnings("ignore")
import joblib
from bs4 import BeautifulSoup
import mammoth
import re
from pdfminer.high_level import extract_text
from pdf2docx import Converter
from pdf2docx import parse
import pdfplumber
from docx import Document
from sklearn.neural_network import MLPClassifier


from pdfminer.high_level import extract_text_to_fp
import io
import tempfile
import sys
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.layout import LAParams
import io
from fuzzywuzzy import fuzz, process
import smbclient

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

temp_directory = tempfile.TemporaryDirectory(dir=document_location)
input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
converted_docx = f'{temp_directory.name}/converted.docx'

laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)

# input_dataset = r"/Users/sakthivel/Documents/SGK/Ferrero/New Format/Dataset/ferrero_new_format_dataset.xlsx"
#
# # df = pd.read_excel(input_dataset,sheet_name='main')
# dataframe = pd.read_excel(input_dataset, sheet_name='Sheet1', engine='openpyxl')
# x_train_laser = laser.embed_sentences(dataframe['text'], lang='en')
# classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750, random_state=0,
#                            shuffle=True)
# classifier.fit(x_train_laser, dataframe['category'])

model_location = ferrero_f8_model_location
classifier = joblib.load(model_location)

# nutri_input_dataset = r"/Users/sakthivel/Documents/SGK/Nutrition Dataset/Master Nutrition Dataset.xlsx"
#
# # df = pd.read_excel(input_dataset,sheet_name='main')
# nutri_dataframe = pd.read_excel(nutri_input_dataset, sheet_name='Sheet1', engine='openpyxl')
# nutri_x_train_laser = laser.embed_sentences(nutri_dataframe['text'], lang='en')
# nutri_classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
#                                  random_state=0,
#                                  shuffle=True)
# nutri_classifier.fit(nutri_x_train_laser, nutri_dataframe['category'])

master_nutri_model_location = ferrero_f8_nutrition_model_location
nutri_classifier = joblib.load(master_nutri_model_location)

keys = ['Calories',
        'Proteins',
        'Fats',
        'Saturated Fats',
        'Trans Fats',
        'Carbohydrates',
        'Sugars',
        'Fibers',
        'Sodium']


key_list = ['Sodium', 'Carbohydrates', 'Sugars', 'Fat', 'Trans Fat', 'Cholesterol', 'Protein', 'Saturated Fat',
            'trans fat', 'saturated fat', '나트륨', '탄수화물', '당류', '지방', '트랜스지방', '포화지방', '콜레스테롤', '단백질']


def get_input(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location + input_pdf


def pdf_to_docx(file, pages):
    try:
        pdf_file = file
        # docx_file = path + 'nestle_file_p1.docx'

        # convert pdf to docx
        parse(pdf_file, converted_docx, pages=[pages - 1])

        return converted_docx
    except:
        pass

def docx_content(docx):
    html = mammoth.convert_to_html(docx).value
    soup = BeautifulSoup(html, "html.parser")
    table_content_list_all = []
    for tables in soup.find_all('table'):
        for row in tables.find_all('tr'):
            column_list = []
            for column in row.find_all('td'):
                #             column_list.append(str(column).replace('<td>','').replace('</td>','').replace('</p>','').replace('<p>','').replace('<td colspan="2">','').strip())
                raw_html = str(column).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace(
                    '</p>', '\n').replace('<br/>', '\n').strip()
                cleantext = BeautifulSoup(raw_html, "html.parser").text
                column_list.append(
                    cleantext.replace('start_bold', '<b>').replace('end_bold', '</b>').replace('\t', '\n').replace('<',
                                                                                                                   '&lt;').replace(
                        '>', '&gt;'))
            if column_list not in table_content_list_all:
                table_content_list_all.append(column_list)

    return table_content_list_all


def ferrero_gen_calssifier(table_content_list_all):
    final_content_list = []
    #     serving_list =[]
    #     ingre_dic={}
    for k in range(0, len(table_content_list_all)):
        if table_content_list_all[k]:
            split = table_content_list_all[k][0].split('\n')
            classified_output = classifier.predict(laser.embed_sentences(
                split[0].replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', ' ').replace('(Lettering size: min 2mm)','').lower(), lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(
                split[0].replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', ' ').replace('(Lettering size: min 2mm)','').lower(), lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            if classified_output not in ['NUTRITIONAL_INFORMATION', 'None']:

                contents = [table_content_list_all[k], classified_output.strip()]
                final_content_list.append(contents)
            elif 'net weight' in table_content_list_all[k][0].lower():
                contents = [table_content_list_all[k], 'NET_CONTENT_STATEMENT']
                final_content_list.append(contents)
            elif 'product name' in table_content_list_all[k][0].lower():
                contents = [table_content_list_all[k], 'PRODUCT_NAME']
                final_content_list.append(contents)
            elif 'commercialised in' in table_content_list_all[k][0].lower():
                contents = [table_content_list_all[k], 'PRODUCT_INFORMATION']
                print(contents)
                final_content_list.append(contents)

    return final_content_list

def gen_dic(final_content_list):
    gen_dic = {}
    unwanted = ['INGREDIENT LIST', 'NAME AND ADDRESS', 'BRAND NAME']
    for p in range(0, len(final_content_list)):
        for d in range(1, len(final_content_list[p][0])):
            if all(s not in final_content_list[p][0][d] for s in unwanted):
                if final_content_list[p][1] not in ['PRODUCT_INFORMATION']:
                #             if 'INGREDIENT LIST' not in final_content_list[p][0][d] and 'NAME AND ADDRESS' not in final_content_list[p][0][d]:
                    if final_content_list[p][0][d].strip() and len(final_content_list[p][0][d]) > 3:
                        if all(s not in final_content_list[p][0][d] for s in ['T9','T15','T24']):
                            lang = classify(final_content_list[p][0][d])[0]
                            if final_content_list[p][1] in gen_dic:
                                gen_dic[final_content_list[p][1]].append({lang: final_content_list[p][0][d]})
                            else:
                                gen_dic[final_content_list[p][1]] = [{lang: final_content_list[p][0][d]}]
        ## Newly added script for product info, as it returns multiple items in list.
        if final_content_list[p][1] in ['PRODUCT_INFORMATION']:
            if 'foglio' not in final_content_list[p][0][1].lower():
                if final_content_list[p][0][1].strip() and len(final_content_list[p][0][1]) > 3:
                    lang = classify(final_content_list[p][0][1])[0]
                    if final_content_list[p][1] in gen_dic:
                        gen_dic[final_content_list[p][1]].append({lang: final_content_list[p][0][1]})
                    else:
                        gen_dic[final_content_list[p][1]] = [{lang: final_content_list[p][0][1]}]
            else:
                if final_content_list[p][0][2]:
                    lang = classify(final_content_list[p][0][2])[0]
                    if final_content_list[p][1] in gen_dic:
                        gen_dic[final_content_list[p][1]].append({lang: final_content_list[p][0][2]})
                    else:
                        gen_dic[final_content_list[p][1]] = [{lang: final_content_list[p][0][2]}]
    return gen_dic

def general_dict(gen_dict):
    general_classifier_dic = {}
    for key, value in gen_dict.items():
        if key in ['ALLERGEN_STATEMENT', 'INGREDIENTS_DECLARATION']:
            for content in value:
                for lang, item in content.items():
                    #                         print(item)
                    classified_output = classifier.predict(laser.embed_sentences(
                        item.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', ' '), lang='en'))
                    probability1 = classifier.predict_proba(laser.embed_sentences(
                        item.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', ' '), lang='en'))
                    probability1.sort()
                    prob1 = probability1[0][-1]
                    if prob1 > 0.70:
                        classified_output = classified_output[0]
                    else:
                        classified_output = 'None'
                    if classified_output not in ['None']:
                        if classified_output in general_classifier_dic:
                            general_classifier_dic[classified_output].append({lang: item})
                        else:
                            general_classifier_dic[classified_output] = [{lang: item}]
                    elif classified_output in ['None']:
                        if key in general_classifier_dic:
                            general_classifier_dic[key].append({lang: item})
                        else:
                            general_classifier_dic[key] = [{lang: item}]
        else:
            if key in general_classifier_dic:
                general_classifier_dic[key].append(value)
            else:
                general_classifier_dic[key] = value

    return general_classifier_dic


def final_gen_dic(pdf_file, page):
    input_docx = pdf_to_docx(pdf_file, page)
    #     print(input_docx)
    if input_docx != None:
        text = docx_content(input_docx)
        out = ferrero_gen_calssifier(text)
        gen_dict = gen_dic(out)
        classified_dict = general_dict(gen_dict)
        return classified_dict
    else:
        pass


def pdf_content(pdf_file, page):
    content_list_1 = []
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[page - 1]
        text = page.extract_text().replace('<', '&lt;').replace('>', '&gt;').split('\n')
        content_list_1.append(text)
    return content_list_1


def nutri_content(content_list_1, keys):
    nutri_list = []
    serv_dict = {}
    for i in range(0, len(content_list_1[0])):
        for k in keys:
            if k in content_list_1[0][i].strip():
                if content_list_1[0][i] not in nutri_list:
                    nutri_list.append(content_list_1[0][i])
        if 'per serving' in content_list_1[0][i].lower():
            output = re.split('Per serving|每一份量', content_list_1[0][i])
            for cnt in output:
                if cnt.strip():
                    lang = classify(cnt)[0]
                    if 'Per_Serving' in serv_dict:
                        serv_dict['Per_Serving'].append({lang: cnt.strip()})
                    else:
                        serv_dict['Per_Serving'] = [{lang: cnt.strip()}]

    return nutri_list, serv_dict

def new_nutri_content(nutri_list):
    new_nutri_list = []
    for k in nutri_list:
        #     print(k)
        regex = re.findall(r'([A-Za-z]\w+)', k.replace('Kcal', '').replace('mg', ''))
        regex = ' '.join(regex)
        #         print(regex)
        if 'per' not in k.lower():
            classified_output = nutri_classifier.predict(laser.embed_sentences(
                regex.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', '').lower(), lang='en'))
            probability1 = nutri_classifier.predict_proba(laser.embed_sentences(
                regex.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', '').lower(), lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.80:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            if classified_output not in ['None', 'Nutrition information']:
                content = [k, classified_output]
                new_nutri_list.append(content)

    return new_nutri_list


def split_list(alist, wanted_parts):
    length = len(alist)
    return [alist[i * length // wanted_parts: (i + 1) * length // wanted_parts]
            for i in range(wanted_parts)]


def regx_final_list(new_nutri_list):
    regex_new_list = []
    for j in new_nutri_list:
        reg1 = re.findall(r'((&lt;)?\s?(\d+)(\.\d+)?\s?(mg|kj|g|kcal|Kcal|%|mcg|大卡|公克|毫克|克|千卡))',
                          str(j).replace(' ', ''))
        regex_new_list.append(reg1)

    new_list1 = []
    new_list2 = []
    for i in regex_new_list:
        out = split_list(i, wanted_parts=2)
        new_list1.append(out[0])
        new_list2.append(out[1])
    return new_list1, new_list2

def nutri_dic(regex_new_list_, nutri_keys_para):
    nutri_arabic_dic = {}
    if regex_new_list_:
        if len(regex_new_list_) == len(nutri_keys_para):
            for l in range(0, len(regex_new_list_)):
                for m in range(0, len(regex_new_list_[l])):
                    if '%' in str(regex_new_list_[l][m][0]):
                        if nutri_keys_para[l][1] in nutri_arabic_dic:
                            nutri_arabic_dic[nutri_keys_para[l][1]].append(
                                {'PDV': {'en': str(regex_new_list_[l][m][0].strip())}})
                        else:
                            nutri_arabic_dic[nutri_keys_para[l][1]] = [
                                {'PDV': {'en': str(regex_new_list_[l][m][0].strip())}}]
                    else:
                        if nutri_keys_para[l][1] in nutri_arabic_dic:
                            nutri_arabic_dic[nutri_keys_para[l][1]].append(
                                {'Value': {'en': str(regex_new_list_[l][m][0].strip())}})
                        else:
                            nutri_arabic_dic[nutri_keys_para[l][1]] = [
                                {'Value': {'en': str(regex_new_list_[l][m][0].strip())}}]

    return nutri_arabic_dic

def nutrition_format1(pdf_file, page):
    content = pdf_content(pdf_file, page)
    flag = 0
    for k in content[0]:
        #         print(k)
        if 'nutrition facts' in k.lower() and "營養標示" in k:
            print('nutri format 1')
            flag = 1
            break
    if flag == 1:
        final_nutri_dict = {}
        final_nutri_list = []
        nutri_list, serv_dict = nutri_content(content, keys)
        new_nutri_list = new_nutri_content(nutri_list)
        new_list1, new_list2 = regx_final_list(new_nutri_list)
        final_nutri_list.append(nutri_dic(new_list1, new_nutri_list))
        final_nutri_list.append(nutri_dic(new_list2, new_nutri_list))
        final_nutri_dict['NUTRITION_FACTS'] = final_nutri_list
        return {**final_nutri_dict, **serv_dict}

def nurtri_split_list_f2(content_list_1):
    new_cnt_list = []
    for j in range(0, len(content_list_1[0])):
        if 'Nutrition Label 營養標示' in content_list_1[0][j]:
            #         if content_list_1[0][j] not in new_cnt_list:
            new_cnt_list.append(content_list_1[0][j:])

    size = len(new_cnt_list[0])
    idx_list = [idx + 1 for idx, val in
                enumerate(new_cnt_list[0]) if "Nutrition Label 營養標示" in val]

    res = [new_cnt_list[0][i: j] for i, j in
           zip([0] + idx_list, idx_list +
               ([size] if idx_list[-1] != size else []))]
    return res

def nutrition_format2(pdf_file, page):
    content = pdf_content(pdf_file, page)
    flag = 0
    for k in content[0]:
        if 'Nutrition Label 營養標示' in k:
            print('nutri format 2')
            flag = 2
            break
    if flag == 2:
        res = nurtri_split_list_f2(content)

        final_nutri_list = []
        final_nutri_dict = {}
        for l in range(0, len(res)):
            new_nutri_list = new_nutri_content(res[l])
            regex_new_list = []
            l1, l2 = regx_final_list(new_nutri_list)
            out1 = nutri_dic(l1, new_nutri_list)
            if out1:
                final_nutri_list.append(out1)
            out2 = nutri_dic(l2, new_nutri_list)
            if out2:
                final_nutri_list.append(out2)
        final_nutri_dict['NUTRITION_FACTS'] = final_nutri_list

        return final_nutri_dict


def nurtri_split_list_f3(content_list_1):
    new_cnt_list = []
    for j in range(0, len(content_list_1[0])):
        if 'nutritional' in content_list_1[0][j].lower() and 'information' in content_list_1[0][j + 1].lower():
            #         if content_list_1[0][j] not in new_cnt_list:
            new_cnt_list.append(content_list_1[0][j:])
    size = len(new_cnt_list[0])
    idx_list = [idx + 1 for idx, val in
                enumerate(new_cnt_list[0]) if "nutritional" in val.lower() or "영양정보" in val]

    res = [new_cnt_list[0][i: j] for i, j in
           zip([0] + idx_list, idx_list +
               ([size] if idx_list[-1] != size else []))]

    return res

def regex_nutrition(new_list10):
    new_regx_dic = {}
    for i in range(0, len(new_list10)):
        reg1 = re.findall(r'((less than)?(&lt;)?\s?(\d+)(\.\d+)?\s?(mg|kj|g|kcal|Kcal|%|mcg|大卡|公克|毫克|克|千卡)\s?(미만|))',
                          str(new_list10[i][0]))
        for l in range(0, len(reg1)):
            if '%' in reg1[l][0]:
                if new_list10[i][1] in new_regx_dic:
                    new_regx_dic[new_list10[i][1]].append({'PDV': {'en': reg1[l][0].strip()}})
                else:
                    new_regx_dic[new_list10[i][1]] = [{'PDV': {'en': reg1[l][0].strip()}}]
            else:
                if new_list10[i][1] in new_regx_dic:
                    new_regx_dic[new_list10[i][1]].append({'Value': {'en': reg1[l][0].strip()}})
                else:
                    new_regx_dic[new_list10[i][1]] = [{'Value': {'en': reg1[l][0].strip()}}]

    return new_regx_dic

def nutrition(dictionary):
    nutri_dic = {}
    for keys, value in dictionary.items():

        split_cnt = re.split('/|,', keys)
        classified_output_1 = nutri_classifier.predict(laser.embed_sentences(
            split_cnt[0].replace('\xa0', '').replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>',
                                                                                                                 ''),
            lang='en'))
        probability_1 = nutri_classifier.predict_proba(laser.embed_sentences(
            split_cnt[0].replace('\xa0', '').replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>',
                                                                                                                 ''),
            lang='en'))
        probability_1.sort()
        prob_1 = probability_1[0][-1]
        if prob_1 > 0.65:
            classified_output_key = classified_output_1[0]
        else:
            classified_output_key = 'None'

        if classified_output_key != 'None':

            if classified_output_key in nutri_dic:

                nutri_dic[classified_output_key].append(value)
            else:
                nutri_dic[classified_output_key] = value

        else:
            if 'calcium' in keys.lower():

                if 'Calcium' in nutri_dic:
                    nutri_dic['Calcium'].append(value)
                else:
                    nutri_dic['Calcium'] = value
            else:
                if keys in nutri_dic:

                    nutri_dic[keys].append(value)
                else:
                    nutri_dic[keys] = value

    return nutri_dic

def nutrition_format3(pdf_file, page):
    content = pdf_content(pdf_file, page)
    flag = 0
    for j in range(0, len(content[0])):
        if 'nutritional' in content[0][j].lower() and 'information' in content[0][j + 1].lower():
            print('nutri format 3')
            flag = 3
            break

    if flag == 3:
        res = nurtri_split_list_f3(content)

        final_nutri_list = []
        final_nutri_dict = {}
        for r in range(0, len(res)):
            new_list10 = []
            new_list11 = []
            for a in res[r]:
                for k in key_list:
                    replace = a.replace('Trans Fat', 'trans fat').replace('Saturated Fat', 'saturated fat').replace(
                        '트랜스지방 ', 'trans fat').replace('포화지방', 'saturated fat')
                    if k in replace:
                        split = replace.split(k)
                        new_list10.append([split[1], k])
                        if len(split) == 3:
                            new_list11.append([split[2], k])
            if new_list10:
                dic = regex_nutrition(new_list10)
                final_nutri_list.append(nutrition(dic))
            if new_list11:
                dic_1 = regex_nutrition(new_list11)
                final_nutri_list.append(nutrition(dic_1))
        final_nutri_dict['NUTRITION_FACTS'] = final_nutri_list

        return final_nutri_dict


def NUTRITION(nutrition_lst):
    Nut_lst_3 = []

    for j in nutrition_lst:
        val_1 = []
        try:
            string_1 = re.findall(r'[A-Za-z\u4e00-\u9fff\s]+', j)[0].strip()
            val_1.append(string_1)
            snd = [i[0].strip() for i in re.findall(r'(<?\s?(\d+)(\.\d+)?\s?(mg|kJ|g|%|mcg|千焦|克|毫克|微克))', j)]
            val_1.extend(snd)
            Nut_lst_3.append(val_1)
        except:
            continue
    return Nut_lst_3

def process_pdf_file(input_file, page_no):
    with pdfplumber.open(input_file) as pdf:
        nutri_list = []
        content_lst = []
        pge_new = page_no - 1
        page = pdf.pages
        text = page[pge_new].extract_text()
        if 'nutrition information' in text.lower():
            each_string = text.split("\n")
            stored_list = NUTRITION(each_string)
            for each_list in stored_list:
                each_list = list(filter(lambda x: x != "", each_list))
                if each_list:
                    Xtest_laser = laser.embed_sentences(each_list[0], lang='en')
                    #                     model_op=mlp_model.predict(Xtest_laser)
                    model_op = nutri_classifier.predict(Xtest_laser)
                    classified_output = model_op[0]
                    #
                    #                     item_prob=mlp_model.predict_proba(Xtest_laser)
                    item_prob = nutri_classifier.predict_proba(Xtest_laser)
                    item_prob[0].sort()
                    prob = item_prob[0][-1]
                    if prob >= 0.96:
                        content = [each_list, classified_output]
                        content_lst.append(content)
    return content_lst


def return_procesed_list(content_lst_of_lst):
    English_list = []
    Chinese_list = []
    for i in range(0, len(content_lst_of_lst)):
        if content_lst_of_lst[i][1] not in [j[1] for j in English_list]:
            English_list.append(content_lst_of_lst[i])
        else:
            Chinese_list.append(content_lst_of_lst[i])

    return English_list, Chinese_list

def Language_Json_format(eng_chn_lst):
    nutri_dic = {}
    for w in range(0, len(eng_chn_lst)):
        for m in range(1, len(eng_chn_lst[w][0])):
            if eng_chn_lst[w][0][m] != '':
                if eng_chn_lst[w][1].strip() in nutri_dic:
                    if '%' not in eng_chn_lst[w][0][m]:
                        nutri_dic[eng_chn_lst[w][1].strip()].append({'Value': {
                            'en': eng_chn_lst[w][0][m].strip()}})
                    else:
                        nutri_dic[eng_chn_lst[w][1].strip()].append({'PDV': {
                            'en': eng_chn_lst[w][0][m].strip()}})
                else:
                    if '%' not in eng_chn_lst[w][0][m]:
                        nutri_dic[eng_chn_lst[w][1].strip()] = [{'Value': {
                            'en': eng_chn_lst[w][0][m].strip()}}]
                    else:
                        nutri_dic[eng_chn_lst[w][1].strip()] = [{'PDV': {
                            'en': eng_chn_lst[w][0][m].strip()}}]
    return nutri_dic

def nutrition_format4(file_input, page_nos):
    content = pdf_content(file_input, page_nos)
    flag = 0
    for j in range(0, len(content[0])):
        if 'nutrition information' in content[0][j].lower():
            print('nutri format 4')
            flag = 4
            break
    if flag == 4:
        page_no = page_nos
        content_lst_of_lst = process_pdf_file(file_input, int(page_no))
        English_list, Chinese_list = return_procesed_list(content_lst_of_lst)
        Nutri_dic = {}
        Json_format_chinese = Language_Json_format(Chinese_list)
        Nutri_dic['NUTRITION_FACTS'] = [Json_format_chinese]
        Json_format_eng = Language_Json_format(English_list)
        Nutri_dic['NUTRITION_FACTS'].extend([Json_format_eng])
        #         page_dict[page_no]=Nutri_dic
        return Nutri_dic


def process_pdf(input_file, page_no):
    both_lang_lst = []
    eng_lst = []
    thai_lst = []
    with pdfplumber.open(input_file) as pdf:
        #     page = pdf.pages
        nutri_list = []
        content_lst = []
        page = pdf.pages

        text = page[int(page_no) - 1].extract_text()

        if 'nutrition facts' in text.lower():
            splitted_text = text.split('\n')
            each_string = text.split("\n")
            #         print(each_string)
            for i in each_string:
                try:

                    thai = re.findall(r"[\u0E00-\u0E7F]+.*", i)[0].strip()
                    thai_lst.append(thai.strip())
                    eng = re.sub(r"[\u0E00-\u0E7F]+.*", "", i)
                    eng_lst.append(eng.strip())


                except:
                    #         print("No match found")
                    continue
        else:
            splitted_text = []
    both_lang_lst.append(eng_lst)
    both_lang_lst.append(thai_lst)
    return splitted_text, thai_lst, eng_lst

def Only_inside_Nutrition(lang_lst):
    Nutrition_lst_1=[]
    other_values=[]
    for j in lang_lst:
        val_1=[]
        try:
            x1 = re.findall(r"(.*?)((นอ้ยกวา่|less than)?\s+?(\d{1,4}\,?\d{0,4}\s?(g|mg|kj|kcal|ก|มก)))\.?\s?(\d{1,4}%)?",j.lower())[0]
            nutrition,value1,pdv=x1[0],x1[1],x1[5]
            value1=" ".join(value1.split())
            assigned_structured_lst=[nutrition.strip(),value1.strip(),pdv.strip()]
            assigned_structured_lst=list(filter(None, assigned_structured_lst))
            Nutrition_lst_1.append(assigned_structured_lst)
        except:
            other_values.append(j)

    return Nutrition_lst_1,other_values


def Nutrition_prediction(Nutrition):
    full_Nutrition_lst=[j for j in [list(filter(None, i)) for i in Nutrition ] if j!=[]]
    predicted_content=[]
    for k in range(0,len(full_Nutrition_lst)):
    #     print(full_Nutrition_lst[k][0])
        Xtest_laser = laser.embed_sentences(full_Nutrition_lst[k][0],lang='en')
#         model_op=mlp_model.predict(Xtest_laser)
        model_op=nutri_classifier.predict(Xtest_laser)
        classified_output=model_op[0]
    #
#         item_prob=mlp_model.predict_proba(Xtest_laser)
        item_prob=nutri_classifier.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob=item_prob[0][-1]
        if prob>=0.95:
            predicted_content.append([full_Nutrition_lst[k],classified_output])
    return predicted_content


def matched_ele_lst_of_lst(Nutrition,splitted_text):
    matched_ele_lst=[]

    for n in range(0,len(Nutrition)):
        matching = [s for s in splitted_text if Nutrition[n][0] in s]
        matched_ele_lst.append([matching,Nutrition[n]])

    return matched_ele_lst

def Thai_predict_Nutri(matched_ele_lst):
    Thai_pred_Nutri_lst=[]
    for i in range(0,len(matched_ele_lst)):
        x1 = re.findall(r"(.*?)((นอ้ยกวา่|less than)?\s+?(\d{1,4}\,?\d{0,4}\s?(g|mg|kj|kcal|ก|มก)))\.?\s?(\d{1,4}%)?",matched_ele_lst[i][0][0].lower())[0]
        Xtest_laser = laser.embed_sentences(x1[0],lang='en')
#         model_op=mlp_model.predict(Xtest_laser)
        model_op=nutri_classifier.predict(Xtest_laser)
        classified_output=model_op[0]
#         item_prob=mlp_model.predict_proba(Xtest_laser)
        item_prob=nutri_classifier.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob=item_prob[0][-1]
        if prob>=0.95:
            Thai_pred_Nutri_lst.append([matched_ele_lst[i][1],classified_output])

    return Thai_pred_Nutri_lst

def VITAMIN(other_values):
    vitamin_value=[]

    for each_vitamin in other_values:
        try:
            y = re.findall(r'((.*?)((นอ้ยกวา่|less than)?\s+(\d{1,4}%)))?\s?(.*?)?((นอ้ยกวา่|less than)?\s+(\d{1,4}%))',each_vitamin)[0]
            vitamin_1,pdv_1,vitamin_2,pdv_2=y[1],y[2],y[5],y[6]
            pdv_1=" ".join(pdv_1.split())
            pdv_2=" ".join(pdv_2.split())
            vitamin_value.append([vitamin_1.strip(),pdv_1.strip()])
            vitamin_value.append([vitamin_2.strip(),pdv_2.strip()])

        except:
            continue
    vitamin_value=[j for j in [list(filter(None, i)) for i in vitamin_value] if j!=[]]

    return vitamin_value

def Thai_comparing_predict_lst(Eng_vitamin_value,Thai_vitamin_value):
    Thai_vitamin_lst=[]
    for k in range(0,len(Eng_vitamin_value)):
        #     print(full_Nutrition_lst[k][0])
        Xtest_laser = laser.embed_sentences(Eng_vitamin_value[k][0],lang='en')
#         model_op=mlp_model.predict(Xtest_laser)
        model_op=nutri_classifier.predict(Xtest_laser)
        classified_output=model_op[0]
    #
#         item_prob=mlp_model.predict_proba(Xtest_laser)
        item_prob=nutri_classifier.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob=item_prob[0][-1]
        Thai_vitamin_lst.append([Thai_vitamin_value[k],classified_output])
    return Thai_vitamin_lst

def ENERGY_SERVING_PROCESSING_LST(splitted_text):
    Energy=[]
    Serving=[]
    for sss in splitted_text:
    #     print(sss)
        sd = re.sub(r"[a-zA-Z]+\s+[a-zA-Z]+[0-9]+\s+?\([^)]*\)\s?([a-zA-Z]+)?(\.|\.\s+|\s+)([0-9]+\.[0-9]+|[0-9]+)", "", sss)

        string_6 = re.findall(r'[A-Za-z\u0E00-\u0E7F\s]+',sd)[0].strip()
    #     print(string_6)
        Xtest_laser = laser.embed_sentences(string_6,lang='en')
#         model_op=mlp_model.predict(Xtest_laser)
        model_op=nutri_classifier.predict(Xtest_laser)
        classified_output=model_op[0]
    #
#         item_prob=mlp_model.predict_proba(Xtest_laser)
        item_prob = nutri_classifier.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob=item_prob[0][-1]

        if prob>=0.95:
            if classified_output=='Energy':
                Energy.append([sd,classified_output])
        Xtest_laser1 = laser.embed_sentences(string_6,lang='en')
#         model_op1=mlp_model1.predict(Xtest_laser1)
        model_op1=classifier.predict(Xtest_laser1)
        classified_output1=model_op1[0]
    #
#         item_prob1=mlp_model1.predict_proba(Xtest_laser1)
        item_prob1=classifier.predict_proba(Xtest_laser1)
        item_prob1[0].sort()
        prob1=item_prob1[0][-1]
#         print({string_6+"_"+str(prob1):classified_output1})
        if prob1>=0.95:
            if classified_output1 in ['SERVING_SIZE','SERVINGS_PER_KEYWORD']:
                Serving.append([sd,classified_output1])
    #Energy
#     print(Serving)
    return Energy,Serving


def SPLITING_BOTH_LANG_ENERGY_SERVING(energy_and_serving):
    thai_lst_1=[]
    eng_lst_1=[]
    for ser in range(0,len(energy_and_serving)):
    #     print(energy_serving[ser][0])
        try:

            thai_ser = re.findall(r"[\u0E00-\u0E7F]+.*",energy_and_serving[ser][0])[0].strip()
            thai_lst_1.append([thai_ser.strip(),energy_and_serving[ser][1]])
            eng_ser = re.sub(r"[\u0E00-\u0E7F]+.*", "", energy_and_serving[ser][0])
            eng_lst_1.append([eng_ser.strip(),energy_and_serving[ser][1]])


        except:
            continue
    # print(thai_ser_lst)
#     print(eng_ser_lst)
    return thai_lst_1,eng_lst_1

def ENERGY_PREDICT_LIST(Energy):
    energy_lst=[]
    for e in range(0,len(Energy)):
        if ':' in Energy[e][0]:
            Energy[e][0]=Energy[e][0].split(':')
            energy_lst.append([Energy[e][0],Energy[e][1]])
        else:
            try:
                d=re.findall(r'[0-9].*',Energy[e][0])[0]
                Energy[e][0] = Energy[e][0].replace(d,', '+d).split(',')
                energy_lst.append([Energy[e][0],Energy[e][1]])
            except:
                continue
    return energy_lst

def SERVING_PREDICT_LIST(serving):
    serving_lst=[]
    for serve in range(0,len(serving)):
    #     print(serving[serve][1])

        if ':' in serving[serve][0]:

            serving[serve][0]=serving[serve][0].split(':')
    #         print(serving[serve][1])
            serving_lst.append([serving[serve][0],serving[serve][1]])

    return serving_lst

def SERVING_DICTIONARY(Serving_lst_of_lst):
    serving_dic={}
    for s in range(0,len(Serving_lst_of_lst)):
    #     print(serving_lst[s][1])
        for j in range(1, len(Serving_lst_of_lst[s][0])):
            if Serving_lst_of_lst[s][0][j]!='':
                if Serving_lst_of_lst[s][1] in serving_dic:
                     serving_dic[Serving_lst_of_lst[s][1]].append({classify(Serving_lst_of_lst[s][0][j])[0]:str(Serving_lst_of_lst[s][0][j].strip())})
                else:
                    serving_dic[Serving_lst_of_lst[s][1]] = [{classify(Serving_lst_of_lst[s][0][j])[0]:str(Serving_lst_of_lst[s][0][j].strip())}]
    return serving_dic


def eng_lst_processng_functions(eng_lst, splitted_text):
    Nutrition, other_values = Only_inside_Nutrition(eng_lst)
    Nutri_predict = Nutrition_prediction(Nutrition)
    # VITAMIN
    Eng_vitamin_value = VITAMIN(other_values)
    Eng_vitamin_predict = Nutrition_prediction(Eng_vitamin_value)
    # Common ENERGY & SERVING
    Energy_lst, Serving_lst = ENERGY_SERVING_PROCESSING_LST(splitted_text)
    # Processing ENERGY
    Thai_energy_lst, Eng_energy_lst = SPLITING_BOTH_LANG_ENERGY_SERVING(Energy_lst)
    Eng_Energy_lst_of_lst = ENERGY_PREDICT_LIST(Eng_energy_lst)
    # Processing SERVING
    Thai_serving_lst, Eng_serving_lst = SPLITING_BOTH_LANG_ENERGY_SERVING(Serving_lst)
    ENG_Serving_lst_of_lst = SERVING_PREDICT_LIST(Eng_serving_lst)
    # JSON FOR SERVING
    ENG_Serving_dict = SERVING_DICTIONARY(ENG_Serving_lst_of_lst)
    # FINAL JSON FORMING FOR NUTRI
    final_nutri = Language_Json_format(Nutri_predict)
    ENG_final_vitamin = Language_Json_format(Eng_vitamin_predict)
    ENG_final_energy = Language_Json_format(Eng_Energy_lst_of_lst)
    #     eng_vit={**ENG_final_energy,**ENG_final_vitamin}
    ENG_Final_nutrition = {**ENG_final_energy, **final_nutri, **ENG_final_vitamin}

    return ENG_Serving_dict, ENG_Final_nutrition, Eng_vitamin_value


def thai_lst_processng_functions(thai_lst, splitted_text, Eng_vitamin_value):
    Nutrition, other_values = Only_inside_Nutrition(thai_lst)
    # NUTRITION
    matched_ele_lst = matched_ele_lst_of_lst(Nutrition, splitted_text)
    Thai_pred_Nutri_lst = Thai_predict_Nutri(matched_ele_lst)
    # ENERGY
    Energy_lst, Serving_lst = ENERGY_SERVING_PROCESSING_LST(splitted_text)
    Thai_energy_lst, Eng_energy_lst = SPLITING_BOTH_LANG_ENERGY_SERVING(Energy_lst)
    Thai_Energy_lst_of_lst = ENERGY_PREDICT_LIST(Thai_energy_lst)
    # HANDLING VITAMIN
    Thai_vitamin_value = VITAMIN(other_values)
    Thai_vitamin_lst = Thai_comparing_predict_lst(Eng_vitamin_value, Thai_vitamin_value)
    # SERVING
    Thai_serving_lst, Eng_serving_lst = SPLITING_BOTH_LANG_ENERGY_SERVING(Serving_lst)
    THAI_Serving_lst_of_lst = SERVING_PREDICT_LIST(Thai_serving_lst)
    THAI_Serving_dict = SERVING_DICTIONARY(THAI_Serving_lst_of_lst)
    # FINAL JSON FORMAT
    Thai_final_nutri = Language_Json_format(Thai_pred_Nutri_lst)
    Thai_final_vitamin = Language_Json_format(Thai_vitamin_lst)
    THAI_final_energy = Language_Json_format(Thai_Energy_lst_of_lst)

    THAI_Final_nutrition = {**THAI_final_energy, **Thai_final_nutri, **Thai_final_vitamin}
    return THAI_Serving_dict, THAI_Final_nutrition

def nutrition_format5(input_1,page_no) :
    content = pdf_content(input_1,page_no)
    flag=0
    for j in range(0,len(content[0])):
        if 'nutrition facts' in content[0][j].lower():
            print('nutri format 5')
            flag = 5
            break
    if flag == 5:
        print("*******")
        print('nutri format 5')
        print("*******")
        splitted_text,thai_lst,eng_lst = process_pdf(input_1,page_no)
        Nutri_dicionary={}
        Serving_dict = {}
        result={}
        ENG_Serving_dict,ENG_Final_nutrition,Eng_vitamin_value= eng_lst_processng_functions(eng_lst,splitted_text)
        THAI_Serving_dict,THAI_Final_nutrition=thai_lst_processng_functions(thai_lst,splitted_text,Eng_vitamin_value)
#         print(ENG_Final_nutrition)
#         print(THAI_Final_nutrition)
        if len(ENG_Final_nutrition)!=0 and len(THAI_Final_nutrition)!=0:

            Nutri_dicionary['NUTRITION_FACTS'] = [ENG_Final_nutrition,THAI_Final_nutrition]

            for key in (ENG_Serving_dict.keys() | THAI_Serving_dict.keys()):
                if key in ENG_Serving_dict: Serving_dict.setdefault(key, []).extend(ENG_Serving_dict[key])
                if key in THAI_Serving_dict: Serving_dict.setdefault(key, []).extend(THAI_Serving_dict[key])

    #     print(Serving_dict,Nutri_dicionary)
            result = {**Serving_dict,**Nutri_dicionary}
    #     print(result)
        return result



def attribute(input_pdf, pages, text):
    text_out = []
    output_io = io.StringIO()
    with open(input_pdf, 'rb') as input:
        extract_text_to_fp(input, output_io, page_numbers=[int(pages) - 1],
                           laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                           output_type='html', codec=None)

    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    results = html.find_all(
        lambda tag: tag.name == "div" and fuzz.ratio(text.lower(), tag.text.lower().replace('/n', '')) > 70)
    #     print(html)
    if results:
        if 'bold' in str(results[-1]).lower():
            for span in results[-1]:
                if 'bold' in span['style'].lower():
                    new_text = span.text.split('\n')
                    text_out.append(f'&lt;b&gt;{new_text[0]}&lt;/b&gt;')
                if 'bold' not in span['style'].lower():
                    #                 print('yes')
                    new_text = span.text.split('\n')
                    text_out.append(new_text[0])
            #             print(' '.join(text_out))
            return ' '.join(text_out)
        else:
            return None


def nutri_page_gen_info(pdf_file, page):
    content_list_1 = pdf_content(pdf_file, page)
    general_info_list = []
    general_info_dict = {}
    start = 0
    for i in range(0, len(content_list_1[0])):
        if 'product' in content_list_1[0][i].lower() and 'dose' in content_list_1[0][i + 1].lower():
            start = i
            pass
        #         general_info_list.append(('\n').join(content_list_1[0][i:i+4]))
        elif 'country of origin' in content_list_1[0][i].lower():
            general_info_list.append(
                ('\n').join(content_list_1[0][start:i + 1]).replace('COMMERCIALISED IN', '').replace('DOSE',
                                                                                                     '').replace(
                    'PRODUCT', '').replace('COUNTRY OF ORIGIN', ''))
            break

    return general_info_list


def nutri_prod_dic(general_info_list, pdf_file, page):
    prod_dict = {}
    prod_list = []
    if general_info_list:
        for cnt in general_info_list:
            #     print(new_cnt)
            splt = cnt.split('\n')
            for new_cnt in splt:
                if new_cnt.strip():
                    output = attribute(pdf_file, page, new_cnt)
                    if output:
                        final_txt = output
                    else:
                        final_txt = new_cnt

                    prod_list.append(final_txt)
        if prod_list:
            final_txt = ('\n').join(prod_list)
            lang = classify(final_txt)[0]
            if 'PRODUCT_INFORMATION' in prod_dict:
                prod_dict['PRODUCT_INFORMATION'].append({lang: final_txt})
            else:
                prod_dict['PRODUCT_INFORMATION'] = [{lang: final_txt}]

    return prod_dict

def final_nutrition_format(pdf_file, page):
    content_list_1 = pdf_content(pdf_file, page)
    flag = 0

    for j in range(0, len(content_list_1[0])):
        #         print(k)
        if 'nutrition facts' in content_list_1[0][j].lower() and "營養標示" in content_list_1[0][j]:
            print('nutri format 1')
            flag = 1
            break
        elif 'Nutrition Label 營養標示' in content_list_1[0][j]:
            print('nutri format 2')
            flag = 2
            break
        elif 'nutritional' in content_list_1[0][j].lower() and 'information' in content_list_1[0][j + 1].lower():
            print('nutri format 3')
            flag = 3
            break
        elif 'nutrition information' in content_list_1[0][j].lower():
            print('nutri format 4')
            flag = 4
            break
        elif 'nutrition facts' in content_list_1[0][j].lower():
            print('nutri format 5')
            flag = 5
            break
        else:
            #             print('another format')
            pass

    output = None
    if flag == 1:
        output = nutrition_format1(pdf_file, page)
    elif flag == 2:
        output = nutrition_format2(pdf_file, page)
    elif flag == 3:
        output = nutrition_format3(pdf_file, page)
    elif flag == 4:
        output = nutrition_format4(pdf_file, page)
    elif flag == 5:
        output = nutrition_format5(pdf_file, page)
    if output != None:
        return output


def ferrero_main(pdf_file, page):

    #     file_dict = {}
    #     page_dict = {}
    #     for p in page:
    pdf_file = get_input(pdf_file,input_pdf_location)
    with pdfplumber.open(pdf_file) as pdf:
        if int(page) <= len(pdf.pages):
            gen_cate_out = final_gen_dic(pdf_file, int(page))
            #     if 'PRODUCT_INFORMATION' not in gen_cate_out and gen_cate_out==None:
            #         nutri_cate_out = final_nutrition_format(pdf_file,int(page))
            #         general_info_list = nutri_page_gen_info(pdf_file,int(page))
            #         prod_dict = nutri_prod_dic(general_info_list)
            #     #     print(nutri_cate_out)
            #         if gen_cate_out!= None and nutri_cate_out!= None:
            #             return nutri_cate_out,gen_cate_out,prod_dict
            #         elif nutri_cate_out== None:
            #             return gen_cate_out
            #         elif gen_cate_out== None:
            #             return nutri_cate_out,prod_dict
            #     else:
            nutri_cate_out = final_nutrition_format(pdf_file, int(page))
            #     print(nutri_cate_out)
            if gen_cate_out != None and nutri_cate_out != None:
                if 'PRODUCT_INFORMATION' not in gen_cate_out:
                    general_info_list = nutri_page_gen_info(pdf_file, int(page))
                    prod_dict = nutri_prod_dic(general_info_list, pdf_file, int(page))
                    return {**nutri_cate_out, **gen_cate_out, **prod_dict}
                else:
                    return {**nutri_cate_out, **gen_cate_out}
            elif nutri_cate_out == None:
                return gen_cate_out
            elif gen_cate_out == None:
                general_info_list = nutri_page_gen_info(pdf_file, int(page))
                prod_dict = nutri_prod_dic(general_info_list, pdf_file, int(page))
                return {**nutri_cate_out, **prod_dict}
        else:
            return {}


# def overall_ferrero_func(pdf_file, page):
#     file_dict = {}
#     page_dict = {}
#     for p in page:
#         fianl_out = ferrero_main(pdf_file, int(p))
#         page_dict[p] = fianl_out
#     file_dict[pdf_file] = page_dict
#     return file_dict
