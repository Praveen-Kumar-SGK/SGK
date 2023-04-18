
import re
import joblib
from langid import classify
# from .excel_processing import *
from dataclasses import dataclass ,field
from sklearn.neural_network import MLPClassifier
from laserembeddings import Laser
from .excel_processing import *

laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)
# model_loc = r"/Users/sakthivelv/Documents/SGK/Ascensia_CEP/Redmond_model.sav"
classifier = joblib.load(ascensia_cep_model_loc)


@dataclass
class Ascensia_CEP_Template:

    def text_preprocessing(self ,text, replace_tup=()):
        text = str(text)
        for txt in replace_tup:
            text = text.replace(txt, "")

        #         text = text.lower()
        text = text.replace('\r', ' ').replace("\t", "")
        text = re.sub(r"\w\$\d", "", text)
        text = text.replace('(', '').replace(')', '')
        # text = re.sub(r"\[.*\]" ,"" ,text)
        return text.strip()

    def dict_to_list(self, dictionary):
        final_list = []
        for key, value in dictionary.items():
            for data_dict in value:
                for text_frame_no, txt in data_dict.items():
                    if "www." in txt.lower():
                        # new_text = re.sub(r'\s*www\.\S+', '', txt)  # --> regex for only address without website
                        new_text = re.sub(r'(b\$0)?\s*www\.\S+(b\$1)?', '', txt)  # --> regex for only address without website
                        text_add = str(new_text).split("*#")
                        for k1 in text_add:
                            if k1.strip():
                                final_list.append(k1)
                        # match = re.search(r'(www\.\S+)',txt).group()  # --> regex for only website without address
                        match = re.search(r'(b\$0)?\s*www\.\S+(b\$1)?',txt).group()  # --> regex for only website without address
                        text_web = str(match).split("*#")
                        for k2 in text_web:
                            if k2.strip():
                                final_list.append(k2)
                            #                             item = re.sub(str(self.splt_parameter), lambda pat: pat.group(1) + "*#" + pat.group(2), txt,flags=re.M)  ## For applying into multi line content
                    else:
                        #                                 itms = []
                        item = str(txt).split("*#")
                        for itm in item:
                            if itm.strip():
                                final_list.append(itm)

        return final_list

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

    def final_dict(self, txt_list, classifier, probability=0.70, unwanted_txt_len=10, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):

        # copy_elements_fixed = ["Country of Origin", "usage instruction", "address", "storage instruction",
        #                        "allergen statement", "ingredients", "BEST_BEFORE_DATE", "DECLARATION_CONTEXT_FOOTNOTE",
        #                        "OTHER_INSTRUCTIONS", "MARKETING_COPY", "FUNCTIONAL_NAME", "SERVING_SIZE", ]

        copy_elements_fixed = ["CONTACT_INFORMATION", "CONTENT_CLAIM", "WEBSITE", "COPYRIGHT_TRADEMARK_STATEMENT",
                               "LOCATION_OF_ORIGIN", "USAGE_INSTRUCTIONS", "ADDRESS", "STORAGE_INSTRUCTIONS",
                               "ALLERGEN_STATEMENT", "INGREDIENTS_DECLARATION", "BEST_BEFORE_DATE",
                               "DECLARATION_CONTEXT_FOOTNOTE", "OTHER_INSTRUCTIONS", "MARKETING_COPY",
                               "FUNCTIONAL_NAME", "SERVING_SIZE", "WARNING_STATEMENTS", "NET_CONTENT_STATEMENT"]

        gen_cate_dic = {}
        languages = set()
        copy_elements = set()
        for txt in txt_list:
            cleaned_txt = self.text_preprocessing(txt, key_replace_list)
            #             print(cleaned_txt)
            if len(cleaned_txt) > int(unwanted_txt_len):

                if "made in" in cleaned_txt.lower():
                    classified_output = "LOCATION_OF_ORIGIN"
                elif "trademark" in cleaned_txt.lower():
                    classified_output = "COPYRIGHT_TRADEMARK_STATEMENT"
                elif "www." in cleaned_txt.lower():
                    classified_output = "WEBSITE"
                elif "file name:" in cleaned_txt.lower() or "sku:" in cleaned_txt.lower() or "contour" in cleaned_txt.lower() and "label" in cleaned_txt.lower() or "microlet" in cleaned_txt.lower() or "contour next" in cleaned_txt.lower():
                    classified_output = "CONTENT_CLAIM"
                else:
                    classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                    probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))
                    probability1.sort()
                    prob1 = probability1[0][-1]
                    if prob1 > float(probability):
                        classified_output = classified_output[0]
                    elif prob1 > 0.70 and prob1 <= probability:
                        classified_output = "OTHER_INSTRUCTIONS"
                    else:
                        classified_output = below_thres_class
            #                     print("text****",cleaned_txt,"probali****",prob1,"output******",classified_output)
            #                 print("**************************")
            else:
                #                 print("********",cleaned_txt)
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
        gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    def cep_main(self, dic):
        if "modifyData" in dic:
            return dic["modifyData"]
        txt_list = self.dict_to_list(dic)
        output_dic = self.final_dict(txt_list, classifier)
        return {**{'status': '0'}, **{"modifyData": output_dic}}


