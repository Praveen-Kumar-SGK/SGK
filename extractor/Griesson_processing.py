from .excel_processing import *
from bidi.algorithm import get_display
from collections import OrderedDict
import string

nutrition_value_check = r"^\d{0,2}\,?\d{0,3}\s{1,2}(g|kj|kcal|mg)"
nutrition_pdv_check = r""

copy_elements_fixed = ["Country of Origin","usage instruction","address","shelf_life_statement","storage instruction","allergen statement","ingredients","warning statement"]

def griesson_processing(dictionary):
    nutrition_value_column = []
    nutrition_header_column = []
    nutrition_pdv_column = []
    unmapped_set = set()
    copy_elements = set()
    languages = set()
    max_nutrition_row = 0
    Nutrition_columns = {}
    Nutrition_dict = {}
    final_dict = {}
    griesson_body = dictionary
    nutrition_other_mode_check = 0
    nutrition_aws_mode = 0
    nutrition_manual_mode = 0
    print(griesson_body)
    try:
        if "modifyData" in griesson_body:
            return griesson_body["modifyData"]
        if "nutrition_data" in griesson_body:
            if "tf_nutrition" in griesson_body["nutrition_data"][0]:
                nutrition_other_mode_check = 1
                if isinstance(griesson_body["nutrition_data"][0]['tf_nutrition'][0],str):
                    nutrition_aws_mode = 1
                key_variable = list(griesson_body["nutrition_data"][0]['tf_nutrition'][0].keys())[0]
                print("key_variable--------->",key_variable)
                if not key_variable.isnumeric():
                    print('manual format')
                    nutrition_manual_mode = 1
                    xx = []
                    for index, dictionary in enumerate(griesson_body["nutrition_data"][0]['tf_nutrition']):
                        d = {}
                        for key, value in dictionary.items():
                            d['1'] = key
                            for ind, val in enumerate(value):
                                d[ind + 2] = val
                        xx.append(d)
                    print(f'xxxx----->{xx}')
                    nutrition_response = nutrition_data_processing(xx, method='manual')
                else:
                    print('semi-textract format')
                    nutrition_response = nutrition_data_processing(griesson_body["nutrition_data"][0]['tf_nutrition'])
                    nutrition_aws_mode = 1
                    # return {'status': '0','nutrition':nutrition_response}
                if nutrition_response and 'Nutrition' not in final_dict:
                    final_dict['Nutrition'] = nutrition_response
        griesson_body.pop('nutrition_data',None)
    except:
        pass
    for layer , layer_data_list in griesson_body.items():
        for data_dict in layer_data_list:
            for text_frame_no , data in data_dict.items():
                cleaned_data = text_preprocessing(data)
                print(get_display(f"{text_frame_no}------>{cleaned_data}"))
                prediction = classifier(cleaned_data)
                output_class = prediction['output']
                output_probability = prediction['probability']
                if output_probability > 0.70:
                    if 'Nutrition' in output_class:
                        if nutrition_other_mode_check == 0:
                            if len(data.split('\r')) > max_nutrition_row:
                                max_nutrition_row = len(data.split('\r'))
                            if output_class in Nutrition_columns:
                                Nutrition_columns[output_class].append(data.split('\r'))
                            else:
                                Nutrition_columns[output_class] = [data.split('\r')]
                        # Nutrition_column_list.append(data.split('\r'))
                    elif output_class not in ['None','Others','design instruction']:
                        try:
                            # lang = lang_detect(data)
                            lang = google_language_detection(data)
                        except:
                            lang = classify(data)[0]
                        # lang = language_detection(data)
                        print('language detection----->',lang,'------>',data)
                        copy_elements.add(output_class)                         # record all elements
                        languages.add(lang)                                     # record all languages
                        if output_class in final_dict:
                            final_dict[output_class].append({lang:data})
                        else:
                            final_dict[output_class] = [{lang:data}]
                    else:
                        pass
                else:
                    if 'vitamin' in data.lower() and 'niacin' in data.lower() and output_class == 'None' and nutrition_other_mode_check == 0:
                        Nutrition_columns.clear()
                        nutrition_other_mode_check = 1
                    else:
                        try:
                            if re.search(nutrition_value_check, cleaned_data):
                                print(cleaned_data)
                                print(f'nutrition value column data--------->{data}')
                                nutrition_value_column.append(data)
                                continue
                            nutri_out = base('ferrero_header', ferrero_header_model).prediction(get_display(cleaned_data.split('/')[0].strip()))
                            nutri_class = nutri_out['output']
                            nutri_probability = nutri_out['probability']
                            if nutri_class not in ['None','header'] and nutri_probability > 0.80:
                                print(f'nutrition header column data--------->{data}')
                                nutrition_header_column.append(nutri_class)
                                continue
                            unmapped_set.add(data)
                        except:
                            pass
    print(f'nutrition value column--------->{nutrition_value_column}')
    print(f'nutrition header column--------->{nutrition_header_column}')
    try:
        if (nutrition_header_column) and (nutrition_value_column or nutrition_pdv_column) and ('Nutrition' not in final_dict):
            nutrition_temp_dict = {}
            nutrition_value_column_copy = [value for value in nutrition_value_column if '100' not in value][::-1]
            nutrition_split_index = [index for index, value in enumerate(nutrition_value_column_copy) if 'kj' in value.lower()]
            nutrition_temp_value = []
            nutrition_length_list = []
            for index, split_index in enumerate(nutrition_split_index):
                try:
                    _nutrition_value_col = nutrition_value_column_copy[split_index:nutrition_split_index[index + 1]]
                    nutrition_temp_value.append(_nutrition_value_col)
                    nutrition_length_list.append(len(_nutrition_value_col))
                    print(nutrition_value_column_copy[split_index:nutrition_split_index[index + 1]])
                    print('-------' * 4)
                except:
                    _nutrition_value_col = nutrition_value_column_copy[split_index:]
                    nutrition_length_list.append(len(_nutrition_value_col))
                    nutrition_temp_value.append(nutrition_value_column_copy[split_index:])
                    print(nutrition_value_column_copy[split_index:])
                    print('-------' * 4)
            nutrition_length , nutrition_header_column_copy,nutrition_pdv_column_copy = None,None,None
            if len(set(nutrition_length_list)) == 1:
                nutrition_length = list(set(nutrition_length_list))[0]
            if nutrition_length:
                nutrition_header_column_start_index = nutrition_header_column.index('Energy')
                nutrition_header_column = nutrition_header_column[:nutrition_header_column_start_index+1]
                nutrition_header_column_copy = list(OrderedDict.fromkeys(nutrition_header_column[::-1][:nutrition_length+1]))
                nutrition_pdv_column_copy = nutrition_pdv_column[::-1][:nutrition_length]
            else:
                pass
            if nutrition_header_column_copy:
                if len(nutrition_header_column_copy) == nutrition_length:
                    for nutrition_list in nutrition_temp_value:
                        for index, value in enumerate(nutrition_list):
                            header = nutrition_header_column_copy[index]
                            if header in nutrition_temp_dict:
                                nutrition_temp_dict[header].append({'Value':{'en':value}})
                            else:
                                nutrition_temp_dict[header] = [{'Value':{'en':value}}]
            print(f'nutrition value column copy--------->{nutrition_value_column_copy}')
            print(f'nutrition header column copy--------->{nutrition_header_column_copy}')
            print(f'nutrition table--------->{nutrition_temp_dict}')
            if 'Nutrition' not in final_dict and nutrition_temp_dict:
                final_dict['Nutrition'] = nutrition_temp_dict
    except:
        pass
    for value in unmapped_set:
        output_class = 'Unmapped'
        try:
            # lang = lang_detect(value)
            lang = google_language_detection(value)
        except:
            lang = classify(value)[0]
        if output_class in final_dict:
            final_dict[output_class].append({lang : value})
        else:
            final_dict[output_class] = [{lang : value}]
    print(unmapped_set)
    '''checking all the columns is of same length , 
    if not make equal by prepending empty string in the columns'''
    Nutrition_columns = is_nutrition_table_columns_equal(Nutrition_columns,max_nutrition_row)
    print(f'nutrition column------->{Nutrition_columns}')

    nutrition_form_check = True    # nutrition cannot form table when it is not in correct shape
    if Nutrition_columns and ('Nutrition' not in final_dict):
        if 'Nutrition header column' in Nutrition_columns:
            for nutrition_index , nutrition_title in enumerate(Nutrition_columns['Nutrition header column'][0]):
                if nutrition_title:
                    nutrition_header = re.sub(r'\((.*?)\)|\[.*?\]|\<(.*?)\>', '', str(nutrition_title))
                    nutrition_header = re.sub(r'\w\$\d', '', nutrition_header)
                    nutrition_header = nutrition_header.split('/')[0].strip()
                    key = base('ferrero_header', ferrero_header_model).prediction(get_display(nutrition_header))['output']
                    if key not in ['None']:
                        pass
                    else:
                        key = nutrition_header
                    for column_name, columns in Nutrition_columns.items():
                        for column in columns:
                            if "header" not in column_name and key != "header":
                                if len(re.findall(r"(g|%|mg|msg|kj\/kcal)",str(column[nutrition_index]))) > 1:
                                    nutrition_form_check = False
                                if column[nutrition_index].strip():
                                    if 'Value' in column_name:
                                        if key in Nutrition_dict:
                                            Nutrition_dict[key].append({'Value': {'en': column[nutrition_index]}})
                                        else:
                                            Nutrition_dict[key] = [{'Value': {'en': column[nutrition_index]}}]
                                    elif 'PDV' in column_name:
                                        if key in Nutrition_dict:
                                            Nutrition_dict[key].append({'PDV': {'en': column[nutrition_index]}})
                                        else:
                                            Nutrition_dict[key] = [{'PDV': {'en': column[nutrition_index]}}]
    if Nutrition_dict and 'Nutrition' not in final_dict and nutrition_form_check:
        final_dict['Nutrition'] = Nutrition_dict

    if 'ingredients' in final_dict:
        ingredients_seperated = []
        for lang_data_dict in final_dict['ingredients']:
            for lang , data in lang_data_dict.items():
                # data = data.replace('\r', '\n')
                data = data.replace('\r', '.#')
                data = re.sub(r"(\.)(?!org)",'.#',data)
                # data = data.replace('\r','\n').replace('.','.#')
                # for sentence in re.split(r"(?<=\.)",data):
                for sentence in data.split('#'):
                    if sentence.strip():
                        _pred = classifier(sentence)
                        _class = _pred['output']
                        _probability = _pred['probability']
                        if _class in ['None','ingredients']:
                            ingredients_seperated.append(sentence)
                        else:
                            try:
                                # lang = lang_detect(sentence)
                                lang = google_language_detection(sentence)
                            except:
                                lang = classify(sentence)[0]
                            languages.add(lang)                                         # record all languages
                            copy_elements.add(_class)                                   # record all elements
                            if "b$0" in sentence and "b$1" not in sentence:
                                sentence = "".join((sentence, "b$1"))
                            elif "b$1" in sentence and "b$0" not in sentence:
                                sentence = "".join(("b$0", sentence))
                            if _class in final_dict:
                                final_dict[_class].append({lang:sentence})
                                ingredients_seperated.append(sentence)
                            else:
                                final_dict[_class] = [{lang:sentence}]
                                ingredients_seperated.append(sentence)
                # final_dict['ingredients'] = [{lang:''.join(ingredients_seperated)}]
    # print(final_dict)
    # print('-------' * 5)
    # print(Nutrition_columns)
    # print('--------' * 5)
    # print("copy_elements---------------->",list(copy_elements))
    # print("languages---------------->",list(languages))
    final_dict = lang_group_dic(final_dict,['ingredients','storage instruction','warning statement','shelf_life_statement'])
    final_dict["languages"] = list(languages)
    # final_dict["copyElements"] = list(copy_elements)
    final_dict["copyElements"] = list(set(copy_elements_fixed)-copy_elements)
    if nutrition_aws_mode == 1 or nutrition_other_mode_check:
        return {**{'status':'0'},**{"modifyData":final_dict}}
    if nutrition_manual_mode == 1:
        return final_dict
    if 'Nutrition' not in final_dict or len(final_dict["Nutrition"]) < 5:
        return {'status':'0'}

    return {**{'status':'0'},**{"modifyData":final_dict}}

