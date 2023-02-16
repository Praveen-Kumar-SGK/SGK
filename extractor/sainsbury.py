from .excel_processing import *
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

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
from pdf2docx import parse
import pdfplumber
import itertools
import tempfile
from fuzzywuzzy import fuzz
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import io

# filename_nutri = r"/Users/sakthivel/Documents/SGK/Nutrition Dataset/master_nutrition_sainsbury_model.sav"
master_nutri_classifier = joblib.load(sainsbury_nutri_model_location)

# model_loc = r"/Users/sakthivel/Documents/SGK/Sainsbury/dataset/sansbury_gen_model.sav"
classifier = joblib.load(sainsbury_model_location)

# document_location = r"/Users/sakthivel/Documents/SGK/Sainsbury/Input files/"


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


def text_preprocessing(text):
    text = str(text)
#     text = text.lower()
    text = text.replace('\r',' ').replace("\t","")
    text = re.sub(r"\w\$\d","",text)
    # text = re.sub(r'[^\w\s]','',text)
    # text = re.sub(r"\(.*\)|\[.*\]","",text)
    text = text.replace('(','').replace(')','').replace(':','')
    text = re.sub(r"\[.*\]","",text)
    return text.strip()

unwanted_items = ("back of pack declaration","reference intake","none",'typical values','typical analysis',
                 "nan","front of pack declaration","100g contains","use on pack","text","supportingtext",
                 "icon","product name") # "front of pack declaration",


def nutrition_dict(frn_nut_list):
    nutri_dict = {}
    unmapped_dict = {}
    counter = {}
    for i in range(0, len(frn_nut_list)):
        if len(frn_nut_list[i]) > 2:
            for j in range(2, len(frn_nut_list[i])):
                cnt = text_preprocessing(frn_nut_list[i][1])
                if cnt.replace('\n', '').lower() not in unwanted_items and frn_nut_list[i][j] != None:
                    classified_output = master_nutri_classifier.predict(laser.embed_sentences(cnt, lang='en'))
                    probability1 = master_nutri_classifier.predict_proba(laser.embed_sentences(cnt, lang='en'))
                    #                         classified_output = nutri_classifier.predict(get_sentence_embeding([cnt]))
                    #                         probability1 = nutri_classifier.predict_proba(get_sentence_embeding([cnt]))
                    probability1.sort()
                    prob1 = probability1[0][-1]
                    if prob1 > 0.75:
                        classified_output = classified_output[0]
                    else:
                        classified_output = cnt

                    counter.setdefault(classified_output, set()).add(i)
                    #print(cnt,classified_output,prob1)
                    value = frn_nut_list[i][j].replace('<', '&lt;').replace('>', '&gt;').strip()
                    if "reference intake" not in value.replace("\n", '').lower() and value.replace("\n",'').lower() not in unwanted_items:
                        column_header = "PDV" if "%" in value else "Value"
                        if classified_output in counter and len(counter[classified_output]) > 1:
                            column_header = f"{column_header}_{int(len(counter[classified_output])) - 1}"
                        if classified_output in nutri_dict:
                            nutri_dict[classified_output].append({column_header: {"en": value}})
                        else:
                            nutri_dict[classified_output] = [{column_header: {"en": value}}]
        elif len(frn_nut_list[i]) == 2:

            cnt = frn_nut_list[i][1].replace('<', '&lt;').replace('>', '&gt;').strip()
            #                 print(cnt)
            if cnt.strip():
                lang = classify(cnt)[0]
                if "serving" in frn_nut_list[i][1].lower() and "contains" in frn_nut_list[i][1].lower() and "nutrition" not in frn_nut_list[i][1].lower():
                    if "SERVING_SIZE" in unmapped_dict:
                        unmapped_dict["SERVING_SIZE"].append({lang: cnt})
                    else:
                        unmapped_dict["SERVING_SIZE"] = [{lang: cnt}]
                elif "reference intake" in frn_nut_list[i][1].lower():
                    if "DECLARATION_CONTEXT_FOOTNOTE" in unmapped_dict:
                        unmapped_dict["DECLARATION_CONTEXT_FOOTNOTE"].append({lang: cnt})
                    else:
                        unmapped_dict["DECLARATION_CONTEXT_FOOTNOTE"] = [{lang: cnt}]
                elif "nutrition" in frn_nut_list[i][1].lower() and "typical value" in frn_nut_list[i][1].lower():
                    if "NUTRITIONAL_CLAIM" in unmapped_dict:
                        unmapped_dict["NUTRITIONAL_CLAIM"].append({lang: cnt})
                    else:
                        unmapped_dict["NUTRITIONAL_CLAIM"] = [{lang: cnt}]
                else:
                    if "Unmapped" in unmapped_dict:
                        unmapped_dict["Unmapped"].append({lang: cnt})
                    else:
                        unmapped_dict["Unmapped"] = [{lang: cnt}]
        else:
            #                 print(frn_nut_list[i][0])
            cnt = frn_nut_list[i][0].replace('<', '&lt;').replace('>', '&gt;').strip()
            #                 print(cnt.replace("\n"," "))
            lang = classify(cnt)[0]
            if "Unmapped" in unmapped_dict:
                unmapped_dict["Unmapped"].append({lang: cnt})
            else:
                unmapped_dict["Unmapped"] = [{lang: cnt}]
    #     print(unmapped_dict)
    return nutri_dict, unmapped_dict


