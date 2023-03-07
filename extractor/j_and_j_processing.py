from .excel_extraction import *


# model_loc = r"/Users/sakthivel/Documents/SGK/J&J/Dataset/j_and_j_model.sav"
classifier = joblib.load(jnj_model_location)

def dict_to_list(dictionary):
    final_list =[]
    for layer , layer_value in dictionary.items():
        print(layer)
        #         if layer not in ['Dimensions','Legend']:
        if layer in ["data"]:
            for key ,value in layer_value.items():
                #                 print(value)
                for data_dict in value:
                    for text_frame_no , txt in data_dict.items():
                        #                         print(txt)

                        item = txt.replace('\x03' ,' ')
                        if "johnson & johnson" not in item.lower():

                            item = re.sub(r"(b\$0)", lambda pat: "**" + pat.group(0), item, flags =re.M) ## For applying into multi line content
                            #                         print(item)
                            item = str(item).split("**")
                            for k in item:
                                #                             if "johnson & johnson" not in k.lower():
                                #                             print(k,"&&&&&&&&&&&")
                                if not re.findall(r"((www.)?\w+\.ca)" ,k) and not re.findall(r"(\d+\.\d)",k):
                                    item_1 = re.sub(r"\.", lambda pat1: pat1.group(0 ) +"**", k, flags =re.M)
                                    item_1 = item_1.split("**")
                                    for k1 in item_1:
                                        item_2 = re.sub(r"•", lambda pat: "**" + pat.group(0), k1, flags =re.M)
                                        item_2 = item_2.split("**")
                                        for k2 in item_2:
                                            #                                     if len(k1)>4:
                                            if k2.strip() and k2.strip() not in final_list:
                                                final_list.append(k2.strip())
                                else:
                                    #                                         print(k)
                                    #                                         print("***************")
                                    item_2 = re.sub(r"•", lambda pat: "**" + pat.group(0), k, flags =re.M)
                                    item_2 = item_2.split("**")
                                    for k2 in item_2:
                                        #                                     if len(k1)>4:
                                        if k2.strip() and k2.strip() not in final_list:
                                            final_list.append(k2.strip())
                        else:
                            # final_list.append(item)
                            if "imported by" not in item.lower():
                                item_txt = re.sub(r"(b\$0JOHNSON & JOHNSON INC)", lambda pat: "**" + pat.group(1), item,
                                                  flags=re.M)  ## For applying into multi line content
                            else:
                                item_txt = re.sub(r"(Imported)", lambda pat: "**" + pat.group(1), item, flags=re.M)
                            item = str(item_txt).split("**")
                            for k in item:
                                if "johnson & johnson" not in k.lower():
                                    item_1 = re.sub(r"\.", lambda pat1: pat1.group(0) + "**", k, flags=re.M)
                                    item_1 = item_1.split("**")
                                    for k1 in item_1:
                                        final_list.append(k1)
                                else:
                                    final_list.append(k)

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
                           "COPYRIGHT_TRADEMARK_STATEMENT", "MARKETING_CLAIM", "OTHER_INSTRUCTIONS",
                           "DESIGN_INSTRUCTIONS", "NET_CONTENT_STATEMENT"]
    gen_cate_dic={}
    languages = set()
    copy_elements = set()
    for txt in txt_list:
        cleaned_txt = text_preprocessing(txt)
        if len(cleaned_txt) > 10:
            classified_output = classifier.predict(laser.embed_sentences(cleaned_txt, lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(cleaned_txt, lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if re.findall("(\d+\s?(ml|mL|Litre|g|litre))", txt) and len(txt) <= 25:
                classified_output = "NET_CONTENT_STATEMENT"
            else:
                if prob1 > 0.70:
                    classified_output = classified_output[0]
                elif prob1 > 0.50 and prob1 <=0.70:
                     classified_output = "OTHER_INSTRUCTIONS"
                else:
                    if "ingredients" in cleaned_txt.lower() or "ingrédients" in cleaned_txt.lower():
                        classified_output = "ingredients"
                    else:
                        classified_output = "Unmapped"
        else:
            if re.findall("(\d+\s?(ml|mL|Litre|g|litre))", txt):
                classified_output = "NET_CONTENT_STATEMENT"
            else:
                classified_output = "Unmapped"
        # print("text",txt,"probali****",prob1,"output******",classified_output)
        value = txt.strip()
        if "b$0" in value and "b$1" not in value:
            value = "".join((value, "b$1"))
        elif "b$1" in value and "b$0" not in value:
            value = "".join(("b$0", value))
        lang = classify(cleaned_txt)[0]
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


def j_and_j_main(dic):
    if "modifyData" in dic["data"]:
        return dic["data"]["modifyData"]
    txt_list = dict_to_list(dic)
    output_dic = final_dict(txt_list)
    return {**{'status':'0'},**{"modifyData":output_dic}}