def is_nutrition_table_columns_equal(nutrition_dict,max_rows):
    modified_dict = {}
    for column_name , columns in nutrition_dict.items():
        for column in columns:
            if len(column) == max_rows:
                print(f'{column_name} is equal')
                if column_name in modified_dict:
                    modified_dict[column_name].append(column)
                else:
                    modified_dict[column_name] = [column]
            else:
                print(f'{column_name} is not equal')
                difference = max_rows-len(column)
                new_column = column
                for _ in range(difference):
                    new_column.insert(0,'')
                if column_name in modified_dict:
                    modified_dict[column_name].append(column)
                else:
                    modified_dict[column_name] = [column]
    return modified_dict


def text_preprocessing(text):
    text = str(text)
    text = text.lower()
    text = text.replace('\r','\n')
    text = re.sub(r"\w\$\d","",text)
    # text = re.sub(r'[^\w\s]','',text)
    # text = re.sub(r"\(.*\)|\[.*\]","",text)
    text = text.replace('(','').replace(')','')
    text = re.sub(r"\[.*\]","",text)
    return text.strip()


def lang_group_dic(dictionary, spec_category):
    final_dic = {}
    for key, value in dictionary.items():
        if key in spec_category:
            dic = {}
            for list_dic in value:
                for lang, txt in list_dic.items():
                    # if "b$0" in txt and "b$1" not in txt:
                    #     txt = "".join((txt,"b$1"))
                    # elif "b$1" in txt and "b$0" not in txt:
                    #     txt = "".join(("b$0",txt))
                    if lang in dic:
                        dic[lang].append(txt)
                    else:
                        dic[lang] = [txt]
            else:
                for lang, text_list in dic.items():
                    joined_text = " ".join(text_list)
                    try:
                        lang = google_language_detection(joined_text)
                    except:
                        lang = classify(joined_text)[0]
                    if key in final_dic:
                        final_dic[key].append({lang: joined_text.strip()})
                    else:
                        final_dic[key] = [{lang: joined_text.strip()}]
        else:
            if key != 'Nutrition':
                for list_dict in value:
                    for lang, txt in list_dict.items():
                        if key in final_dic:
                            final_dic[key].append({lang: txt.strip()})
                        else:
                            final_dic[key] = [{lang: txt.strip()}]
            else:
                if key in final_dic:
                    final_dic[key].append(value)
                else:
                    final_dic[key] = value

    print(final_dic)
    return final_dic

