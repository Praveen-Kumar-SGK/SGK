import mammoth
from bs4 import BeautifulSoup
from functools import partial
from bidi.algorithm import get_display
from .excel_processing import *
from sklearn.metrics.pairwise import cosine_similarity
from termcolor import colored
from textblob import TextBlob

# GM_HD_model_dataset = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/GM_HD_headers_dataset.xlsx"
# GM_HD_model_location = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/GM_HD_model.pkl"
# ferrero_model_location = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/ferrero_header_model.pkl"

# ip_docx = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/HD_M7 Belgian Chocolate Hazelnut 100ml_PS 8261249 ACS0220_kl1.docx"
# ip_docx = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/HD_M7 Dark Chocolate & Caramelized Almonds 100ml_PS 8261255 ACS0220_kl1.docx"
# ip_docx = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/HD_ P2 Dark Chocolate & Caramelized Almond 460ML_PS 8251496 ACS0620_KL1.docx"

'''
new_unwanted_txt = ["Trademark Statement\n(English)","Package Structure Tracking Number","Consumer Guarantee/Consumer Contact Information\n(English)",
                    "Best Before \n(English)","Disclaimer\n(English)"]
'''

new_unwanted_txt_cleaned = ["Trademark Statement","Package Structure Tracking Number","Consumer Guarantee/Consumer Contact Information",
                    "Best Before","Disclaimer"]

header_memory = ""

def docx_to_html(file):
    print('entering docx to html')
    if file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                html = mammoth.convert_to_html(f).value
                # print(html)
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                html = mammoth.convert_to_html(f).value
                print('file found')
        finally:
            smbclient.reset_connection_cache()
    else:
        print('local file')
        file = document_location + file
        html = mammoth.convert_to_html(file).value
    return html

def docx_to_table(input_file):
    html = docx_to_html(input_file)
    # html = mammoth.convert_to_html(input_file).value
    soup = BeautifulSoup(html,"html.parser")
    for tables in soup.find_all('table'):
        for table in tables:
            row_values = []
            for row in table.find_all('tr'):
                column_values = []
                for column in row.find_all('td'):
                    if column.text.strip():
                        column_values.append(column.text)
                else:
                    if column_values:
                        row_values.append(column_values)
            else:
                if row_values:
                    df = pd.DataFrame(row_values)
                    # if df.shape[0] < 13:
                    if df.shape[0] < 20:
                        # print('---' * 10)
                        yield row_values

def docx_to_table2(input_file):
    html = docx_to_html(input_file)
    # html = mammoth.convert_to_html(input_file).value
    soup = BeautifulSoup(html,"html.parser")
    for tables in soup.find_all('table'):
        for table in tables:
            row_values = []
            for row in table.find_all('tr'):
                column_values = []
                for column in row.find_all('td'):
                    if column.text.strip():
                        if not column_values:
                            column_values.append(column.text)
                        else:
                            column = str(column)
                            column = column.replace("</p>","</p>&&")
                            # column = column.replace('<strong>', '&lt;b&gt;').replace('</strong>', '&lt;/b&gt;')
                            column = re.sub(r"<(\/?br\/?)>", "&&", column)
                            column = re.sub(r"\^(.*?)\^","",column,flags=re.M).strip()
                            column = column.replace("&&","\n").strip()
                            column = BeautifulSoup(column,"html.parser")
                            # print("hhhhhhhhh-------->",column.text)
                            # column = re.sub(r"<(.*?)>","",column).strip()
                            # column = re.sub(r"\^.*?\^","",column).strip()
                            column = column.text.strip()
                            column = str(column).replace("<", "&lt;").replace(">", "&gt;")

                            column_values.append(column)
                else:
                    if column_values:
                        row_values.append(column_values)
            else:
                if row_values:
                    df = pd.DataFrame(row_values)
                    # if df.shape[0] < 13:
                    if df.shape[0] < 26:
                        # print('---' * 10)
                        yield row_values

