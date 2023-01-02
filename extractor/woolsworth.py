from .excel_processing import *
import pandas as pd
import warnings
warnings.filterwarnings("ignore")

import numpy as np
from langid import classify
import time
import warnings
warnings.filterwarnings("ignore")
import joblib
from bs4 import BeautifulSoup
import re
import pdfplumber
import tempfile
from fuzzywuzzy import fuzz
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import io
import shutil
import camelot

## From Sainsbury

classifier = joblib.load(woolsworth_gen_model_from_sainsbury)

mlp_model = joblib.load(woolswoth_gen_model)
mlp_model_1 = joblib.load(woolswoth_nutri_model)


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
        print("local or dev environment")
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

def general_dict_new(frn_nut_list):
    gen_dict={}
    unmapped_dict={}
    for i in range(0,len(frn_nut_list)):
        if frn_nut_list[i]:
            cnt = text_preprocessing(frn_nut_list[i][0])
            if cnt.replace("\n",'').lower() not in unwanted_items and cnt.strip():
                classified_output = classifier.predict(laser.embed_sentences(cnt, lang='en'))
                probability1 = classifier.predict_proba(laser.embed_sentences(cnt, lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]
                if prob1 > 0.75:
                       classified_output = classified_output[0]
                else:
                        classified_output = 'Unmapped'
                cnt = frn_nut_list[i][0].replace('<', '&lt;').replace('>', '&gt;').strip()
                lang = classify(cnt)[0]
                if classified_output in ("INGREDIENTS_DECLARATION") and "before cooking" not in cnt.lower():
                    if "INGREDIENTS_DECLARATION" in gen_dict:
                        gen_dict["INGREDIENTS_DECLARATION"].append({lang:cnt})
                    else:
                        gen_dict["INGREDIENTS_DECLARATION"] = [{lang:cnt}]

                if len(frn_nut_list[i]) > 1:
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

def Nutrition_extraction_func(pdf_file, page_no):
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[int(page_no) - 1]
        text = page.extract_text().split('\n')
        print(''.join(text))
        matching_text = (
        'energy', 'calories', 'total carbohydrate', 'dietary fiber', 'cholesterol', 'fat', 'total fat', 'sodium',
        'protein', 'saturated', 'trans', 'polyunsaturated', 'omega', 'acids', 'epa', 'dha', 'monounsaturated',
        'carbohydrate', 'sugars', 'vitamin d', 'calcium', 'iron', 'potassium', 'total sugars', 'sodium',
        'saturated fat', 'trans fat')
        extract_nutri = []
        start_Ingredient = False
        if 'nutrition information' in ''.join(text).lower():
            start = False
            for i in range(len(text)):
                if 'Back of Pack  Nutrition' in text[i]:
                    start = True
                if '*Percentage daily intakes' in text[i] or "reference intake" in text[i].lower():
                    start = False
                if start:
                    if text[i] == None:
                        continue
                    extract_nutri.append(text[i])
        elif 'INGREDIENTS LIST' in ''.join(text):
            for j in range(len(text)):
                #print(text[i])
                if 'INGREDIENTS LIST' in text[j]:
                    sp = re.findall(r'[A-Za-z\u00C0-\u00D6\u00D8-\u00f6\u00f8-\u00ff\s]+',text[j + 1].replace("-", "").strip())
                    if sp and sp[0].lower().strip() in matching_text:
                        start_Ingredient = True
                if '*Percentage daily intakes' in text[j] or "reference intake" in text[j].lower():
                    start_Ingredient = False
                if start_Ingredient:
                    if text[j] == None:
                        continue
                    extract_nutri.append(text[j])
#     print(extract_nutri)
    return extract_nutri


def Calories(extract_nutri):
    cleaned_nutri_list = []
    for j in extract_nutri:
        if re.search(r'\bcal\b', j.lower()):
            # cleaned_nutri_list.append('Calories ' + j)
            cleaned_nutri_list.append('Energy ' + j)
        else:
            cleaned_nutri_list.append(j)
    # print(cleaned_nutri_list)
    return cleaned_nutri_list



def Nutri_serve_header(Cleaned_list):
    nutrition_lst = []
    serving = []
    header = []
    Header_dic = {}
    for i in range(len(Cleaned_list)):
        #     print(Cleaned_list[i])
        first_ele_nutri = re.findall(r'[\-\sA-Za-z\u00C0-\u00D6\u00D8-\u00f6\u00f8-\u00ff\s]+', Cleaned_list[i])
        #     print(first_ele_nutri[0])
        Xtest_laser = laser.embed_sentences(first_ele_nutri[0], lang='en')
        model_op = mlp_model.predict(Xtest_laser)
        classified_output = model_op[0]
        item_prob = mlp_model.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob = item_prob[0][-1]
        #     print({Cleaned_list[0]+'_'+str(prob):classified_output})
        if prob >= 0.94 and classified_output in ('SERVING_SIZE', 'SERVING_PER_CONTAINER'):
            serving.append(Cleaned_list[i])
        elif prob >= 0.80 and classified_output in ("NUTRI_TABLE_HEADERS"):
            #         print({Cleaned_list[i]+'_'+str(prob):classified_output})
            if classified_output in Header_dic:
                Header_dic[classified_output].append({classify(Cleaned_list[i])[0]: str(Cleaned_list[i]).strip()})
            else:
                Header_dic[classified_output] = [{classify(Cleaned_list[i])[0]: str(Cleaned_list[i]).strip()}]
        else:

            Xtest_laser_1 = laser.embed_sentences(
                first_ele_nutri[0].replace("-", "").replace("EPA", "Omega").replace("DHA", "Omega").replace("DHA",
                                                                                                            "Omega").replace(
                    "Includes", "Includes Added Sugars"), lang='en')
            model_op_1 = mlp_model_1.predict(Xtest_laser_1)
            classified_output_1 = model_op_1[0]
            #
            item_prob_1 = mlp_model_1.predict_proba(Xtest_laser_1)
            item_prob_1[0].sort()
            prob_1 = item_prob_1[0][-1]
            print("nutrition output ",{first_ele_nutri[0]+'_'+str(prob_1):classified_output_1})
            if prob_1 >= 0.95:
                nutrition_lst.append(Cleaned_list[i])
#     print(nutrition_lst)
    # print(serving)
    #     print(Header_dic)
    return nutrition_lst, serving, Header_dic


def Nutrition_correct_list(nutrition_list):
    Nutri_list = []
    for x in nutrition_list:
        element_list = []
        value_list = []

        regex_extracted = re.findall(
            r"([\w\,\-\s]*?)\s+(\<?\s?\-?\d{0,3}\.?\d{0,2}\s?(%|g added sugars|g|kj|kcal|mg|mcg|cal))", x, flags=re.I)
        if not regex_extracted:
            regex_extracted = re.findall(r"([\w\,\-\s]*?)\s+((\<?\s?\-?\d{0,3}\.?\d{0,2}\s?))", x, flags=re.I)
        for tuple_content in regex_extracted:
            if tuple_content[0] and tuple_content[0].strip() not in ("-"):
                element_list.append(tuple_content[0])
            if tuple_content[1]:
                value_list.append(tuple_content[1])
        storing = [i for i in value_list]
        storing.insert(0, " ".join(element_list).strip())
        #     print(" ".join(element_list).strip(),value_list)

        Nutri_list.append(storing)
    return Nutri_list


def Appending_dic(list_of_list):
    nutri_dic = {}
    counter = {}
    for l in range(0, len(list_of_list)):
        counter.setdefault(list_of_list[l][0], 0)
        counter[list_of_list[l][0]] = counter[list_of_list[l][0]] + 1
        for m in range(1, len(list_of_list[l])):
            # print(list_of_list[l][m])
            list_of_list[l][m] = list_of_list[l][m].replace('<', '&lt;').replace('>', '&gt;')
            if list_of_list[l][m] != '':
                column_header = "PDV" if "%" in str(list_of_list[l][m]) else "Value"
                if str(list_of_list[l][0]) in counter and counter[str(list_of_list[l][0])] > 1:
                    column_header = f"{column_header}_{int(counter[str(list_of_list[l][0])]) - 1}"
                nutri_dic.setdefault(list_of_list[l][0].strip(),[]).append({column_header: {'en': list_of_list[l][m].strip()}})
    return nutri_dic

def Nutri_final_prediction(dic_values):
    dic = {}
    for keys, value in dic_values.items():
        Xtest_laser_1 = laser.embed_sentences(keys.replace("-", "").strip(), lang='en')
        model_op_1 = mlp_model_1.predict(Xtest_laser_1)
        classified_output_1 = model_op_1[0]
        #
        item_prob_1 = mlp_model_1.predict_proba(Xtest_laser_1)
        item_prob_1[0].sort()
        prob_1 = item_prob_1[0][-1]
        #     print({classified_output_1+str(prob_1):keys})
        if prob_1 > 0.90:
            if classified_output_1 != 'UNMAPPED':
                if classified_output_1 in dic:
                    dic[classified_output_1].append(value)
                else:
                    dic[classified_output_1] = value
            else:
                if keys in dic:
                    dic[keys].append(value)
                else:
                    dic[keys] = value
        else:
            if keys in dic:
                dic[keys].append(value)
            else:
                dic[keys] = value
    return dic



def Serving(serving_list):
    Serving_lst = []
    for ee in range(0, len(serving_list)):
        if ":" in serving_list[ee]:
            serve = serving_list[ee].split(":")
        else:
            serve = [serving_list[ee]]
        Serving_lst.append(serve)
    #     print(len(Serving_lst))
    serve_dic = {}
    for l in range(0, len(Serving_lst)):
        if len(Serving_lst[l]) > 1:
            for m in range(1, len(Serving_lst[l])):
                Serving_lst[l][m] = Serving_lst[l][m].replace('<', '&lt;').replace('>', '&gt;')
                if Serving_lst[l][m] != '':
                    #             print(Serving_lst[l][m])
                    if Serving_lst[l][0].strip() in serve_dic:
                        serve_dic[Serving_lst[l][0].strip()].append(
                            {classify(Serving_lst[l][m])[0]: str(Serving_lst[l][m].strip())})
                    else:
                        serve_dic[Serving_lst[l][0].strip()] = [
                            {classify(Serving_lst[l][m])[0]: str(Serving_lst[l][m]).strip()}]
        elif len(Serving_lst[l]) == 1:
            #             print(Serving_lst[l])
            if Serving_lst[l][0].strip() in serve_dic:
                serve_dic[Serving_lst[l][0].strip()].append(
                    {classify(Serving_lst[l][0])[0]: str(Serving_lst[l][0].strip())})
            else:
                serve_dic[Serving_lst[l][0].strip()] = [
                    {classify(Serving_lst[l][0])[0]: str(Serving_lst[l][0]).strip()}]

    serving_dic = {}
    for ser_keys, ser_value in serve_dic.items():
        Xtest_laser = laser.embed_sentences(ser_keys, lang='en')
        model_op = mlp_model.predict(Xtest_laser)
        classified_output = model_op[0]
        item_prob = mlp_model.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob = item_prob[0][-1]
        #         print({classified_output+str(prob):ser_keys})
        if prob > 0.90:
            if classified_output != 'None':
                if classified_output in serving_dic:
                    serving_dic[classified_output].append(ser_value)
                else:
                    serving_dic[classified_output] = ser_value
            else:
                if ser_keys in serving_dic:
                    serving_dic[ser_keys].append(ser_value)
                else:
                    serving_dic[ser_keys] = ser_value
                #     print(serving_dic)
    return serving_dic



def attribute(input_pdf,pages,text):
    text_out=[]
    output_io = io.StringIO()
    with open(input_pdf,'rb') as input:
                        extract_text_to_fp(input, output_io,page_numbers= [int(pages)-1],
                                           laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                                           output_type='html', codec=None)

    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    results = html.find_all(
        lambda tag: tag.name == "div" and fuzz.ratio(text.lower(),tag.text.lower().replace('/n',''))>66)
    # print(results)
    if len(results) == 1:
        if 'bold' in str(results[-1]).lower():
            for span in results[-1]:
                if 'bold' in span['style'].lower():
                    new_text = span.text.split('\n')
                    text_out.append(f'<b>{new_text[0]}</b>')
                if 'bold' not in span['style'].lower():
                    #                 print('yes')
                    new_text = span.text.split('\n')
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
        if 'bold' in str(results[ind[-1]]).lower():
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

def pdf_plumber_bold_text_dic(dictionary,pdf_file,page):
    new_dict={}
    if dictionary:
        if any(k in list(dictionary.keys()) for k in ["INGREDIENTS_DECLARATION","ALLERGEN_STATEMENT"]):
            for key,value in dictionary.items():
                if key in ["INGREDIENTS_DECLARATION","ALLERGEN_STATEMENT"]:
                    for dic in value:
                        for lang,txt in dic.items():
                            temp_list=[]
                            txt = txt.split('\n')
                            for text in txt:
                                bold_txt = attribute(pdf_file,page,text)
                                print(bold_txt)
                                if bold_txt:
    #                                     print(bold_txt)
                                    temp_list.append(bold_txt)
                                else:
                                    temp_list.append(text)
#                             print(temp_list)
                            if temp_list:
                                bold_text = ('\n').join(temp_list)
#                                 print(bold_txt)
                                if bold_text:
                                    bold_text = bold_text.replace('<b>','&lt;b&gt;').replace('</b>','&lt;/b&gt;').strip()
    #                                 if any(k in bold_txt for k in cnt_keys):
    #                                     bold_txt = [bold_txt.replace(s,"") for s in cnt_keys if s in bold_txt][0]
    #                                 else:
    #                                     bold_txt = bold_txt
                                    if key in new_dict:
                                        new_dict[key].append({lang:bold_text})
                                    else:
                                        new_dict[key] = [{lang:bold_text}]
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
    
def nutri_table_header(pdf_file, page_no):
    nutri_header_dict = {}

    tables = camelot.read_pdf(pdf_file, pages=str(page_no), flavor='stream', row_tol=12, col_tol=10)
    for table in tables:
        new_list = table.df.values.tolist()
        for row_ind in range(0, len(new_list)):
            text = (" ").join(new_list[row_ind]).lower()
            if "% daily intake" in text:
                for col_ind in range(1, len(new_list[row_ind])):        # ignoring first column in header
                    value = new_list[row_ind][col_ind].strip()
                    if value:
                        lang = classify(value)[0]
                        nutri_header_dict.setdefault("NUTRI_TABLE_HEADERS", []).append({lang: value})
    return nutri_header_dict


def Nutri_function_call(pdf_file, page_no):
    extract_nutri = Nutrition_extraction_func(pdf_file, page_no)
    nutri_header_dict = nutri_table_header(pdf_file, page_no)
    Cleaned_list = Calories(extract_nutri)
    nutrition_list, serving_list, Header_dic = Nutri_serve_header(Cleaned_list)
    Nutri_cleaned = Nutrition_correct_list(nutrition_list)
    Nutri_values = Appending_dic(Nutri_cleaned)
    Nutrition_final = Nutri_final_prediction(Nutri_values)
    if nutri_header_dict:
        for key, value in nutri_header_dict.items():
            for items in value:
                for lang, text in items.items():
                    Nutrition_final.setdefault("NUTRI_TABLE_HEADERS", []).append({"Value": {"en": text}})
    Serving_dic = Serving(serving_list)
    Nutri_dic = {}
    if 'NUTRITION_FACTS' in Nutri_dic:
        Nutri_dic['NUTRITION_FACTS'].append(Nutrition_final)
    else:
        Nutri_dic['NUTRITION_FACTS'] = [Nutrition_final]

    Nutri_serving_Header_dictionary = {**Serving_dic,
                                       **Nutri_dic,**nutri_header_dict}  # in future update in training data set(woolworth_general) and add **Header_dic
    #     print(Nutri_serving_Header_dictionary)
    return Nutri_serving_Header_dictionary


def pdf_data_extraction(pdf_file, page_no):
    with pdfplumber.open(pdf_file) as pdf:
        if int(page_no) <= len(pdf.pages):
            tables = pdf_extract_table(pdf_file, int(page_no))
            df_list = []

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
                else:
                    gen_cnt_list.append(cnt_list[row])
            if gen_cnt_list:
                gen_cnt_list = [[x for x in y if x.replace('\n','').lower() not in ['nan','none','product name:']] for y in gen_cnt_list]
                gen_cate_dict = general_dict_new(gen_cnt_list)
                # converted_docx = f'{temp_directory.name}/converted.docx'
                # new_gen_cate_dic = bold_text_dic(gen_cate_dict, pdf_file, page_no,converted_docx)
                gen_cate_dict = pdf_plumber_bold_text_dic(gen_cate_dict, pdf_file, page_no)
                # final_gen_list.append(gen_cate_dict)

            Nutri_serving_Header_dictionary = Nutri_function_call(pdf_file, page_no)

            if bool(gen_cate_dict) == True and bool(Nutri_serving_Header_dictionary['NUTRITION_FACTS'][0]) == True:
                Main_dict = {**gen_cate_dict, **Nutri_serving_Header_dictionary}
            elif bool(gen_cate_dict) == True:
                Main_dict = gen_cate_dict
            elif bool(Nutri_serving_Header_dictionary['NUTRITION_FACTS'][0]) == True:
                Main_dict = Nutri_serving_Header_dictionary
            else:
                Main_dict = {}
            return Main_dict
        else:
            return {}

def woolsworth_main(pdf_file, pages):
    t1 = time.time()
    final_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    pdf_file = get_input(pdf_file, input_pdf_location)
    for page in pages.split(","):
        print(page)
        page_response = pdf_data_extraction(pdf_file, int(page))
        final_dict[page] = page_response

    t2 = time.time()
    print(f'Complted in {t2 - t1} secs')
    try:
        temp_directory.cleanup()
    except:
        shutil.rmtree(temp_directory.name)
    finally:
        print("temp_folder_cleaned")
    return final_dict
