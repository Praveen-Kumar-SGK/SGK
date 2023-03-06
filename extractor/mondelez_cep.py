

import re
import joblib
from langid import classify
from .excel_processing import *
from dataclasses import dataclass, field
from sklearn.metrics.pairwise import cosine_similarity
from bidi.algorithm import get_display
# ---------------------------------------------------------------------------------------------------------------------
# Loading model
classifier = joblib.load(mondelez_cep_model_loc)
# ---------------------------------------------------------------------------------------------------------------------
nutri_table_available = False
@dataclass
class Mondelez_CEP_Template():
    # splt_parameter: str = r"\.\r|\. |\.\t|\:\s|\.b\$1"
    splt_parameter: str = r"\.[\r\n]|\. |\.\t|\:\s|\.b\$1"

    # -----------------------------------------------------------------------------------------------------------------
    def text_preprocessing(self, text, replace_tup=()):
        text = str(text)
        for txt in replace_tup:
            text = text.replace(txt, "")

        text = text.lower()
        text = text.replace('\r', ' ').replace("\t", "").replace('\xa0', '')
        text = re.sub(r"\w\$\d", "", text)
        text = text.replace('(', '').replace(')', '')
        text = re.sub(r"\[.*\]", "", text)
        return text.strip()

    # -----------------------------------------------------------------------------------------------------------------
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
    # -----------------------------------------------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------------------------------------------------
    def language_detection(self, value, language=None):
        if language == "google translate":
            lang = "gt"  # need to integrate
        elif language == "whatlangid":
            lang = "wl"  # need to integrate
        else:
            lang = classify(value)[0]
        return lang
    # -----------------------------------------------------------------------------------------------------------------
    def bold_tag_close(self, value):
        value = value.strip()
        if "b$0" in value and "b$1" not in value:
            value = "".join((value, "b$1"))
        elif "b$1" in value and "b$0" not in value:
            value = "".join(("b$0", value))
        if "i$0" in value and "i$1" not in value:
            value = "".join((value, "i$1"))
        elif "i$1" in value and "i$0" not in value:
            value = "".join(("i$0", value))
        # Texting having multiple bold tags
        if len(re.findall(r"b\$0", value)) > len(re.findall(r'b\$1', value)):
            value = value + 'b$1'
        elif len(re.findall(r"b\$0", value)) < len(re.findall(r'b\$1', value)):
            value = 'b$0' + value
        return value
        # ---------------------------------------------------------------------------------------------------------------------
    def bold_sequence(self, text):
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

    # -----------------------------------------------------------------------------------------------------------------
    def final_dict(self, txt_list, classifier, probability=0.75, unwanted_txt_len=4, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):
        copy_elements_fixed = ["COUNTRY OF ORIGIN", "USAGE INSTRUCTION", "ADDRESS",
                               "SHELF_LIFE_STATEMENT", "NET_CONTENT_STATEMENT", "STORAGE INSTRUCTION",
                               "ALLERGEN STATEMENT", "INGREDIENTS", "INGREDIENTS CLAIM",
                               "WARNING STATEMENT", "COPYRIGHT_TRADEMARK_STATEMENT", "MARKETING_CLAIM",
                               "OTHER_INSTRUCTIONS", "CONTACT_INFORMATION", "DISCLAIMER", "WEBSITE",
                               "DESIGN_INSTRUCTIONS"]
        gen_cate_dic = {}
        languages = set()
        copy_elements = set()

        for txt in txt_list:
            cleaned_txt = self.text_preprocessing(txt, key_replace_list)
            if len(cleaned_txt) > int(unwanted_txt_len):
                classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))[0]
                probability1.sort()
                proba = probability1[-1]

                # Elements required for conditions #
                word_count = [i.strip() for i in cleaned_txt.split(' ')]
                num_of_alphabets = sum(1 for char in cleaned_txt if char.isalpha())
                num_of_numbers = sum(1 for char in cleaned_txt if char.isdigit())
                matches  = ['kj', 'толе', 'tel', 'кдж']

                # Condition to filter nutrition names in multiple languages #
                if sum(1 for c in cleaned_txt if c == '/') >= 4 or sum(1 for c in cleaned_txt if c == ';') >= 4:
                    classified_output = "Unmapped"

                # Condition to filter single words or few words text having shorter word length #
                elif 'www.' not in cleaned_txt and '.com' not in cleaned_txt and classified_output[
                    0] != 'NET_CONTENT_STATEMENT' and (
                        len(word_count) < 4 or sum([True for word in word_count if len(word) >= 5]) < 2):
                    classified_output = "Unmapped"

                # Capturing the phone numbers #
                elif (num_of_alphabets <= 5 and num_of_numbers >= 8 and '%' not in cleaned_txt) or 'Հեռ' in cleaned_txt:
                    classified_output = "address"

                # Removing misclassified net content
                elif classified_output[0] == 'NET_CONTENT_STATEMENT' and (
                        len(cleaned_txt) < 15 or len(cleaned_txt) > 47 or proba < 0.9 or any(
                        [x in cleaned_txt for x in matches])):
                    classified_output = "Unmapped"


                else:
                    if proba > probability:
                        classified_output = classified_output[0]
                    elif proba > 0.50 and proba <= probability:
                        classified_output = "OTHER_INSTRUCTIONS"
                    else:
                        classified_output = below_thres_class

            else:
                classified_output = "Unmapped"

            value = self.bold_tag_close(txt)
            value = self.bold_sequence(value)
            lang = self.language_detection(cleaned_txt, language)
            copy_elements.add(classified_output)
            languages.add(lang)
            if value.strip():
                if classified_output == "Unmapped":
                    gen_cate_dic.setdefault(classified_output, []).append({lang: value})
                else:
                    gen_cate_dic.setdefault(classified_output.upper(), []).append({lang: value})
        # gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
        gen_cate_dic["copyElements"] = copy_elements_fixed
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    # -----------------------------------------------------------------------------------------------------------------
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

    # -----------------------------------------------------------------------------------------------------------------
    def mondelez_cep_main(self, dic):
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
        output_dic = {**self.final_dict(txt_list, classifier), **output_dic}
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

# ---------------------------------------------------------------------------------------------------------------------