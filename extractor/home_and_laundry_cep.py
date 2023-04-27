import re
import joblib
from langid import classify
from .excel_processing import *
from dataclasses import dataclass, field
from .utils import GoogleTranslate , get_gs1_elements
# ---------------------------------------------------------------------------------------------------------------------
# ------------------------------------------------------------
# Loading model
classifier = joblib.load(home_and_laundry_cep_model_loc)


# ---------------------------------------------------------------------------------------------------------------------

@dataclass
class Home_and_laundry_CEP_Template():
    # splt_parameter: str = r"\.\r|\. |\.\t"
    splt_parameter: str = r"\.[\r\n]|\. |\.\t"

    # ---------------------------------------------------------------------------------------------------------------------
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

    # ---------------------------------------------------------------------------------------------------------------------
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

    # ---------------------------------------------------------------------------------------------------------------------
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

    # ---------------------------------------------------------------------------------------------------------------------
    def bold_tag_close(self, value):
        value = value
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

    # ---------------------------------------------------------------------------------------------------------------------
    def final_dict(self, txt_list, classifier, probability=0.75, unwanted_txt_len=4, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):

        # copy_elements_fixed = ["address", "OTHER_INSTRUCTIONS", "MARKETING_CLAIM", "expiration statement",
        #  "ingredients", "storage instruction", "Country of Origin",
        #  "warning statement", "WEBSITE", "VARIANT", "net content",
        #  "usage instruction","MARKETING_COPY"]

        copy_elements_fixed = ["ADDRESS", "OTHER_INSTRUCTIONS", "MARKETING_CLAIM", "EXPIRATION STATEMENT",
                               "INGREDIENTS","STORAGE INSTRUCTION", "COUNTRY OF ORIGIN", "WARNING STATEMENT",
                               "WEBSITE", "VARIANT", "NET CONTENT", "USAGE INSTRUCTION", "MARKETING_COPY"]

        # gs = {'Warning Statement': 'warning statement', 'Contact Information': 'address',
        #       'Recycle Statement': 'MARKETING_COPY', 'Environment Statement': 'MARKETING_COPY'}

        gs = {'Warning Statement': 'WARNING STATEMENT', 'Contact Information': 'ADDRESS',
              'Recycle Statement': 'MARKETING_COPY', 'Environment Statement': 'MARKETING_COPY'}
        key_replace_list = ()
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
                # print(classified_output,cleaned_txt,len(cleaned_txt))
                if any(chr.isdigit() for chr in cleaned_txt) and (
                        cleaned_txt.endswith('ml') or cleaned_txt.endswith('l') or cleaned_txt.endswith(
                        'kg') or cleaned_txt.endswith('g')) and len(cleaned_txt) <= 8:
                    classified_output = "NET_CONTENT_STATEMENT"
                elif 'neto' in cleaned_txt and len(cleaned_txt) <= 20:
                    classified_output = "NET_CONTENT_STATEMENT"
                elif cleaned_txt.startswith('tel') or cleaned_txt.startswith('tlf') and len(cleaned_txt) < 40 and len(
                        [i for i in cleaned_txt if i.isdigit()]) <= 13:
                    classified_output = 'Contact Information'
                elif cleaned_txt.startswith('www.'):
                    classified_output = 'Contact Information'
                elif classified_output[0] == 'Contact Information' and len(cleaned_txt) < 20:
                    classified_output = 'Unmapped'
                elif classified_output[0] == 'DESIGN_INSTRUCTIONS':
                    classified_output = 'Unmapped'


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
                # value = self.bold_tag_close(txt)
                value = txt
            lang = self.language_detection(cleaned_txt, language)
            if classified_output in gs:
                classified_output = gs[classified_output]
            copy_elements.add(classified_output)
            languages.add(lang)
            if value not in ["b$0 b$1", "b$0b$1", "b$0*b$1", "•", "b$0.b$1", "b$0َb$1"] and value.strip():
                if classified_output == "Unmapped":
                    gen_cate_dic.setdefault(classified_output, []).append({lang: value})
                else:
                    gen_cate_dic.setdefault(classified_output.upper(), []).append({lang: value})
        gen_cate_dic["copyElements"] = list(set(get_gs1_elements()) - copy_elements)
        # gen_cate_dic["copyElements"] = copy_elements_fixed
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    # ---------------------------------------------------------------------------------------------------------------------
    def home_and_laundry_cep_main(self, dic):
        if "modifyData" in dic:
            return dic["modifyData"]
        txt_list = self.dict_to_list(dic)
        output_dic = self.final_dict(txt_list, classifier)
        return {**{'status': '0'}, **{"modifyData": output_dic}}

# ---------------------------------------------------------------------------------------------------------------------