def general_dict_new(frn_nut_list):
    gen_dict={}
    unmapped_dict={}
    for i in range(0,len(frn_nut_list)):
        if frn_nut_list[i]:
            cnt = text_preprocessing(frn_nut_list[i][0])
            if cnt.replace("\n",'').lower() not in unwanted_items and cnt.strip():
                if cnt.replace("\n", '').lower() not in ["step", "time"]:
                    classified_output = classifier.predict(laser.embed_sentences(cnt, lang='en'))
                    probability1 = classifier.predict_proba(laser.embed_sentences(cnt, lang='en'))
                    probability1.sort()
                    prob1 = probability1[0][-1]
                    if prob1 > 0.75:
                        classified_output = classified_output[0]
                    else:
                        classified_output = 'Unmapped'
                else:
                    classified_output = 'Unmapped'
                cnt = frn_nut_list[i][0].replace('<', '&lt;').replace('>', '&gt;').strip()
                lang = classify(cnt)[0]
                if classified_output in ("INGREDIENTS_DECLARATION") and "before cooking" not in cnt.lower():
                    if "INGREDIENTS_DECLARATION" in gen_dict:
                        gen_dict["INGREDIENTS_DECLARATION"].append({lang:cnt})
                    else:
                        gen_dict["INGREDIENTS_DECLARATION"] = [{lang:cnt}]

                if len(frn_nut_list[i]) >1:
                    if classified_output not in ("Unmapped"):
                        for j in range(1,len(frn_nut_list[i])):
                                value = frn_nut_list[i][j].replace('<', '&lt;').replace('>', '&gt;').strip()
                                lang = classify(value)[0]
                                if value.replace("\n",'').lower() not in unwanted_items and value.strip() :
                                    if classified_output in gen_dict:
                                        gen_dict[classified_output].append({lang:value})
                                    else:
                                        gen_dict[classified_output] = [{lang:value}]
                    else:
                        for j in range(0,len(frn_nut_list[i])):
                                value = frn_nut_list[i][j].replace('<', '&lt;').replace('>', '&gt;').strip()
                                lang = classify(value)[0]
                                if value.replace("\n",'').lower() not in unwanted_items and value.strip() :
                                    if classified_output in gen_dict:
                                        gen_dict[classified_output].append({lang:value})
                                    else:
                                        gen_dict[classified_output] = [{lang:value}]



                elif len(frn_nut_list[i])==1 and classified_output not in ("INGREDIENTS_DECLARATIONS") :
                        if "Unmapped" in gen_dict:
                            if len(cnt) > 5:
                                if {lang:cnt} not in gen_dict["Unmapped"]:
                                    gen_dict["Unmapped"].append({lang:cnt})
                            else:
                                gen_dict["Unmapped"].append({lang:cnt})
                        else:
                            gen_dict["Unmapped"] = [{lang:cnt}]

    return gen_dict

