

import re
import joblib
from langid import classify
from .excel_processing import *
from dataclasses import dataclass, field

# ---------------------------------------------------------------------------------------------------------------------
# Loading model
classifier = joblib.load(mondelez_cep_model_loc)
# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Mondelez_CEP_Template():
    splt_parameter: str = r"\.\r|\. |\.\t|\:\s|\.b\$1"

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
    def dict_to_list(self, dictionary):
        final_list = []
        for key, value in dictionary.items():
            #print(value)
            for data_dict in value:
                for text_frame_no,txt in data_dict.items():
                    item = re.sub(str(self.splt_parameter), lambda pat: pat.group()+"*#", txt, flags=re.M)
                    item = str(item).split("*#")
                    for k in item:
                        if k.strip():
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
        return value
    # -----------------------------------------------------------------------------------------------------------------
    def final_dict(self, txt_list, classifier, probability=0.75, unwanted_txt_len=4, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):
        copy_elements_fixed = ["Country of Origin", "usage instruction", "address", "shelf_life_statement",
                               "NET_CONTENT_STATEMENT",
                               "storage instruction", "allergen statement", "ingredients", "ingredients claim",
                               "warning statement",
                               "COPYRIGHT_TRADEMARK_STATEMENT", "MARKETING_CLAIM", "OTHER_INSTRUCTIONS",
                               "CONTACT_INFORMATION", "DISCLAIMER", "WEBSITE", "DESIGN_INSTRUCTIONS"]
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
                matches = matches = ['kj', 'толе', 'tel', 'кдж']

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

            if txt.startswith('b$1'):
                txt = txt.split('b$1', 1)[1]
            if 'b$1' in txt or "b$0" in txt:
                temp = []
                for items in txt.split("\r"):
                    temp.append(self.bold_tag_close(items) + '\r')

                x = "".join(temp)
                value = self.bold_tag_close(x)
            else:
                value = self.bold_tag_close(txt)
            value = self.bold_tag_close(txt)
            lang = self.language_detection(cleaned_txt, language)
            copy_elements.add(classified_output)
            languages.add(lang)
            if value.strip():
                gen_cate_dic.setdefault(classified_output, []).append({lang: value})
        gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    # -----------------------------------------------------------------------------------------------------------------
    def mondelez_cep_main(self, dic):
        if "modifyData" in dic:
            return dic["modifyData"]
        txt_list = self.dict_to_list(dic)
        output_dic = self.final_dict(txt_list, classifier)
        return {**{'status': '0'}, **{"modifyData": output_dic}}

# ---------------------------------------------------------------------------------------------------------------------