import pdfplumber
import camelot
import smbclient
import re
import numpy as np
from fuzzywuzzy import fuzz , process
import pandas as pd
import joblib
from laserembeddings import Laser
from sklearn.neural_network import MLPClassifier
import tempfile
from .excel_processing import base

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

#initialize laser
laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)

title_card = ['^COMPANY CONTACT INFORMATION$','^PRODUCT SPECIFIC REQUIRED INFORMATION$','^PRODUCT INFORMATION$','^CLAIM INFORMATION$','^ALLERGEN SUPPORT INFORMATION$','^CERTIFICATIONS$','rev:\s{0,1}?\d{0,1}\/\d{0,1}\/\d{0,4}?','This section to be completed','\S{4,5}\:\/\/(www)?\.?\w*\.\w*\/?',
              'example','^LABEL COPY']

title_card_dict = {'GENERAL INFORMATION':'rev:\s{0,1}?\d{0,1}\/\d{0,1}\/\d{0,4}?',
                   'COMPANY CONTACT INFORMATION':'^COMPANY CONTACT INFORMATION$',
                   'PRODUCT INFORMATION':'^PRODUCT INFORMATION$',
                   'CLAIM INFORMATION':'^CLAIM INFORMATION$',
                   'ALLERGEN SUPPORT INFORMATION':'^ALLERGEN SUPPORT INFORMATION$',
                   'CERTIFICATIONS':'^CERTIFICATIONS$',
                   'LABEL COPY':'^LABEL COPY$',
                   'PRODUCT SPECIFIC REQUIRED INFORMATION':'^PRODUCT SPECIFIC REQUIRED INFORMATION$',
                   'NUTRITION_SERVING':'^VARIED$',
                   'NUTRITION':'^Serving Size$',
                   }

unwanted_header = ['(ALL PROVIDED INSTRUCTIONS MUST BE VALIDATED. COOKING INSTRUCTIONS MUST INCLUDE AN INTERNAL TEMPERATURE STATEMENT).',
                   '(N/A IF DOES NOT APPLY.)','(END TEMPERATURE MUST MEET USDA.)','(PLEASE PROVIDE DNRF STATEMENT.)',
                   '(N/A IF DOESN"T APPLY.)','(IF YES, PLEASE PROVIDE).','(YES / NO) PLEASE PROVIDE DNRF STATEMENT)',
                   'END TEMPERATURE MUST MEET USDA MINIMUM STANDARDS.',
                   '(N/A if does not apply. IF product is subject to California cleaning laws=please provide the intentionally added ingredients from Designated Lists including fragrance to be used as the ingredient statement, unless EPA)',
                   '(All claims must have substantiation sent in with this document, test results etc.)',
                   'PLEASE LIST ANY FRONT OF PACK TEXT AS IT PERTAINS : KEEP OUT OF REACH OF CHILDREN, SIGNAL WORD, PRECAUTIONARY TEXT, AND REFERRAL STATEMENT TO SEE BACK PANEL.',
                   '(INCLUDE SMALL PARTS, CHOKE WARNING, SUFFOCATION WARNINGS, PRECAUTIONARY TEXT, SIGNAL WORD, FIRST AID TEXT, PHYSICAL OR CHEMICAL HAZARDS)',
                   'PROPER OPENING OF PRODUCT WHERE/WHAT NOT TO USE PRODUCT ON HANDLING STATEMENTS',
                   'INCLUDE ANY "COMPARE TO" STATEMENTS IN THIS SECTION ALONG WITH DISCLAIMERS',
                   'EXAMPLE -CAPSULES, TABLETS, SOFTGELS, GUMMIES','Examples: 16oz (1 LB) 453g, 100 COATED TABELTS, 25 LIQUID GELS',
                   'PLEASE NOTE WE DO NOT USE STRUCTURE FUNCTIONS CLAIMS','All claims must have substantiation sent in with this document, test results etc.',
                   'PLEASE LIST ANY FRONT OF PACK TEXT AS IT PERTAINS : KEEP OUT OF REACH OF CHILDREN, SIGNAL WORD, PRECAUTIONARY TEXT, AND REFERRAL STATEMENT TO SEE BACK PANEL.',
                   '(INCLUDE SMALL PARTS, CHOKE WARNING, SUFFOCATION WARNINGS, PRECAUTIONARY TEXT, CONSULT A PHYSICIAN, HEALTH CONDITONS, MEDICATION INTERACTION, ALLERGIC REACTIONS, IRON WARNINGS, MACHINERY AND DROWSINESS, ALCOHOL, ANY OTHER STATEMENTS )',
                   'ALSO INCLUDE ANY "COMPARE TO" STATEMENTS IN THIS SECTION ALONG WITH DISCLAIMERS. PLEASE PROVIDE THE NATIONAL BRAND SUPPLEMENT PANEL ON THE "PANEL INFORMATION " TAB IF YOU ARE USING A COMPARE TO STATEMENT.',
                   ]