def dictionary_append(list_of_dic):
    final_dict = {}
    for dic in list_of_dic:
        for key, value in dic.items():
            for cnt in value:
                for lang, txt in cnt.items():
                    if key in final_dict:
                        final_dict[key].append({lang: txt})
                    else:
                        final_dict[key] = [{lang: txt}]

    return final_dict


def pdf_extract_table(pdf_file,page_no):

    with pdfplumber.open(pdf_file) as pdf:
        if int(page_no) <= len(pdf.pages):
            page = pdf.pages[page_no-1]
            tables = page.extract_tables()
            return tables
        else:
            return {}


def front_nutri_temp_list(l):
    nutrition_list = ["energy", "fat", "saturates", "sugars", "salt"]
    temp_list = []
    for i in range(0, len(l)):

        if l[i][0].lower() in nutrition_list:
            l[i].insert(0, "")
            temp_list.append(l[i])
        else:
            temp_list.append(l[i])
    return temp_list


def pdf_to_docx(pdf_file, page_no,converted_docx):

    # docx_file = document_location + 'filename.docx'
    # convert pdf to docx
    parse(pdf_file, converted_docx, pages=[page_no - 1])

    return converted_docx


def pdf_to_content_list(docx_file):
    #     docx_file = pdf_to_docx(file,page)
    html = mammoth.convert_to_html(docx_file).value
    soup = BeautifulSoup(html, "html.parser")
    #     print(soup)
    table_content_list_all = []
    for tables in soup.find_all('p'):
        raw_html = str(tables).replace('<strong>', '&lt;b&gt;').replace('</strong>', '&lt;/b&gt;').replace('<br/>',
                                                                                                           '\n').replace(
            '\t', '')
        #         raw_html = str(tables).replace('<strong>','&lt;b&gt;').replace('</strong>','&lt;/b&gt;').replace('\t','').replace('<br/>','\n')
        #         print(raw_html)
        cleantext = BeautifulSoup(raw_html, "html").text.strip()
        cleantext = cleantext.split('\n')
        #         print(cleantext)
        if cleantext:
            for cnt in cleantext:
                table_content_list_all.append(cnt.strip())

    #     print(table_content_list_all)
    return table_content_list_all


class recursive(object):
    def __init__(self, _list, index, score, text, src_text):
        self.score = score
        self.index = index
        self._list = _list
        self.text = text
        self.src_text = src_text

    def try_recursion(self):
        #         try:
        combine_next_seg = lambda x: ''.join((self.text, self._list[x]))  # one line function
        #         except:
        #             combine_next_seg = self.text  # one line function
        try:
            temp_text = combine_next_seg(self.index)
        except:
            temp_text = self.text
        #         temp_text = combine_next_seg(self.index)
        temp_score = fuzz.ratio(re.sub("<.*?>", "", temp_text.lower()), self.src_text.lower())
        if temp_score > self.score:
            self.score = temp_score
            self.index = self.index + 1
            self.text = temp_text
            self.try_recursion()
        # print(f"return value ========>{self.score}---->{self.index}")
        return self.score, self.index


def search_bold_content(text, content_list):
    score_dict = {}
    for index, div_text in enumerate(content_list):
        score = fuzz.ratio(text, re.sub("<.*?>", "", div_text))
        #         print(score)
        if score > 30:
            temp_score_recur, upto_index_recur = recursive(content_list, index, score, div_text,
                                                           text).try_recursion()
            # print(index,upto_index_recur)
            score_dict[temp_score_recur] = " ".join(content_list[index:upto_index_recur + 1])

    if score_dict and max(score_dict) > 80:
        #         print(score_dict[max(score_dict)])
        return score_dict[max(score_dict)]