def classifier(model_location,text):
    if os.path.exists(model_location):
        model = joblib.load(model_location)
    else:
        print('model training')
        df = pd.read_excel(GM_HD_model_dataset, engine='openpyxl')
        df = df.sample(frac=1)
        list_text = df['text'].tolist()
        preprocessed_text = []
        for text in list_text:
            preprocessed_text.append(text_preprocessing(text))
        df['cleaned_text'] = preprocessed_text
        X_train_laser = laser.embed_sentences(df['cleaned_text'], lang='en')
        model = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
                              random_state=0, shuffle=True)
        model.fit(X_train_laser, df['category'])
        joblib.dump(model, model_location)
    prediction = model.predict(laser.embed_sentences([text], lang='en'))
    probability = model.predict_proba(laser.embed_sentences([text], lang='en'))
    probability[0].sort()
    max_probability = max(probability[0])
    if max_probability > 0.65:
        pred_output = prediction[0]
    else:
        pred_output = 'None'

    print('----------'*5)
    print(text)
    print({'probability': max_probability, 'output': pred_output})
    print('----------'*5)
    return {'probability': max_probability, 'output': pred_output}

def GM_header_classifier(model_location,model_dataset,text):
    if os.path.exists(model_location):
        model = joblib.load(model_location)
    else:
        print('model training')
        df = pd.read_excel(model_dataset, engine='openpyxl')
        df = df.sample(frac=1)
        list_text = df['text'].tolist()
        preprocessed_text = []
        for text in list_text:
            preprocessed_text.append(text_preprocessing(text))
        df['cleaned_text'] = preprocessed_text
        X_train_laser = laser.embed_sentences(df['cleaned_text'], lang='en')
        model = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
                              random_state=0, shuffle=True)
        model.fit(X_train_laser, df['category'])
        joblib.dump(model, model_location)
    prediction = model.predict(laser.embed_sentences([text], lang='en'))
    probability = model.predict_proba(laser.embed_sentences([text], lang='en'))
    probability[0].sort()
    max_probability = max(probability[0])
    if max_probability > 0.65:
        pred_output = prediction[0]
    else:
        pred_output = 'None'
    print('----------'*5)
    print("text----------->",text,"--------->",{'probability': max_probability, 'output': pred_output})
    print('----------'*5)
    return {'probability': max_probability, 'output': pred_output}

def text_preprocessing(text):
    text = str(text)
    text = text.lower()
    text = text.replace('\r','\n')
    # text = re.sub(r'[^\w\s]','',text)
    # text = re.sub(r"\(.*\)|\[.*\]","",text)
    text = text.replace('(','').replace(')','')
    text = re.sub(r"\[.*\]","",text)
    return text

# def is_nutrition_table(table : list) -> str:
#     nutrition_table_detector = partial(classifier,griesson_model_location)
#     table_text = " ".join([text.strip() for list in table for text in list])
#     # output = base('general', model_location).prediction(get_display(table_text))['output']
#     output = nutrition_table_detector(table_text)['output']
#     return output

def is_nutrition_table_or_not(texts):
    for text in texts:
        print("text_checking------>",text)
        if not text.strip():
            continue
        text = text.split('/')[0] if text.split('/')[0].strip() else text.split('/')[1]
        text = re.sub(r"\(.*\)","",text).lower()
        text = re.sub(r"[^\w\s]","",text).lower()
        table_check = ['nutrition information', 'nutrition information typical values', 'nutrition declaration','Valeurs nutritionnelles moyennes']
        similarity = 0
        if isinstance(text,str) and 'rdt' not in text:
            similarity = cosine_similarity(laser.embed_sentences(text, lang='en'),
                                           laser.embed_sentences(table_check, lang='en').mean(0).reshape(1, 1024))[0][0]
            print('*******' * 5)
            print(text, '----->', similarity)
            print('*******' * 5)
            if similarity > 0.80:
                return True
            else:
                continue
    else:
        return False

# import re
# is_nutrition_table_or_not('Nutrition Facts')