def cleaning_unwanted_titles(text):
    for title in title_card:
        if re.search(r"{}".format(title), text, re.I):
            # print(text)
            return ''
    return text

def cleaning_unwanted_headers(df):
    index_to_clear = []
    rows, columns = df.shape
    for column in range(columns)[:1]:
        for row in range(rows):
            header = df[column][row].strip()
            if ":" not in header and header.strip():
                loop_check = True
                temp_score = 0
                while loop_check:
                    _, score = process.extract(header, unwanted_header, scorer=fuzz.partial_ratio)[0]
                    _, score1 = process.extract(header, unwanted_header, scorer=fuzz.token_sort_ratio)[0]
                    if score > 90 and score1 > temp_score:
                        # print('header-------->', header)
                        temp_score = score1
                        index_to_clear.append(row)
                        df[column][row] = ""
                        # print(row)
                        try:
                            header = " ".join((header, df[column][row + 1])).strip()
                            row = row + 1
                        except:
                            loop_check = False
                    else:
                        loop_check = False
    return df

def noise_removal_1(df):                   # remove folded line within brackets ()
    rows, columns = df.shape
    for column in range(columns)[:1]:
        for row in range(rows):
            header = df[column][row].strip()
            # print(header)
            if header:
                if "(" in header and ")" not in header:
                    temp_rows = []
                    temp_row_index = []
                    for _row in range(row, rows):
                        if ")" not in df[column][_row]:
                            temp_row_index.append(_row)
                            temp_rows.append(df[column][_row])
                        else:
                            temp_row_index.append(_row)
                            temp_rows.append(df[column][_row])
                            break
                    for _row in temp_row_index:
                        df[column][_row] = " ".join(temp_rows)
                    # print(" ".join(temp_rows))
                    # print(f'temp row----->{temp_rows}')
                else:
                    pass
    return df

def noise_removal_2(df):
    rows, columns = df.shape
    for column in range(columns)[:1]:
        for row in range(rows):
            header = df[column][row].strip()
            if header:
                if not re.search(r"(\:|\?|\#)$", header):
                    temp_rows = []
                    temp_row_index = []
                    # print('header---->', {header})
                    try:
                        if (re.search(r"(\:|\?|\#)$", df[column][row + 1].strip()) or "(yes/no)" in df[column][row + 1].lower()) and (re.search(r"(\:|\?|\#)$", df[column][row - 1].strip()) or not df[column][row-1].strip()):
                            temp_row_index.append(row)
                            temp_rows.append(df[column][row])
                            # print(df[column][row])
                            temp_row_index.append(row + 1)
                            temp_rows.append(df[column][row + 1])
                            # print(df[column][row + 1])
                    except:
                        temp_rows.clear()
                        temp_row_index.clear()
                        pass
                    for _row in temp_row_index:
                        df[column][_row] = " ".join(temp_rows)
    return df

def cleaning_sub_texts(text):
    if re.search(r"^\(.*\)\.?$", text):
        # print(text)
        return ""
    else:
        return text

def check_nan(text):
    if not text.strip():
        return np.nan
    else:
        return text

def is_certification_or_nutrition(df):
    rows, columns = df.shape
    for column in range(columns):
        for row in range(rows):
            header = df[column][row].strip()
            if header:
                if 'kosher' in header.lower():
                    return 'CERTIFICATIONS'
                elif 'serving size' in header.lower():
                    return 'NUTRITION'
    return 'None'