def classifier(text):
    if os.path.exists(griesson_model_location):
        model = joblib.load(griesson_model_location)
    else:
        print('model training')
        df = pd.read_excel(griesson_model_dataset, engine='openpyxl')
        df = df.sample(frac=1)
        list_text = df['text'].tolist()
        preprocessed_text = []
        for text in list_text:
            preprocessed_text.append(text_preprocessing(text))
        df['cleaned_text'] = preprocessed_text
        # X_train_laser = laser.embed_sentences(df['text'], lang='en')
        X_train_laser = laser.embed_sentences(df['cleaned_text'], lang='en')
        model = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
                              random_state=0, shuffle=True)
        model.fit(X_train_laser, df['category'])
        joblib.dump(model, griesson_model_location)
    prediction = model.predict(laser.embed_sentences([text], lang='en'))
    probability = model.predict_proba(laser.embed_sentences([text], lang='en'))
    probability[0].sort()
    max_probability = max(probability[0])
    if max_probability > 0.65:
        pred_output = prediction[0]
    else:
        pred_output = 'None'
    print(text)
    print({'probability': max_probability, 'output': pred_output})
    print('----------'*5)
    return {'probability': max_probability, 'output': pred_output}


def nutrition_data_processing(input_list,method=None):
    print(input_list)
    nutrition_dict = {}
    nutrition_dict_exception = {}
    for nutrition_row_dict in input_list:
        nutrition_header_original = nutrition_row_dict["1"]
        nutrition_header = nutrition_row_dict["1"].split('/')[-1].strip()
        if nutrition_header and len(nutrition_row_dict) > 1:
            if method == "manual":
                nutri_probability = 1
                nutri_class = nutrition_header
            else:
                nutrition_header = re.sub(r"(g|mg|kj|kcal|mcg|\/)*\b","",nutrition_header.lower())
                nutri_out = base('ferrero_header', master_nutrition_model_location).prediction(get_display(nutrition_header))
                nutri_class = nutri_out['output']
                nutri_probability = nutri_out['probability']
                print(nutrition_header,'------>',nutri_class)
            nutrition_row_dict.pop('1',None)
            if nutrition_row_dict:
                if nutri_class not in ['None', 'header','Nutrition information'] and nutri_probability > 0.80:
                    for index , value in nutrition_row_dict.items():
                        header = 'PDV' if "%" in value else 'Value'
                        value = value.strip()
                        if not value:     # textract null value and value with header fix
                            for regex_value in re.finditer(r"\d{0,}?\,?\d{0,}?\s{0,1}?(g|mg|kj|kcal|mcg)\/?(g|mg|kj|kcal|mcg)?",nutrition_header_original,re.I):
                                if re.search(r"\d",str(regex_value.group())):
                                    value = (regex_value.group()).strip()
                                    break
                        if value.strip():
                            if nutri_class in nutrition_dict:
                                nutrition_dict[nutri_class].append({header:{'en':value}})
                            else:
                                nutrition_dict[nutri_class] = [{header:{'en':value}}]
                elif nutri_class not in ['header','Nutrition information'] and len(nutrition_header) > 5:
                    print("else statement ra")
                    nutrition_header = re.sub(r"(g|mg|kj|kcal|mcg|\/)*\b", "", nutrition_header.lower())
                    if nutrition_header.lower() not in ("vitamine") and not re.search(r"\d",nutrition_header):
                    # if nutrition_header.lower() not in ("vitamine"):
                        nutri_class = nutrition_header
                    else:
                        continue
                    for index , value in nutrition_row_dict.items():
                        header = 'PDV' if "%" in value else 'Value'
                        value = value.strip()
                        if not value:     # textract null value and value with header fix
                            for regex_value in re.finditer(r"\d{0,}?\,?\d{0,}?\s{0,1}?(g|mg|kj|kcal|mcg)\/?(g|mg|kj|kcal|mcg)?",nutrition_header_original,re.I):
                                if re.search(r"\d",str(regex_value.group())):
                                    value = (regex_value.group()).strip()
                                    break
                        if value.strip():
                            if nutri_class in nutrition_dict_exception:
                                nutrition_dict_exception[nutri_class].append({header:{'en':value}})
                            else:
                                nutrition_dict_exception[nutri_class] = [{header:{'en':value}}]
    print(nutrition_dict)

    if len(nutrition_dict) <= 3:
        nutrition_dict.clear()
    else:
        nutrition_dict = {**nutrition_dict,**nutrition_dict_exception}
    return nutrition_dict

# def language_detection(text):
#     text = re.sub(r'[^\w\s]', '', text).strip()
#     text = text.replace('\n',' ')
#     if text:
#         fastext_probability = language_model.predict_pro(text)[0]
#         if fastext_probability[1] > 0.70 or fastext_probability[0] in ['en']:
#             return fastext_probability[0]
#         else:
#             classify_language = classify(text)[0]
#             return classify_language
#     else:
#         return 'en'

from .utils import GoogleTranslate
def google_language_detection(text):
    text = re.sub(r'[^\w\s]', '', text).strip()
    text = text.replace('\n',' ')
    if text:
        return 'en'
        # return classify(text)[0]
        # with GoogleTranslate(text) as output:
        #     lang = output["language"]
        #     return lang
    else:
        return 'en'