# def nutrition_table_processing_old(table:list) -> dict:
#     nutrition_dict = {}
#     df = pd.DataFrame(table)
#     rows, columns = df.shape
#     if 'nutrition information' in str(df[0][0]).lower() and "rdt" in str(df[0][0]).lower():
#         for column in range(columns)[:1]:
#             for row in range(rows):
#                 nutrition = str(df[column][row]).split('/')[0].strip()
#                 print(f"data--------->{nutrition}")
#                 nutrition_detection = partial(classifier,ferrero_model_location)
#                 output = nutrition_detection(get_display(nutrition))
#                 key = output['output']
#                 probability = output['probability']
#                 print(f'{nutrition}-------->{key}----------->{probability}')
#                 if key not in ['None','nutrition_table_reference']:
#                     for _col in range(columns)[1:]:
#                         nutri_value = df[_col][row]
#                         if nutri_value:
#                             nutri_value = str(nutri_value).strip()
#                             if key in nutrition_dict:
#                                 if '%' in str(df[_col][row]):
#                                     nutrition_dict[key].append({'PDV':{'en':nutri_value}})
#                                 else:
#                                     nutrition_dict[key].append({'Value':{'en':nutri_value}})
#                             else:
#                                 if '%' in str(df[_col][row]):
#                                     nutrition_dict[key] = [{'PDV':{'en':nutri_value}}]
#                                 else:
#                                     nutrition_dict[key] = [{'Value':{'en':nutri_value}}]
#         return  nutrition_dict

def nutrition_table_processing(table:list) -> dict:
    print('Inside Nutrition table processing')
    nutrition_dict = {}
    df = pd.DataFrame(table)
    rows, columns = df.shape
    # print('inside nutrition table processing')
    # if 'nutrition information' in str(df[0][0]).lower() and "rdt" in str(df[0][0]).lower():
    if len(table) > 2:
        text_to_check = [table[0][0], table[1][0]]
    else:
        text_to_check = [table[0][0]]
    print("text_to_cjeck--------->",text_to_check)
    if is_nutrition_table_or_not(text_to_check):
        print('nutrition_table_found')
        # print(df)
        for _column in range(columns)[:1]:
            for _row in range(rows)[:5]:
                val = str(df[_column][_row])
                if 'serving' in val.lower() and re.search(r'\d',val.lower()):
                    if "NUMBER_OF_SERVINGS_PER_PACKAGE" in nutrition_dict:
                        nutrition_dict["NUMBER_OF_SERVINGS_PER_PACKAGE"].append({'en': val})
                    else:
                        nutrition_dict["NUMBER_OF_SERVINGS_PER_PACKAGE"] = [{'en': val}]
        if any("%" in value and "*" not in value for value in df[0].to_list()):
            df = df.iloc[:, ::-1]
            df.columns = range(df.shape[1])
            print('inverted df')
            # print(df)
        for column in range(columns)[:1]:
            for row in range(rows):
                nutrition_original = df[column][row]
                if isinstance(nutrition_original,str) and str(nutrition_original).strip():
                    nutrition_original = str(df[column][row])
                else:
                    if isinstance(df[column+1][row],str) and str(nutrition_original).strip():
                        nutrition_original = str(df[column+1][row])
                    else:
                        continue
                nutrition = nutrition_original.split('/')[0].strip()
                print("original nutrition------>",nutrition)
                # nutrition = re.sub(r"[^A-Za-z\s]","",nutrition)
                # if 'serving' in nutrition.lower():
                #     if "serving information" in nutrition_dict:
                #         nutrition_dict["serving information"].append({'en': nutrition_original})
                #     else:
                #         nutrition_dict["serving information"] = [{'en': nutrition_original}]
                #     continue
                # print(f"data--------->{nutrition}")
                # nutrition_detection = partial(classifier,ferrero_model_location)
                # output = nutrition_detection(get_display(nutrition))
                # output = base('ferrero_header', ferrero_header_model).prediction(get_display(nutrition),method='labse')
                output = base('ferrero_header', ferrero_header_model_gm).prediction(get_display(nutrition))
                key = output['output']
                probability = output['probability']
                print(f'{nutrition}-------->{key}----------->{probability}')
                if probability > 0.60:
                    if key in ['nutrition_table_reference']:
                        nutrition_dict[key] = {'en': nutrition_original}
                    elif key not in ['None','nutrition_table_reference','header',"Nutrition information"]:
                        remaining_cells_in_row = df.loc[row][1:].to_list()
                        remaining_cell_join_text = " ".join((text for text in remaining_cells_in_row if text))
                        print(f"listttttt join--------->{remaining_cell_join_text}")
                        for value in re.finditer(r"(less than)?\s?\d{0,4}?\.?,?\d{0,2}?\D{0,4}?\s?\(?(mg|g|kcal|kj|%|-)\)?\/?(mg|g|kcal|kj|%|-)?",remaining_cell_join_text,re.I):
                        #for value in re.finditer(r"\d{0,4}?\.?\d{0,2}?\s?(mg|g|kcal|kj|%|-)\/?(mg|g|kcal|kj|%|-)?",remaining_cell_join_text,re.I):
                            value = str(value.group()).strip()
                            print('value---inside----->',value)
                            if not re.search(r"\d",value):
                                continue
                            if value:
                                # value_header = 'PDV' if any("%" in _val for _val in df.iloc[:,column].to_list() if isinstance(_val,str) and str(_val).strip()) else "Value"
                                value_header = 'PDV' if "%" in value else "Value"
                                if key in nutrition_dict:
                                    nutrition_dict[key].append({value_header: {'en': value}})
                                else:
                                    nutrition_dict[key] = [{value_header: {'en': value}}]
        # print(nutrition_dict)
    return  nutrition_dict