def certifications_processing(df):
    certifications_dict = {}
    certification_regex = {
        'ORGANIC CERTIFICATION': "organic",'KOSHER CERTIFICATION':"kosher",'GLUTEN FREE CERTIFICATION':'gluten',
        'FAIR TRADE CERTIFICATION': 'fair', 'NON-GMO CERTIFICATION':'non-gmo',
        '3rd PARTY LABELLING CERTIFICATION':'certification:'
    }
    rows, columns = df.shape
    for column in range(columns):
        for row in range(rows):
            header = df[column][row].lower().strip()
            for regex_key , re_pattern in certification_regex.items():
                if re_pattern in header:
                    for _col in range(columns)[column+1:]:
                        value = df[_col][row].strip()
                        if value:
                            # print(header, value)
                            certifications_dict[regex_key] = [{'en':value}]
                            break
    return certifications_dict

def ffill_block_strategy(df):
    # print("inside ffill block strategy-----**********")
    rows , columns = df.shape
    for column in range(columns)[:1]:
        for row in range(rows):
            if pd.isna(df[column][row]):
                try:
                    if isinstance(df[column+1][row-1],str):
                        if df[column+1][row-1].lower().strip() in ['n/a','no']:
                            df[column][row] = "@@@"
                    else:
                        pass
                except:
                    pass
    return df

def convert_for_bfill_strategy(text):
    if text == "@@@":
        return np.nan
    else:
        return text

def nutrition_processing(df):
    print('inside nutrition processing')
    nutrition_dict = {}
    rows, columns = df.shape
    for column in range(columns)[:1]:
        for row in range(rows):
            header = df[column][row].lower().strip()
            if header:
                for _col in range(columns)[1:]:
                    value = df[_col][row].strip()
                    if value:
                        value_header = 'PDV' if "%" in value else "Value"
                        if 'added' in header and 'sugars' in header:
                            header = 'added sugar'
                        if 'serving size' in header:
                            value = value.replace(" ", "")
                            if header in nutrition_dict:
                                nutrition_dict['serving size'].append(value)
                            else:
                                nutrition_dict['serving size'] = [value]
                            continue
                        if 'varied' in header:
                            if header in nutrition_dict:
                                nutrition_dict['varied'].append(value)
                            else:
                                nutrition_dict['varied'] = [value]
                            continue
                        if re.search(r"\d",value):
                            value = value.replace(" ", "")
                            if header in nutrition_dict:
                                nutrition_dict[header].append({value_header:{'en':value}})
                            else:
                                nutrition_dict[header] = [{value_header:{'en':value}}]
    return nutrition_dict

def normal_content_processing(df):
    content_dict = {}
    whole_list = []
    groups = df.groupby([0]).groups
    rows, columns = df.shape
    for key, value in groups.items():
        temp_list = []
        output = albertson_classifier(key)
        output_class = output['output']
        output_probability = output['probability']
        # print(key,output)
        if output_probability > 0.70 and output_class not in ('None'):
            for row_index in list(value):
                for column in range(columns)[1:]:
                    cell_value = df[column][row_index]
                    if cell_value.strip():
                        temp_list.append(cell_value)
            final_content = '\n'.join(temp_list)
            print('final_conten------------t',final_content)
            if re.search(r"\b\.\s([A-Z\/\s]*:)",final_content,re.MULTILINE):
                final_content = re.sub(r"\b\.\s([A-Z\/\s]*:)", lambda pat: "**" + pat.group(1), final_content, re.MULTILINE)
                final_content = final_content.replace('\n',' ').replace('**','\n')
            else:
                pass
            whole_list.append(final_content.strip().lower())
            # if output_class == "NET_CONTENT_STATEMENT" and not final_content.strip():
            if final_content.strip():
                if output_class in content_dict:
                    content_dict[output_class].append({'en':final_content})
                else:
                    content_dict[output_class] = [{'en':final_content}]
            # print(f'{output_class}------->{final_content}')
    return content_dict , whole_list

def albertson_classifier(text):
    import os
    model_location = "".join((document_location,"albertson_model.pkl"))
    dataset_location = "".join((document_location,"albertson_dataset.xlsx"))
    if os.path.exists(model_location):
        classifier = joblib.load(model_location)
    else:
        dataframe = pd.read_excel(dataset_location,engine='openpyxl')
        x_train_laser = laser.embed_sentences(dataframe['text'], lang='en')
        classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750, random_state=0,shuffle=True)
        classifier.fit(x_train_laser, dataframe['category'])
        joblib.dump(classifier,model_location)
    prediction = classifier.predict(laser.embed_sentences([text], lang='en'))
    probability = classifier.predict_proba(laser.embed_sentences([text], lang='en'))
    probability[0].sort()
    max_probability = max(probability[0])
    if max_probability > 0.70:
        pred_output = prediction[0]
    else:
        pred_output = 'None'
    return {'probability': max_probability, 'output': pred_output}

