import re
import joblib
from langid import classify
from .excel_processing import *
from dataclasses import dataclass, field
from dateutil.parser import parse

# ----------------------------------------------------------------------------------------
# Loading model

classifier = joblib.load(listerine_cep_model_loc)


# ------------------------------------------------------------------------------------------------

@dataclass
class Listerine_CEP_Template:
    splt_parameter: str = r"\.[\r\n]|\.\t| - |\. [\r\n]|. _ |.  "

    def text_preprocessing(self, text, replace_tup=()):
        text = str(text)
        for txt in replace_tup:
            text = text.replace(txt, "")

        text = text.lower()
        text = text.replace('\r', ' ').replace("\t", "")
        text = re.sub(r"\w\$\d", "", text)
        text = text.replace('(', '').replace(')', '')
        text = re.sub(r"\[.*\]", "", text)
        return text.strip()

    def dict_to_list(self, dictionary):
        final_list = []
        for key, value in dictionary.items():
            # print(value)
            for data_dict in value:
                for text_frame_no, txt in data_dict.items():
                    item = re.sub(str(self.splt_parameter), lambda pat: pat.group() + "*#", txt, flags=re.M)
                    item = str(item).split("*#")
                    for k in item:
                        if k.strip():
                            final_list.append(k.strip())
        return final_list

    def language_detection(self, value, language=None):  # lang Module need to update
        if language == "google translate":
            lang = "gt"  # need to integrate
        elif language == "whatlangid":
            lang = "wl"  # need to integrate
        else:
            lang = classify(value)[0]
        return lang

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

    def bold_tag_close(self, value):
        value = value.strip()
        value = self.bold_sequence(value)
        if "b$0" in value and "b$1" not in value:
            value = "".join((value, "b$1"))
        elif "b$1" in value and "b$0" not in value:
            value = "".join(("b$0", value))
        if "i$0" in value and "i$1" not in value:
            value = "".join((value, "i$1"))
        elif "i$1" in value and "i$0" not in value:
            value = "".join(("i$0", value))
        return value
    
    def is_date(self, string, fuzzy=False):
        try: 
            parse(string, fuzzy=fuzzy)
            return True
        except ValueError:
            return False

    def final_dict(self, txt_list, classifier, probability=0.80, unwanted_txt_len=3, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):
        copy_elements_fixed = ["ADDRESS", "COUNTRY OF ORIGIN", "DESIGN_INSTRUCTIONS", "INGREDIENTS",
                               "LOT_NUMBER", "MARKETING_CLAIM", "NET CONTENT", "OPENING_INSTRUCTIONS",
                               "OTHER_INSTRUCTIONS", "RECYCLE_STATEMENT", "USAGE INSTRUCTION",
                               "WARNING STATEMENT"]

        key_replace_list = ()

        gen_cate_dic = {}
        languages = set()
        copy_elements = set()
        for txt in txt_list:
            cleaned_txt = self.text_preprocessing(txt, key_replace_list)
            if len(cleaned_txt) > 0:
                num_of_alphabets = sum(1 for char in cleaned_txt if char.isalpha())
                num_of_numbers = sum(1 for char in cleaned_txt if char.isdigit())
                
                if cleaned_txt[0].isdigit() and cleaned_txt.endswith('ml') and len(cleaned_txt) <= 6:
                    classified_output = "net content"
                elif cleaned_txt[0].isdigit() and cleaned_txt.endswith('mm') and len(cleaned_txt) <= 8:
                    classified_output = "DESIGN_INSTRUCTIONS"
                elif len(cleaned_txt)<13 and self.is_date(cleaned_txt)==True:
                    classified_output="Unmapped"
                elif (num_of_alphabets <5) or (num_of_numbers >= num_of_alphabets):
                    classified_output="Unmapped"
                else:
                    if len(cleaned_txt) > int(unwanted_txt_len):
                        classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                        probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))[0]
                        probability1.sort()
                        proba = probability1[-1]
                        if proba > probability:
                            classified_output = classified_output[0]
                        elif proba > 0.60 and proba <= probability:
                            classified_output = "OTHER_INSTRUCTIONS"
                            # print("text****",cleaned_txt,"probali****",proba,"output******",classified_output)
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

            lang = self.language_detection(cleaned_txt, language)
            copy_elements.add(classified_output)
            languages.add(lang)
            if value not in ["b$0 b$1", "b$0b$1", "b$0*b$1", "•", "b$0.b$1", "b$0َb$1"] and value.strip():
                if classified_output == "Unmapped":
                    gen_cate_dic.setdefault(classified_output, []).append({lang: value})
                else:
                    gen_cate_dic.setdefault(classified_output.upper(), []).append({lang: value})
        # gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
        gen_cate_dic["copyElements"] = copy_elements_fixed
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    def listerine_cep_main(self, dic):
        if "modifyData" in dic:
            return dic["modifyData"]
        txt_list = self.dict_to_list(dic)
        output_dic = self.final_dict(txt_list, classifier)
        return {**{'status': '0'}, **{"modifyData": output_dic}}
        # ------------------------------------------------------------------------------------------------