def normal_table_processing(table:list) -> dict:
    global header_memory
    print('inside normal table processing')
    normal_dict = {}
    df = pd.DataFrame(table)
    # print(df)
    rows, columns = df.shape
    print("rows-------->",rows)
    print("columns-------->",columns)
    if columns > 1 and columns <= 25:
        for column in range(columns)[:1]:
            for row in range(rows):
                # print(df[column][row])
                header = str(df[column][row])
                # print('header_memory------>',header_memory)
                if df[column+1][row] and ":" not in header:
                    if re.search(r"^\(.*\)$",header.strip()) and header_memory and header_memory != 'None':
                        header = header_memory
                        # print(header,'------->',df)
                    # header_cleaned = re.sub(r"\(.*\)","",header).split('/')[0].strip()
                    header_cleaned = re.sub(r"\(.*\)","",header).strip()
                    header_cleaned = header_cleaned.replace("RDT","")
                    normal_detection = partial(GM_header_classifier,GM_HD_model_location,GM_HD_model_dataset)
                    if header_cleaned:
                        output = normal_detection(get_display(header_cleaned))
                        output_class = output['output']
                        header_memory = header
                        probability = output['probability']
                        print(f'{header_cleaned}-----{output_class}-------{probability}')
                        if output_class and probability > 0.70:
                            # if output_class == "NET_CONTENT_STATEMENT":
                            #     print(table)
                            #     print('----' * 5)
                            if str(df[column+1][row]).strip() and re.sub(r"\(.*\)","",str(df[column+1][row])).strip() not in new_unwanted_txt_cleaned:
                                value = df[column+1][row]
                                if isinstance(value,str):
                                    value = str(df[column+1][row]).strip()
                                    value = text_cleaning(value).strip()
                                    if value:
                                        try:
                                            lang = custom_language_detection(value)
                                        except:
                                            lang = classify(value)[0]
                                        if output_class in normal_dict:
                                            normal_dict[output_class].append({lang: value})
                                        else:
                                            normal_dict[output_class] = [{lang: value}]
    return normal_dict