def get_smb_or_local(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                with open(input_pdf_location,'wb') as pdf:
                    pdf.write(f.read())
            print('file found')
        except:
            pass
            # raise Exception('File is being used by another process / smb not accessible')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location+input_pdf

def get_overall_content(input_pdf,page):
    plumber_pdf = pdfplumber.open(input_pdf)
    page = plumber_pdf.pages[int(page)-1]
    tables = page.extract_tables()
    table_list = [content.strip() for table in tables for t_list in table for content in t_list if len(str(content).split()) >= 3]
    return table_list

def albertson_main(file,pages):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    final_dict = {}
    overall_content_list = []
    input_pdf = get_smb_or_local(file,input_pdf_location)
    pages = pages
    pdfplumber_pdf = pdfplumber.open(input_pdf)
    for page in pages.split(','):
        print(f'{page}')
        if int(page) - 1 in range(len(pdfplumber_pdf.pages)):
            page_dict = {}
            tables = camelot.read_pdf(input_pdf, pages=page, flavor='stream', row_tol=12, edge_tol=500)
            no_of_tables = len(tables)
            chunked_df = {}
            for table_no in range(no_of_tables):
                chunk_index_list = []
                chunk = {}
                df = tables[table_no].df
                rows, columns = df.shape
                for column in range(columns):
                    for row in range(rows):
                        search_query = df[column][row]
                        for title, regex_pattern in title_card_dict.items():
                            if re.search(r"{}".format(regex_pattern), search_query, re.I):
                                # print(search_query)
                                chunk_index_list.append({'title': title, 'index': row})
                            else:
                                chunk_index_list.append({'title': 'NO TITLE', 'index': 0})
                # chunk_index_list = sorted(chunk_index_list,key = lambda x: x['index'])
                chunk_index_list = sorted(
                    list({frozenset(list_element.items()): list_element for list_element in chunk_index_list}.values()),
                    key=lambda d: d['index'])
                for index, title_index_dict in enumerate(chunk_index_list):
                    # print(title_index_dict)
                    try:
                        chunk[title_index_dict['title']] = [title_index_dict['index'],
                                                            chunk_index_list[index + 1]['index']]
                    except:
                        chunk[title_index_dict['title']] = [title_index_dict['index']]
                for title, chunk_list in chunk.items():
                    # print(chunk_list)
                    try:
                        temp_df = df.loc[chunk_list[0]:chunk_list[1] - 1]
                        temp_df = temp_df.reset_index(drop=True)
                        rows, columns = temp_df.shape
                        if columns > 2:
                            out = is_certification_or_nutrition(temp_df)
                            # print('output---------->', out)
                            if out not in ['None']:
                                title = out
                            else:
                                pass
                        chunked_df[title] = temp_df
                    except:
                        temp_df = df.loc[chunk_list[0]:]
                        temp_df = temp_df.reset_index(drop=True)
                        rows, columns = temp_df.shape
                        if columns > 2:
                            out = is_certification_or_nutrition(temp_df)
                            # print('output---------->', out)
                            if out not in ['None']:
                                title = out
                            else:
                                pass
                                # temp_df = temp_df.drop([0],axis='columns')
                                # temp_df.columns = range(temp_df.shape[1])
                        chunked_df[title] = temp_df
            for df_title, dataframe in chunked_df.items():
                if df_title not in ["COMPANY CONTACT INFORMATION", "NUTRITION","NUTRITION_SERVING", "CERTIFICATIONS"]:
                    rows, columns = dataframe.shape
                    if columns >= 2 and rows > 1:
                        # dataframe preprocessing
                        df_pro = dataframe.applymap(cleaning_unwanted_titles)
                        df_pro = cleaning_unwanted_headers(df_pro)
                        df_pro = noise_removal_1(df_pro)
                        df_pro = df_pro.applymap(cleaning_sub_texts)
                        df_pro = noise_removal_2(df_pro)
                        df_pro = df_pro.applymap(check_nan)
                        df_pro = df_pro.dropna(axis=1, how='all')
                        df_pro = df_pro.dropna(axis=0, how='all')
                        df_pro.columns = range(df_pro.shape[1])
                        df_pro = df_pro.reset_index(drop=True)
                        df_pro = ffill_block_strategy(df_pro)
                        df_pro[0].fillna(method='ffill', axis=0, inplace=True)
                        df_pro = df_pro.applymap(convert_for_bfill_strategy)
                        df_pro[0].fillna(method='bfill', axis=0, inplace=True)
                        df_pro[0].fillna(method='ffill', axis=0, inplace=True)
                        df_pro.fillna('', inplace=True)
                        content_dict , content_list = normal_content_processing(df_pro)
                        overall_content_list.extend(content_list)
                        if page != '1':
                            plumber_content_list = get_overall_content(input_pdf,page)
                            plumber_content_list = list(set(plumber_content_list))
                            unmapped_element = []
                            for plumber_content in plumber_content_list:
                                _, plumb_score = process.extract(plumber_content.lower(), overall_content_list, scorer=fuzz.partial_token_set_ratio)[0]
                                _, plumb_score1 = process.extract(plumber_content.lower(), overall_content_list, scorer=fuzz.ratio)[0]
                                # print(plumber_content,plumb_score)
                                if (plumb_score < 90) or (plumb_score > 90 and plumb_score1 < 70):
                                    unmapped_element.append(plumber_content)
                            # unmapped_element = list(set(plumber_content_list)-set(content_list))
                            for content in unmapped_element:
                                output = base('general', model_location).prediction(content)
                                print(output)
                                if output['output'] in ['ingredients']:
                                    if 'INGREDIENTS_DECLARATION' in content_dict:
                                        content_dict['INGREDIENTS_DECLARATION'].append({'en':content})
                                    else:
                                        content_dict['INGREDIENTS_DECLARATION'] = [{'en':content}]
                                else:
                                    if 'unmapped' in content_dict:
                                        content_dict['unmapped'].append({'en':content})
                                    else:
                                        content_dict['unmapped'] = [{'en':content}]
                            # print('****' * 5)
                            # print('unmapped element----->',unmapped_element)
                            # print('content list----->',content_list)
                            # print('plumber content list-------->',plumber_content_list)
                            # print('*******' * 6)

                        page_dict = {**page_dict, **content_dict}
                    else:
                        pass
                else:
                    rows, columns = dataframe.shape
                    if columns >= 2 and rows >= 1:
                        # if df_title == "NUTRITION":
                        if "NUTRITION" in df_title:
                            nutrition_data = nutrition_processing(dataframe)
                            try:
                                if 'serving size' in page_dict:
                                    page_dict['serving size'].append({'en':nutrition_data['serving size'][0]})
                                else:
                                    page_dict['serving size'] = [{'en':nutrition_data['serving size'][0]}]
                                nutrition_data.pop('serving size',None)
                            except:
                                pass
                            try:
                                if 'varied' in page_dict:
                                    page_dict['varied'].append({'en':nutrition_data['varied'][0]})
                                else:
                                    page_dict['varied'] = [{'en':nutrition_data['varied'][0]}]
                                nutrition_data.pop('varied',None)
                            except:
                                pass
                            if nutrition_data:
                                if 'NUTRITION_FACTS' in page_dict:
                                    page_dict['NUTRITION_FACTS'].append(nutrition_data)
                                else:
                                    page_dict['NUTRITION_FACTS'] = [nutrition_data]
                            # print(nutrition_data)
                        elif df_title == "CERTIFICATIONS":
                            # print('inside certification')
                            df_pro = dataframe.applymap(cleaning_unwanted_titles)
                            df_pro = cleaning_unwanted_headers(df_pro)
                            df_pro = noise_removal_1(df_pro)
                            df_pro = df_pro.applymap(cleaning_sub_texts)
                            df_pro = noise_removal_2(df_pro)
                            df_pro = df_pro.applymap(check_nan)
                            df_pro = df_pro.dropna(axis=1, how='all')
                            df_pro = df_pro.dropna(axis=0, how='all')
                            df_pro.columns = range(df_pro.shape[1])
                            df_pro = df_pro.reset_index(drop=True)
                            df_pro[0].fillna(method='ffill', axis=0, inplace=True)
                            df_pro[0].fillna(method='bfill', axis=0, inplace=True)
                            df_pro.fillna('', inplace=True)
                            certification_data = certifications_processing(df_pro)
                            page_dict = {**page_dict, **certification_data}
            final_dict[page] = page_dict
    try:
        temp_directory.cleanup()
    except:
        pass
    return final_dict
