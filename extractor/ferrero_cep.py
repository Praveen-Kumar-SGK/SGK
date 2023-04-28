from bidi.algorithm import get_display
from .excel_processing import *
from sklearn.metrics.pairwise import cosine_similarity
from .utils import GoogleTranslate , get_gs1_elements

# model_loc = r"/Users/sakthivel/Documents/SGK/Ferrero_CEP/dataset/ferrero_cep_model.sav"
# classifier = joblib.load(model_loc)

classifier = joblib.load(ferrero_cep_model_location)

# master_nutrition_model_location = r"/Users/sakthivel/Documents/SGK/Ferrero_CEP/dataset/master_nutrition.pkl"
nutri_table_available = False

def dict_to_list(dictionary):
    final_list = []
    global nutri_table_available
    for key, value in dictionary.items():
        for data_dict in value:
            for text_frame_no, txt in data_dict.items():
                # item = re.sub(r"\s{3,}|\.\r", lambda pat: pat.group()+"**", txt, flags=re.M)  ## For applying into multi line content
                item = re.sub(r"\s{3,}|\.[\r\n]", lambda pat: pat.group()+"**", txt, flags=re.M)  ## For applying into multi line content
                item = str(item).split("**")
                for k in item:
                    if k.strip():
                        if is_nutrition_table_available(text_preprocessing(k.split(":")[0])):
                            nutri_table_available = True
                        final_list.append(k.strip())
    return final_list

def text_preprocessing(text):
    text = str(text)
    text = text.lower()
    text = text.replace('\r',' ').replace("\t","")
    text = re.sub(r"\w\$\d","",text)
    # text = re.sub(r'[^\w\s]','',text)
    # text = re.sub(r"\(.*\)|\[.*\]","",text)
    text = text.replace('(','').replace(')','')
    text = re.sub(r"\[.*\]","",text)
    return text.strip()

def bold_sequence(text):
    tags = re.findall(r"b\$[01]", text, flags=re.M)
    temp_tags = tags.copy()
    index_to_ignore = []
    for index, tag in enumerate(temp_tags):
        if index not in index_to_ignore:
            if tag == "b$1" and index == 0:
                text = "".join(["b$0", text])
            elif tag == "b$0" and index == range(len(tags))[-1]:
                text = "".join([text, "b$1"])
            elif tag == "b$0" and temp_tags[index + 1] == "b$1":
                index_to_ignore.append(index + 1)
    return text

def italian_sequence(text):
    tags = re.findall(r"i\$[01]", text, flags=re.M)
    temp_tags = tags.copy()
    index_to_ignore = []
    for index, tag in enumerate(temp_tags):
        if index not in index_to_ignore:
            if tag == "i$1" and index == 0:
                text = "".join(["i$0", text])
            elif tag == "i$0" and index == range(len(tags))[-1]:
                text = "".join([text, "i$1"])
            elif tag == "i$0" and temp_tags[index + 1] == "i$1":
                index_to_ignore.append(index + 1)
    return text

def final_dict(txt_list):
    copy_elements_fixed = ["COUNTRY OF ORIGIN", "USAGE INSTRUCTION", "ADDRESS", "SHELF_LIFE_STATEMENT",
                           "STORAGE INSTRUCTION", "ALLERGEN STATEMENT", "INGREDIENTS", "WARNING STATEMENT",
                           "COPYRIGHT_TRADEMARK_STATEMENT", "MARKETING_CLAIM", "OTHER_INSTRUCTIONS",
                           "MARKETING_COPY", "FUNCTIONAL_NAME"]
    gen_cate_dic={}
    classified_output = None
    languages = set()
    copy_elements = set()
    for txt in txt_list:
        cleaned_txt = text_preprocessing(txt)
        if len(cleaned_txt) >10:
            classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]

            if prob1 > 0.80:
                classified_output = classified_output[0]
            elif prob1 > 0.60 and prob1 <=0.80:
                 classified_output = "OTHER_INSTRUCTIONS"
            else:
                classified_output = 'Unmapped'
            # print("text",cleaned_txt,"probali****",prob1,"output******",classified_output)
            # print("**************************")
        else:
                classified_output = 'Unmapped'

        value = txt.strip()
        value = bold_sequence(value)
        value = italian_sequence(value)
        if "b$0" in value and "b$1" not in value:
            value = "".join((value, "b$1"))
        elif "b$1" in value and "b$0" not in value:
            value = "".join(("b$0", value))
        if "i$0" in value and "i$1" not in value:
            value = "".join((value, "i$1"))
        elif "i$1" in value and "i$0" not in value:
            value = "".join(("i$0", value))
        lang = classify(cleaned_txt)[0]
        copy_elements.add(classified_output)
        languages.add(lang)
        if value not in ["b$0 b$1", "b$0b$1", "b$0*b$1", "•", "b$0.b$1", "b$0َb$1"] and value.strip():
            if classified_output == "Unmapped":
                gen_cate_dic.setdefault(classified_output, []).append({lang: value})
            else:
                gen_cate_dic.setdefault(classified_output.upper(), []).append({lang: value})
    gen_cate_dic,languages,copy_elements = ingre_split_dict(gen_cate_dic,languages,copy_elements)
    gen_cate_dic["copyElements"] = list(set(get_gs1_elements()) - copy_elements)
    # gen_cate_dic["copyElements"] = copy_elements_fixed
    gen_cate_dic["languages"] = list(languages)
    return gen_cate_dic

