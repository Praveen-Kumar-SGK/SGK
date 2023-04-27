from .excel_processing import *
from dataclasses import dataclass,field
from .utils import GoogleTranslate , get_gs1_elements

# model_loc = r"/Users/sakthivel/Documents/SGK/Kimberly/Dataset/kimberly_cep_model.sav"
# joblib.dump(classifier,model_loc)
classifier = joblib.load(kimberly_cep_model_loc)


@dataclass
class CEP_Template:
    # splt_parameter: str = r"\.\r|\. \r|\.  |  \r|•|\. |b\$1"
    splt_parameter: str = r"\.[\r\n]|\. [\r\n]|\.  |  [\r\n]|•|\. |b\$1"

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
                    item = re.sub(str(self.splt_parameter), lambda pat: pat.group() + "*#", txt,
                                  flags=re.M)  ## For applying into multi line content
                    item = str(item).split("*#")
                    for k in item:
                        if k.strip():
                            final_list.append(k.strip())
        return final_list

    def language_detection(self, value, language=None):  # lang Module need to update
        # if language == "google translate":
        #     lang = "gt"  # need to integrate
        # elif language == "whatlangid":
        #     lang = "wl"  # need to integrate
        # else:
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

    def final_dict(self, txt_list, classifier, probability=0.75, unwanted_txt_len=10, below_thres_class="Unmapped",
                   language=None, key_replace_list=()):

        copy_elements_fixed = ["COUNTRY OF ORIGIN", "USAGE INSTRUCTION", "ADDRESS", "SHELF_LIFE_STATEMENT",
                               "STORAGE INSTRUCTION", "ALLERGEN STATEMENT", "INGREDIENTS", "WARNING STATEMENT",
                               "COPYRIGHT_TRADEMARK_STATEMENT", "MARKETING_CLAIM", "OTHER_INSTRUCTIONS",
                               "MARKETING_COPY", "FUNCTIONAL_NAME", "CONTACT_INFORMATION", "DISCLAIMER",
                               "WEBSITE", "DESIGN_INSTRUCTIONS", "RECYCLE_STATEMENT", "MANUFACTURER_STATEMENT"]

        gen_cate_dic = {}
        languages = set()
        copy_elements = set()
        for txt in txt_list:
            cleaned_txt = self.text_preprocessing(txt, key_replace_list)
            if len(cleaned_txt) >= int(unwanted_txt_len):
                classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]

                if "made in" in cleaned_txt.lower() or "fabricado" in cleaned_txt.lower():
                    classified_output = "MANUFACTURER_STATEMENT"
                elif "trademark" in cleaned_txt.lower() or "affiliates" in cleaned_txt.lower():
                    classified_output = "COPYRIGHT_TRADEMARK_STATEMENT"
                elif "www" in cleaned_txt.lower():
                    classified_output = "CONTACT_INFORMATION"
                else:
                    if prob1 > float(probability):
                        classified_output = classified_output[0]
                    elif prob1 > 0.50 and prob1 <= probability:
                        classified_output = "OTHER_INSTRUCTIONS"
                    else:
                        classified_output = below_thres_class
            #                 print("text****",cleaned_txt,"probali****",prob1,"output******",classified_output)
            # print("**************************")
            else:
                classified_output = "Unmapped"

            value = self.bold_tag_close(txt)
            lang = self.language_detection(cleaned_txt, language)
            copy_elements.add(classified_output)
            languages.add(lang)
            if value not in ["b$0 b$1", "b$0b$1", "b$0*b$1","•","b$0.b$1","b$0َb$1"] and value.strip():
                if classified_output == "Unmapped":
                    gen_cate_dic.setdefault(classified_output, []).append({lang: value})
                else:
                    gen_cate_dic.setdefault(classified_output.upper(), []).append({lang: value})
        gen_cate_dic["copyElements"] = list(set(get_gs1_elements()) - copy_elements)
        # gen_cate_dic["copyElements"] = copy_elements_fixed
        gen_cate_dic["languages"] = list(languages)
        return gen_cate_dic

    def kimberly_cep_main(self, dic):
        if "modifyData" in dic:
            return dic["modifyData"]
        txt_list = self.dict_to_list(dic)
        output_dic = self.final_dict(txt_list, classifier)
        return {**{'status': '0'}, **{"modifyData": output_dic}}

