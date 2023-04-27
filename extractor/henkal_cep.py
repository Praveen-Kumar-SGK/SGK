from .excel_extraction import *
from .utils import GoogleTranslate , get_gs1_elements


# model_loc = r"/Users/sakthivel/Documents/SGK/Henkal_CEP/henkal_cep_model.sav"
classifier = joblib.load(henkal_model_location)

def dict_to_list(dictionary):
    final_list = []
    for key, value in dictionary.items():
        #                 print(value)
        for data_dict in value:
            for text_frame_no, txt in data_dict.items():
                #                         print(txt.replace('\r','\n'))
                #                         print("***********************")
                if not re.findall(r"(\d\.)", txt) and not re.findall(r"(\w+\.com)", txt) and not re.findall(
                        r"(\.\w\$\d)", txt):
                    item = re.sub(r"\.", lambda pat: pat.group() + "**", txt,
                                  flags=re.M)  ## For applying into multi line content
                    #                             print(item)
                    #                             print("*****************")
                    item = str(item).split("**")

                    for k in item:
                        if k.strip():
                            final_list.append(k.strip())
                else:
                    final_list.append(txt.strip())
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

def final_dict(txt_list):
    copy_elements_fixed = ["COUNTRY OF ORIGIN", "USAGE INSTRUCTION", "ADDRESS", "SHELF_LIFE_STATEMENT",
                           "STORAGE INSTRUCTION", "ALLERGEN STATEMENT", "INGREDIENTS", "WARNING STATEMENT",
                           "COPYRIGHT_TRADEMARK_STATEMENT", "MARKETING_CLAIM", "OTHER_INSTRUCTIONS"]
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
#             print("text",cleaned_txt,"probali****",prob1,"output******",classified_output)
#             print("**************************")
        else:
                classified_output = 'Unmapped'

        value = txt.strip()
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
    gen_cate_dic["copyElements"] = list(set(get_gs1_elements()) - copy_elements)
    # gen_cate_dic["copyElements"] = copy_elements_fixed
    gen_cate_dic["languages"] = list(languages)
    return gen_cate_dic

def henkal_main(dic):
    if "modifyData" in dic:
        return dic["modifyData"]
    txt_list = dict_to_list(dic)
    output_dic = final_dict(txt_list)
    return {**{'status':'0'},**{"modifyData":output_dic}}