def nutrition_data_processing(input_list,method=None):
    # print(input_list)
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
                # print(nutrition_header,'------>',nutri_class)
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
                    # print("else statement ra")
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
    # print(nutrition_dict)

    if len(nutrition_dict) <= 3:
        nutrition_dict.clear()
    else:
        nutrition_dict = {**nutrition_dict,**nutrition_dict_exception}
    return nutrition_dict

def ingre_split_dict(dic,languages,copy_elements):
    final_dic = {}
    for key, value in dic.items():
        if key in ["INGREDIENTS","OTHER_INSTRUCTIONS"]:
            for cnt in value:
                for lang, txt in cnt.items():
                    # if key in ["ingredients", "OTHER_INSTRUCTIONS"]:
                    item = re.sub(r"\. ", lambda pat: pat.group()+"**", txt, flags=re.M)
                    splt_txt = item.split("**")
                    for final_text in splt_txt:
                        classified_output = classifier.predict(laser.embed_sentences(final_text, lang='en'))
                        probability1 = classifier.predict_proba(laser.embed_sentences(final_text, lang='en'))
                        probability1.sort()
                        prob1 = probability1[0][-1]
                        if prob1 > 0.80:
                            classified_output = classified_output[0]
                        elif prob1 > 0.60 and prob1 <= 0.80:
                            classified_output = "OTHER_INSTRUCTIONS"
                        else:
                            classified_output = 'Unmapped'
                        if "b$0" in final_text and "b$1" not in final_text:
                            final_text = "".join((final_text, "b$1"))
                        elif "b$1" in final_text and "b$0" not in final_text:
                            final_text = "".join(("b$0", final_text))
                        # print("text", final_text, "probali****", prob1, "output******", classified_output)
                        # print("**************************")
                        # lang = classify(final_text)[0]
                        copy_elements.add(classified_output)
                        languages.add(lang)
                        if classified_output in final_dic:
                            final_dic[classified_output].append({lang: final_text.strip()})
                        else:
                            final_dic[classified_output] = [{lang: final_text.strip()}]
        else:
            for cnt in value:
                if key in final_dic:
                    final_dic[key].append(cnt)
                else:
                    final_dic[key] = [cnt]

    return final_dic,languages,copy_elements

    

def is_nutrition_table_available(text):
#     print("**********",text)
    nutri_header = ['INFORMASI NILAI GIZI', 'nutrition information', 'nutrition information typical values',
                    'nutrition declaration']
    similarity = cosine_similarity(laser.embed_sentences(text, lang='en'),
                                   laser.embed_sentences(nutri_header, lang='en').mean(0).reshape(1, 1024))[0][0]
    # print("**********",text,"&&&&&&&&&&&&",similarity)
    if similarity > 0.80:
#         print("$$$$$$$"*4)
        return True
    else:
        return False


def ferrero_main(dic):
    output_dic ={}
    nutrition_aws_mode = 0
    nutrition_manual_mode = 0
    global nutri_table_available
    nutri_table_available = False
    if "modifyData" in dic:
        return dic["modifyData"]
    if "nutrition_data" in dic:
        if "tf_nutrition" in dic["nutrition_data"][0]:
            nutrition_other_mode_check = 1
            if isinstance(dic["nutrition_data"][0]['tf_nutrition'][0], str):
                nutrition_aws_mode = 1
            try:
                key_variable = list(dic["nutrition_data"][0]['tf_nutrition'][0].keys())[0]

                # print("key_variable--------->", key_variable)
                if not key_variable.isnumeric():
                    # print('manual format')
                    nutrition_manual_mode = 1
                    nutrition_aws_mode = 0
                    xx = []
                    for index, dictionary in enumerate(dic["nutrition_data"][0]['tf_nutrition']):
                        d = {}
                        for key, value in dictionary.items():
                            d['1'] = key
                            for ind, val in enumerate(value):
                                d[ind + 2] = val
                        xx.append(d)
                    # print(f'xxxx----->{xx}')
                    nutrition_response = nutrition_data_processing(xx, method='manual')
                else:
                    # print('semi-textract format')
                    nutrition_response = nutrition_data_processing(dic["nutrition_data"][0]['tf_nutrition'])
                    nutrition_aws_mode = 1
            except:
                nutrition_response = {}
                # return {'status': '0','nutrition':nutrition_response}
            if nutrition_response and 'Nutrition' not in output_dic:
                output_dic['Nutrition'] = nutrition_response
    dic.pop('nutrition_data', None)
    txt_list = dict_to_list(dic)
    output_dic = {**final_dict(txt_list), **output_dic}
    print(output_dic)
    if nutrition_aws_mode == 1 or not nutri_table_available:
        return {**{'status': '0'}, **{"modifyData": output_dic}} # Status "0" goes to CEP for edit option else go to tornado for xml generation
    elif nutrition_manual_mode == 1:
        return output_dic
    # return {**{'status':'0'}, **{"modifyData":output_dic}}
    # if not nutri_table_available:
    #     return {**{'status':'0'}, **{"modifyData":output_dic}}
    else:
        return {'status':'0'}

    
