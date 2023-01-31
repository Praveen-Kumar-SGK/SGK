import re
import joblib
from langid import classify
from .excel_processing import *
from dataclasses import dataclass, field

# ------------------------------------------------------------

# Loading model


classifier = joblib.load(cocacola_cep_model_loc)


# ------------------------------------------------------------

@dataclass
class Cocacola_CEP_Template:
    splt_parameter: str = r"\.\r|\. |\.\t"

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

    def ingredient_contact_split(self, gen_cate):
        contct = []
        for key, val in gen_cate.items():
            if "INGREDIENTS_DECLARATION" in key:
                for ind, dic in enumerate(val):
                    ingrt = list(dic.items())[0][1].lower()
                    ingrt = ingrt.split('\r', 1)
                    if 'consumer information' in ingrt[0]:
                        contct.append({'en': ingrt[0]})
                        gen_cate["INGREDIENTS_DECLARATION"][ind] = {'en': ingrt[1]}
                    else:
                        gen_cate = gen_cate
        try:
            gen_cate["CONTACT_INFORMATION"].extend(contct)
        except:
            gen_cate["CONTACT_INFORMATION"] = contct
        return gen_cate

    def final_dict(self, txt_list, classifier, probability=0.75, unwanted_txt_len=4, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):
        copy_elements_fixed = ["address","OTHER_INSTRUCTIONS","MARKETING_CLAIM","expiration statement",
                             "ingredients","storage instruction","Country of Origin",
                             "warning statement","WEBSITE","VARIANT","net content",
                             "usage instruction","RECYCLE_STATEMENT","DIET_EXCHANGES","INTERNAL_PACKAGE_IDENTIFIER"]

        gs = {"MANUFACTURING_SITE": 'address', "BEST_BEFORE_DATE": 'expiration statement',
        "INGREDIENTS_DECLARATION": 'ingredients',
        "STORAGE_INSTRUCTIONS": 'storage instruction', "LOCATION_OF_ORIGIN": 'Country of Origin',
        "WARNING_STATEMENTS": 'warning statement', "NET_CONTENT_STATEMENT": 'net content',
        "USAGE_INSTRUCTIONS": 'usage instruction', "CONTACT_INFORMATION": 'address'}

        key_replace_list = ()

        gen_cate = {}
        gen_cate_dic ={}
        languages = set()
        copy_elements = set()
        for txt in txt_list:
            cleaned_txt = self.text_preprocessing(txt, key_replace_list)
            if (len(cleaned_txt) == 8 or len(cleaned_txt) == 6) and (
                    str(cleaned_txt).startswith('133') or str(cleaned_txt).startswith('95')):
                classified_output = "INTERNAL_PACKAGE_IDENTIFIER"
            elif cleaned_txt[0].isdigit() and (cleaned_txt.endswith('ml') or cleaned_txt.endswith('l')) and len(
                    cleaned_txt) <= 6 and cleaned_txt[-3:] != 'cal':
                classified_output = "net content"
            elif (cleaned_txt.startswith('1800') or cleaned_txt.startswith('0800')) and len(cleaned_txt) <= 12:
                classified_output = "address"
            else:
                if len(cleaned_txt) > int(unwanted_txt_len):
                    classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                    probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))[0]
                    probability1.sort()
                    proba = probability1[-1]
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
                # value = self.bold_tag_close(txt)
                value = txt

            lang = self.language_detection(cleaned_txt, language)
            if classified_output in gs:
                classified_output=gs[classified_output]
            copy_elements.add(classified_output)
            languages.add(lang)
            gen_cate.setdefault(classified_output, []).append({lang: value})
            gen_cate_dic = self.ingredient_contact_split(gen_cate)
            gen_cate_dic = {key: val for key, val in gen_cate_dic.items() if val}
        gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    def cocacola_cep_main(self, dic):
        if "modifyData" in dic:
            return dic["modifyData"]
        txt_list = self.dict_to_list(dic)
        output_dic = self.final_dict(txt_list, classifier)
        return {**{'status': '0'}, **{"modifyData": output_dic}}

# ------------------------------------------------------------------------
