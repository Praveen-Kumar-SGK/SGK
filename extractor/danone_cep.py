import re
import joblib
from langid import classify
from .excel_processing import *
from dataclasses import dataclass,field
from dateutil.parser import parse
from sklearn.neural_network import MLPClassifier
from sklearn.metrics.pairwise import cosine_similarity
from bidi.algorithm import get_display
from .utils import GoogleTranslate , get_gs1_elements

# -------------------------------------------------------------------------------------------
model_location = danone_cep_model_loc
# -------------------------------------------------------------------------------------------

nutri_table_available = False
@dataclass
class Danone_CEP_Template():
    
    splt_parameter : str = r"\. \n|\.\n|\.    \n|\n\#"
    
    def text_preprocessing(self, text, replace_tup=()):
        text = str(text)
        for txt in replace_tup:
            text = text.replace(txt, "")

        text = text.lower()
        text = text.replace('\r' ,' ').replace("\t" ,"")
        text = re.sub(r"\w\$\d" ,"" ,text)
        text = text.replace('(' ,'').replace(')' ,'')
        text = re.sub(r"\[.*\]" ,"" ,text)
        return text.strip()
 
    # -------------------------------------------------------------------------------------------
    
    def is_nutrition_table_available(self, text):

        nutri_header = ['nutritional value','კვებითი ღირებულება','nutrition value','nutrition']
        text = re.sub(r'\d','',text)
        text = re.sub(r'\b\D{1}\b', '', text)
        similarity = cosine_similarity(laser.embed_sentences(text, lang='en'),
                                       laser.embed_sentences(nutri_header, lang='en').mean(0).reshape(1, 1024))[0][0]
        # print("**********",text,"&&&&&&&&&&&&",similarity)
        if similarity > 0.8:
            return True
        else:
            return False
    # -------------------------------------------------------------------------------------------
    
    def dict_to_list(self, dictionary):
        final_list = []
        global nutri_table_available
        for key, value in dictionary.items():
            for data_dict in value:
                for text_frame_no, txt in data_dict.items():
                    item = re.sub(str(self.splt_parameter), lambda pat: pat.group() + "*#", txt, flags=re.M) ## For applying into multi line content
                    item = str(item).split("*#")
                    itms = []
                    for itm in item:
                        itms.extend(str(itm).split("\r"))

                    for k in itms:
                        if k.strip():
                            if self.is_nutrition_table_available(self.text_preprocessing(k.split("/")[0])):
                                nutri_table_available = True
                            final_list.append(k.strip())
        return final_list
    # --------------------------------------------------------------------------------------------    
    
    def language_detection(self, value, language=None):  # lang Module need to update
        if language == "google translate":
            lang = "gt"  # need to integrate
        elif language == "whatlangid":
            lang = "wl"  # need to integrate
        else:
            lang = classify(value)[0]
        return lang

    def bold_sequence(self,text):
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

    def italian_sequence(self,text):
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
    # --------------------------------------------------------------------------------------------    
    
    def is_date(self, string, fuzzy=False):
        try:
            parse(string, fuzzy=fuzzy)
            return True
        except ValueError:
            return False
    # --------------------------------------------------------------------------------------------
    # Loading model
    def load_model(model_location):
        return joblib.load(model_location)

    def final_dict(self, txt_list, model_location, probability=0.70, unwanted_txt_len=6, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):
        

        copy_elements_fixed = ["ADDRESS", "COPYRIGHT_TRADEMARK_STATEMENT", "DESIGN_INSTRUCTIONS",
                               "LOCATION_OF_ORIGIN", "INGREDIENTS_DECLARATION", "MARKETING_CLAIM",
                                "OTHER_INSTRUCTIONS", "SERVING_SIZE", "STORAGE_INSTRUCTIONS",
                               "USAGE_INSTRUCTIONS", "WARNING_STATEMENTS","Unmapped"]

        classifier = load_model(model_location)
        gen_cate_dic = {}
        languages = set()
        copy_elements = set()
        for txt in txt_list:
            cleaned_txt = self.text_preprocessing(txt, key_replace_list)
            if len(cleaned_txt) > int(unwanted_txt_len):
                if "made in new zealand" in cleaned_txt.lower():
                    classified_output = "LOCATION_OF_ORIGIN"
                elif (cleaned_txt.isdigit() and len(cleaned_txt)<=15):
                    classified_output = "Unmapped"
                elif cleaned_txt.endswith('.PDF'):
                    classified_output = "Unmapped"     
                elif cleaned_txt[0].isdigit() and cleaned_txt[-2].isalpha() and cleaned_txt[-1].isdigit():
                    classified_output = "Unmapped"
                elif len(cleaned_txt) < 13 and self.is_date(cleaned_txt) == True:
                    classified_output = "Unmapped"
                else:
                    classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                    probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))[0]
                    probability1.sort()
                    proba = probability1[-1]
                    if proba > float(probability):
                        classified_output = classified_output[0]                    
                    elif proba > 0.50 and proba <= probability:
                            classified_output = "OTHER_INSTRUCTIONS"       
                    else:
                        classified_output = below_thres_class
    #                         print("text****",cleaned_txt,"probali****",prob1,"output******",classified_output)
    #                         print("**************************")
            else:
                classified_output = "Unmapped"


            value = self.bold_sequence(txt)
            value = self.italian_sequence(value)
            lang = self.language_detection(cleaned_txt, language)
            copy_elements.add(classified_output)
            languages.add(lang)
            
            if value not in ["b$0 b$1", "b$0b$1", "b$0*b$1", "•", "b$0.b$1"] and value.strip():
                if classified_output == "Unmapped":
                    gen_cate_dic.setdefault(classified_output, []).append({lang: value})
                else:
                    gen_cate_dic.setdefault(classified_output.upper(), []).append({lang: value})
                    
        #gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
        gen_cate_dic["copyElements"] = list(set(get_gs1_elements()) - copy_elements)
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic
    # --------------------------------------------------------------------------------------------
    
    def nutrition_data_processing(self, input_list, method=None):
        # print(input_list)
        nutrition_dict = {}
        nutrition_dict_exception = {}
        for nutrition_row_dict in input_list:
            nutrition_header_original = nutrition_row_dict["1"]
            # nutrition_header = nutrition_row_dict["1"].split('/')[-1].strip()
            nutrition_header = str(sorted(nutrition_row_dict["1"].split("/"), key=len, reverse=True)[0]).strip()
            if nutrition_header and len(nutrition_row_dict) > 1:
                if method == "manual":
                    nutri_probability = 1
                    nutri_class = nutrition_header
                else:
                    nutrition_header = re.sub(r"(g|mg|kj|kcal|mcg|\/)*\b", "", nutrition_header.lower())
                    nutri_out = base('ferrero_header', master_nutrition_model_location).prediction(get_display(nutrition_header))
                    nutri_class = nutri_out['output']
                    nutri_probability = nutri_out['probability']
                    print(nutrition_header, '------>', nutri_class)
                nutrition_row_dict.pop('1', None)
                if nutrition_row_dict:
                    if nutri_class not in ['None', 'header', 'Nutrition information'] and nutri_probability > 0.60:
                        for index, value in nutrition_row_dict.items():
                            header = 'PDV' if "%" in value else 'Value'
                            value = value.strip()
                            if not value:  # textract null value and value with header fix
                                for regex_value in re.finditer(
                                        r"\d{0,}?\,?\d{0,}?\s{0,1}?(g|mg|kj|kcal|mcg)\/?(g|mg|kj|kcal|mcg)?",
                                        nutrition_header_original, re.I):
                                    if re.search(r"\d", str(regex_value.group())):
                                        value = (regex_value.group()).strip()
                                        break
                            if value.strip():
                                if nutri_class in nutrition_dict:
                                    nutrition_dict[nutri_class].append({header: {'en': value}})
                                else:
                                    nutrition_dict[nutri_class] = [{header: {'en': value}}]
                    elif nutri_class not in ['header', 'Nutrition information'] and len(nutrition_header) > 2:
                        # print("else statement ra")
                        nutrition_header = re.sub(r"(g|mg|kj|kcal|mcg|\/)*\b", "", nutrition_header.lower())
                        if nutrition_header.lower() not in ("vitamine") and not re.search(r"\d", nutrition_header):
                            # if nutrition_header.lower() not in ("vitamine"):
                            nutri_class = nutrition_header
                        else:
                            continue
                        for index, value in nutrition_row_dict.items():
                            header = 'PDV' if "%" in value else 'Value'
                            value = value.strip()
                            if not value:  # textract null value and value with header fix
                                for regex_value in re.finditer(
                                        r"\d{0,}?\,?\d{0,}?\s{0,1}?(g|mg|kj|kcal|mcg)\/?(g|mg|kj|kcal|mcg)?",
                                        nutrition_header_original, re.I):
                                    if re.search(r"\d", str(regex_value.group())):
                                        value = (regex_value.group()).strip()
                                        break
                            if value.strip():
                                if nutri_class in nutrition_dict_exception:
                                    nutrition_dict_exception[nutri_class].append({header: {'en': value}})
                                else:
                                    nutrition_dict_exception[nutri_class] = [{header: {'en': value}}]
        # print(nutrition_dict)

        if len(nutrition_dict) <= 3:
            nutrition_dict.clear()
        else:
            nutrition_dict = {**nutrition_dict, **nutrition_dict_exception}
        return nutrition_dict
    
    # --------------------------------------------------------------------------------------------

    def danone_cep_main(self, dic):
        output_dic = {}
        nutrition_aws_mode = 0
        nutrition_manual_mode = 0
        nutrition_availability = 0
        global nutri_table_available
        nutri_table_available = False
        if "modifyData" in dic:
            return dic["modifyData"]
        if "nutrition_data" in dic:
            if "tf_nutrition" in dic["nutrition_data"][0]:
                nutrition_availability = 1
                if dic["nutrition_data"][0]['tf_nutrition']:
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
                            nutrition_response = self.nutrition_data_processing(xx, method='manual')
                        else:
                            # print('semi-textract format')
                            nutrition_response = self.nutrition_data_processing(
                                dic["nutrition_data"][0]['tf_nutrition'])
                            nutrition_aws_mode = 1
                    except:
                        nutrition_response = {}
                        # return {'status': '0','nutrition':nutrition_response}
                    if nutrition_response and 'Nutrition' not in output_dic:
                        output_dic['Nutrition'] = nutrition_response
        dic.pop('nutrition_data', None)
        txt_list = self.dict_to_list(dic)
        output_dic = {**self.final_dict(txt_list, model_location=model_location), **output_dic}
        # print(output_dic)
        if nutrition_aws_mode == 1 or not nutri_table_available or nutrition_availability:
            return {**{'status': '0'}, **{
                "modifyData": output_dic}}  # Status "0" goes to CEP for edit option else go to tornado for xml generation
        elif nutrition_manual_mode == 1:
            return output_dic
        # return {**{'status':'0'}, **{"modifyData":output_dic}}
        # if not nutri_table_available:
        #     return {**{'status':'0'}, **{"modifyData":output_dic}}
        else:
            return {'status': '0'}
    # --------------------------------------------------------------------------------------------