def main(input_docx):
    final_dict = {}
    nutrition_final_dict = {}
    for table in docx_to_table2(input_docx):
        print(table)
        # output = is_nutrition_table(table)
        if len(table) > 2:
            text_to_check = [table[0][0],table[1][0]]
        else:
            text_to_check = [table[0][0]]
        print('first_object------->',text_to_check)
        # output = is_nutrition_table_or_not(table[0][0])
        # if output == "Nutrition":              # Nutrition table processing
        if is_nutrition_table_or_not(text_to_check):              # Nutrition table processing
            print("getting into nutrition table processing")
            nutrition_information = nutrition_table_processing(table)
            # print(nutrition_information)
            if 'nutrition_table_reference' in nutrition_information:
                if 'nutrition_table_reference' in final_dict:
                    final_dict['nutrition_table_reference'].append(nutrition_information['nutrition_table_reference'])
                else:
                    final_dict['nutrition_table_reference'] = [nutrition_information['nutrition_table_reference']]
                nutrition_information.pop('nutrition_table_reference',None)
            if 'NUMBER_OF_SERVINGS_PER_PACKAGE' in nutrition_information:
                if 'NUMBER_OF_SERVINGS_PER_PACKAGE' in final_dict:
                    final_dict['NUMBER_OF_SERVINGS_PER_PACKAGE'].append(nutrition_information['NUMBER_OF_SERVINGS_PER_PACKAGE'][0])
                else:
                    final_dict['NUMBER_OF_SERVINGS_PER_PACKAGE'] = nutrition_information['NUMBER_OF_SERVINGS_PER_PACKAGE']
                nutrition_information.pop('NUMBER_OF_SERVINGS_PER_PACKAGE',None)
            if nutrition_information:
                if 'NUTRITION_FACTS' in nutrition_final_dict:
                    nutrition_final_dict['NUTRITION_FACTS'].append(nutrition_information)
                else:
                    nutrition_final_dict['NUTRITION_FACTS'] = [nutrition_information]
        elif "GDA" in str(table[0][0]):
            key = "NUTRITIONAL_CLAIM"
            try:
                value = str(table[0][1])
            except:
                continue
            if key in final_dict:
                final_dict[key].append({classify(value)[0]:value})
            else:
                final_dict[key] = [{classify(value)[0]:value}]
            continue
        else:
            normal_dictionary = normal_table_processing(table)
            for key , value in normal_dictionary.items():
                if key in final_dict:
                    final_dict[key].append(value[0])
                else:
                    final_dict[key] = value
    print(final_dict)
    # remove duplicates
    final_cleaned_dict = {}
    for category , value_list in final_dict.items():
        final_cleaned_dict[category] = list({frozenset(list_element.items()) : list_element for list_element in value_list}.values())
    # print('after cleaning---->',final_cleaned_dict)
    return {**nutrition_final_dict,**final_cleaned_dict}

def text_cleaning(text):
    unwanted_text = ['Country of Origin"^','/(in bold/)','NA','N/A','n/a','English Back Translation:','English Back Translation:n/a','English Back Translation:NA',
                     'new EU recycling logo.PNG< a >','English Back Translation:see english sentence','English Back Translation:see french field',
                     'Green dot registered.png< a >',' new EU recycling logo.PNG< a >','English Back Translation:see lead country','English Back Translation:See artwork',
                     'G17 Chocolate 2047032[1]-MGO-G531997A-2','NFP HD CHOCOLATE (MC)','M15 Chocolate - Nutri Info','GM logo.png< a >',
                     'tbc*','address^','icone vegetarienne.PNG< a >','*only new logo eco emballage in yellow box*','*only new logo eco emballage with following text in yellow box*',
                     'new EU recycling logo.PNG< a >','OR (if lack of space )','NA.bmp< a >','*Note: website already in the Generic English Information',
                    ]
    text = re.sub(r"\^[^\s].*?\^","",text,flags=re.M)
    text = re.sub(r"English Back Translation.*","",text,flags=re.I)
    text = re.sub(r"\([^)]*(font size).*\)","",text,flags=re.I|re.M)
    for text_pattern in unwanted_text:
        try:
            text = re.sub(r"{}\b".format(text_pattern),'',text.strip())
        except:
            text = text.replace(text_pattern,'')
    return text

# from langid.langid import LanguageIdentifier, model
# identifier = LanguageIdentifier.from_modelstring(model, norm_probs=True)

from .utils import GoogleTranslate
from .mongo_interface import MongoSearch
def custom_language_detection(text):
    # return classify(text)[0]
    language = MongoSearch(text=text,to_lang=None).detect_language()
    if language:
        return language
    with GoogleTranslate(text) as output:
        return output['language']

    # text_blob_result = TextBlob(text).detect_language()
    # print(colored(text, 'green'), '<------textblob-------->', colored(text_blob_result, 'magenta'))
    # return text_blob_result
    # fastext_probability = language_model.predict_pro(text)[0]
    # if fastext_probability[1] > 0.75:
    #     print(colored(text, 'green'), '-------->', colored(fastext_probability, 'yellow'))
    #     return fastext_probability[0]
    # classify_results = identifier.classify(text)
    # if classify_results[0] == fastext_probability[1] or classify_results[1] > 0.90:
    #     print(colored(text, 'green'), '-------->', colored(classify_results, 'blue'))
    #     return classify_results[0]
    # else:
    #     try:
    #         text_blob_result = TextBlob(text).detect_language()
    #         print(colored(text, 'green'), '<------textblob-------->', colored(text_blob_result, 'magenta'))
    #         return text_blob_result
    #     except:
    #         return fastext_probability[0]
