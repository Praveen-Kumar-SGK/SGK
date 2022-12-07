from .excel_processing import *

# model_loc = r"/Users/sakthivel/Documents/SGK/Beiersdorf_CEP/dataset/beiersdorf_cep_model.sav"
# model_loc = "/Users/sakthivel/Documents/SGK/Beiersdorf_CEP/dataset/beiersdorf_cep_upsamp_model.sav"

classifier = joblib.load(beiersdorf_cep_model_loc)

def dict_to_list(dictionary):
    final_list = []
    for key ,value in dictionary.items():
        for data_dict in value:
            for text_frame_no , txt in data_dict.items():
                item = re.sub(r"\.\r|\. \r", lambda pat: pat.group()+"*#", txt, flags=re.M)  ## For applying into multi line content
                item = str(item).split("*#")
                for k in item:
                    if k.strip():
                        final_list.append(k.strip())
    return final_list


def text_preprocessing(text):
    text = str(text)
    text = text.lower()
    text = text.replace('\r',' ').replace("\t","")
    text = re.sub(r"\w\$\d","",text)
    text = text.replace('(','').replace(')','')
    text = re.sub(r"\[.*\]","",text)
    return text.strip()

def final_dict(txt_list):
    copy_elements_fixed = ["Country of Origin", "usage instruction", "address", "shelf_life_statement",
                           "storage instruction", "allergen statement", "ingredients", "warning statement",
                           "COPYRIGHT_TRADEMARK_STATEMENT","MARKETING_CLAIM", "OTHER_INSTRUCTIONS",
                           "CONTACT_INFORMATION","DISCLAIMER","WEBSITE","DESIGN_INSTRUCTIONS"]
    gen_cate_dic={}
    languages = set()
    copy_elements = set()
    for txt in txt_list:
        cleaned_txt = text_preprocessing(txt)
        if len(cleaned_txt) > 15:
            if "disclaimer" in txt.strip().lower():
                classified_output = "DISCLAIMER"
            elif "www" in txt.strip().lower():
                classified_output = "WEBSITE"
            else:
                classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
                probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]
                if prob1 > 0.70:
                    classified_output = classified_output[0]
                # elif prob1 > 0.60 and prob1 <=0.70:
                #      classified_output = "OTHER_INSTRUCTIONS"
                else:
                    classified_output = "Unmapped"
                # print("text", txt, "probali****", prob1, "output******", classified_output)
        else:
            if "www" in txt.strip().lower():
                classified_output = "WEBSITE"
            else:
                classified_output = "Unmapped"

        value = txt.strip()
        if "b$0" in value and "b$1" not in value:
            value = "".join((value, "b$1"))
        elif "b$1" in value and "b$0" not in value:
            value = "".join(("b$0", value))
        lang = classify(cleaned_txt)[0]
        copy_elements.add(classified_output)
        languages.add(lang)
        gen_cate_dic.setdefault(classified_output, []).append({lang:value})
    gen_cate_dic["copyElements"] = list(set(copy_elements_fixed) - copy_elements)
    gen_cate_dic["languages"] = list(languages)
    return gen_cate_dic


def beiersdorf_cep_main(dic):
    if "modifyData" in dic:
        return dic["modifyData"]
    txt_list = dict_to_list(dic)
    output_dic = final_dict(txt_list)
    return {**{'status':'0'},**{"modifyData":output_dic}}