def attribute(input_pdf,pages,text):
    text_out=[]
    output_io = io.StringIO()
    with open(input_pdf,'rb') as input:
                        extract_text_to_fp(input, output_io,page_numbers= [int(pages)-1],
                                           laparams=LAParams(line_margin=0.15, line_overlap=0.4, all_texts=False),
                                           output_type='html', codec=None)

    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    results = html.find_all(
        lambda tag: tag.name == "div" and fuzz.ratio(text.lower(),tag.text.lower().replace('/n',''))>66)
    # print("attribute$$$$$$$$$",results)
    if len(results) == 1:
        if 'bold' in str(results[-1]).lower():
            for span in results[-1]:
                if 'bold' in span['style'].lower():
                    new_text= span.text.split('\n')
                    text_out.append(f'<b>{new_text[0]}</b>')
                if 'bold' not in span['style'].lower():
    #                 print('yes')
                    new_text= span.text.split('\n')
                    text_out.append(new_text[0])
            # print(' '.join(text_out))
            return ''.join(text_out)
        else:
            return None
    elif len(results) > 1:
        ind = []
        for index in range(0, len(results)):
            text_list = []
            for span in results[index]:
                text_list.append(span.text)
            if text_list:
                output = fuzz.ratio(text.lower(), "".join(text_list).replace('/n', '')) > 80
                if output:
                    ind.append(index)
        if not ind:
            return None
        if ind and 'bold' in str(results[ind[-1]]).lower():
            for span in results[ind[-1]]:
                if 'bold' in span['style'].lower():
                    new_text = span.text.split('\n')
                    text_out.append(f'<b>{new_text[0]}</b>')
                if 'bold' not in span['style'].lower():
                    new_text = span.text.split('\n')
                    text_out.append(new_text[0])
            return ''.join(text_out)
        else:
            return None

def bold_text_dic(dictionary,pdf_file,page,converted_docx):
    new_dict={}
    if dictionary:
        if any(k in list(dictionary.keys()) for k in ["INGREDIENTS_DECLARATION"]):
            # docx_file = pdf_to_docx(pdf_file,page,converted_docx)
            # cnt_list = pdf_to_content_list(docx_file)
            for key,value in dictionary.items():
                if key in ["INGREDIENTS_DECLARATION"]:
                    for dic in value:
                        for lang,txt in dic.items():
                            temp_list=[]
                            txt = txt.split('\n')
                            for text in txt:
#                             bold_txt = search_bold_content(txt,cnt_list)
                                bold_txt = attribute(pdf_file,page,text)
#                             print(bold_txt)
                                if bold_txt:
                                    temp_list.append(bold_txt)
                                else:
                                    temp_list.append(text)
#                                 print(temp_list)
                            if temp_list:
                                bold_txt = ('').join(temp_list)
#                                 print(bold_txt)
                                if bold_txt:
                                    bold_txt = bold_txt.replace('<b>','&lt;b&gt;').replace('</b>','&lt;/b&gt;').replace('<', '&lt;').replace('>', '&gt;').strip()
                                    if key in new_dict:
                                        new_dict[key].append({lang:bold_txt})
                                    else:
                                        new_dict[key] = [{lang:bold_txt}]
                                else:
                                    if key in new_dict:
                                        new_dict[key].append({lang:txt})
                                    else:
                                        new_dict[key] = [{lang:txt}]
                else:
                    new_dict[key] = value
        else:
            new_dict = dictionary

    return new_dict

def serving_dict(serve_list):
    serve_dict={}
    for ind,value in enumerate(serve_list):
        for in_row,in_value in enumerate(serve_list[ind]):
            if "reference intake" in in_value.lower():
                lang = classify(in_value)[0]
                if "DECLARATION_CONTEXT_FOOTNOTE" in serve_dict:
                    serve_dict["DECLARATION_CONTEXT_FOOTNOTE"].append({lang:in_value})
                else:
                    serve_dict["DECLARATION_CONTEXT_FOOTNOTE"] = [{lang:in_value}]

            elif any(x for x in ["serves","per","serving"] if x in in_value.lower()) :
                lang = classify(in_value)[0]
                if "SERVING_SIZE" in serve_dict:
                    serve_dict["SERVING_SIZE"].append({lang:in_value})
                else:
                    serve_dict["SERVING_SIZE"] = [{lang:in_value}]

    return serve_dict

def nutri_header_dict(nutri_header_list):
    header_dict={}
    for row_ind in range(0,len(nutri_header_list)):
        text = ("").join(nutri_header_list[row_ind]).lower()
        if "back of pack" in text and "nutrition" in text:
            header = nutri_header_list[row_ind+1][1:]
            if header:
                for txt in header[1:]:              # ignore first value of nutrition header
                    value = txt.strip()
                    if value:
                        lang = classify(value)[0]
                        header_dict.setdefault("NUTRI_TABLE_HEADERS", []).append({lang: value})
                break
    return header_dict


def pdf_data_extraction(pdf_file, page_no):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    pdf_file = get_input(pdf_file, input_pdf_location)
    with pdfplumber.open(pdf_file) as pdf:
        if int(page_no) <= len(pdf.pages):
            tables = pdf_extract_table(pdf_file, int(page_no))
            df_list = []
            final_gen_list = []
            final_nutri_list = []
            final_nutri_dict = {}
            for lis in tables:
                df = pd.DataFrame(lis)
                df_list.append(df)

            final_df = pd.concat(df_list)
            final_df = final_df.replace('', np.nan, regex=True)
            final_df.loc[:, 0] = final_df.loc[:, 0].ffill()
            final_df = final_df.astype(str)
            cnt_list = final_df.values.tolist()

            front_nutri_list = []
            back_nutri_list = []
            gen_cnt_list = []
            for row in range(0, len(cnt_list)):
                if "front of pack" in cnt_list[row][0].lower():
                    front_nutri_list.append(cnt_list[row])
                elif "back of pack" in cnt_list[row][0].lower():
                    back_nutri_list.append(cnt_list[row])
                elif "nutrition information" in cnt_list[row][0].lower():
                    back_nutri_list.append(cnt_list[row])
                else:
                    gen_cnt_list.append(cnt_list[row])
            if gen_cnt_list:
                gen_cnt_list = [[x for x in y if x.replace('\n','').lower() not in ['nan','none','product name:']] for y in gen_cnt_list]
                gen_cate_dict = general_dict_new(gen_cnt_list)
                converted_docx = f'{temp_directory.name}/converted.docx'
                new_gen_cate_dic = bold_text_dic(gen_cate_dict, pdf_file, page_no,converted_docx)
                final_gen_list.append(new_gen_cate_dic)

            if len(front_nutri_list) > 1:
                front_nutri_list = list(map(list, itertools.zip_longest(*front_nutri_list, fillvalue=None)))
                front_nutri_list = front_nutri_temp_list(front_nutri_list)
                serve_dict = serving_dict(front_nutri_list)
                nutri_dict1, gen_cate_dict1 = nutrition_dict(front_nutri_list)
                if nutri_dict1:
                    final_nutri_list.append(nutri_dict1)
                if gen_cate_dict1:
                    final_gen_list.append(gen_cate_dict1)
                if serve_dict:
                    final_gen_list.append(serve_dict)
            if len(back_nutri_list) > 1:
                back_nutri_list = [[x for x in y if x not in ['nan', 'None']] for y in back_nutri_list]
                nutri_dict2, gen_cate_dict2 = nutrition_dict(back_nutri_list)
                header_dict = nutri_header_dict(back_nutri_list)
                final_gen_list.append(header_dict)
                if nutri_dict2:
                    for key, value in header_dict.items():
                        for items in value:
                            for lang, text in items.items():
                                nutri_dict2.setdefault("NUTRI_TABLE_HEADERS", []).append({"Value": {"en": text}})
                    final_nutri_list.append(nutri_dict2)
                if gen_cate_dict2:
                    final_gen_list.append(gen_cate_dict2)

            overall_gen_dict = dictionary_append(final_gen_list)
            if final_nutri_list:
                final_nutri_dict["NUTRITION_FACTS"] = final_nutri_list

            return {**overall_gen_dict, **final_nutri_dict}
        else:
            return {}


def sainsbury_main(pdf_file, pages):
    t1 = time.time()
    final_dict = {}
    for page in pages.split(","):
        print(page)
        page_response = pdf_data_extraction(pdf_file, int(page))
        final_dict[page] = page_response

    t2 = time.time()
    print(f'Complted in {t2 - t1} secs')
    return final_dict








