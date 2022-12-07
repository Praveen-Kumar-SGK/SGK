import warnings
warnings.filterwarnings("ignore")
from bs4 import BeautifulSoup
import mammoth
from pdf2docx import parse
import pdfplumber
import tabula
import tempfile
from fuzzywuzzy import fuzz
from .excel_processing import *

path = document_location

arnotts_model_loc = campbell_arnotts_model
arnotts_model = joblib.load(arnotts_model_loc)

filename_nutri = campbell_arnotts_nutrition_model
classifier = joblib.load(filename_nutri)

cnt_keys = ['ENERGY','PROTEIN','FAT, TOTAL','SATURATED','GLUTEN',
            'CARBOHYDRATE','SUGARS','DIETARY FIBRE','SODIUM','*']
serving_key = ['SERVINGS PER PACKAGE','SERVING SIZE']


def arnott_gen_cate(pdf_file, page):
    df = tabula.read_pdf(pdf_file, pages=str(page), lattice=True,
                         pandas_options={'header': None})
    gen_cate_dic = {}
    nutri_list = []
    for table in range(len(df)):
        df[table] = df[table].dropna(axis=0, how='all')
        df[table] = df[table].dropna(axis=1, how='all')
        df[table] = df[table].fillna('None')
        new_list = df[table].values.tolist()
        for row in range(0, len(new_list)):
            if new_list[row][0] != "None":
                new_list[row] = [txt for txt in new_list[row] if txt != "None"]
                for inn_list in range(1, len(new_list[row]) - 1):
                    cnt = re.sub("\r|-", " ", new_list[row][0])
                    classified_output = arnotts_model.predict(laser.embed_sentences(cnt, lang='en'))
                    probability1 = arnotts_model.predict_proba(laser.embed_sentences(cnt, lang='en'))
                    probability1.sort()
                    prob1 = probability1[0][-1]
                    if prob1 > 0.75:
                        classified_output = classified_output[0]
                    else:
                        classified_output = 'Unmapped'

                    #                         print(new_list[row],classified_output,prob1)

                    if len(new_list[row]) >= 2:
                        value = re.sub("\r", "\n",
                                       str(new_list[row][inn_list]).replace('<', '&lt;').replace('>', '&gt;').strip())
                        if classified_output not in ["NUTRITIONAL_PANEL"]:
                            lang = classify(value)[0]
                            if value not in ["None"]:
                                if classified_output in gen_cate_dic:
                                    gen_cate_dic[classified_output].append({lang: value})
                                else:
                                    gen_cate_dic[classified_output] = [{lang: value}]

                        elif classified_output in ["NUTRITIONAL_PANEL"]:
                            nutri_list.append(value)
                else:
                    if new_list[row][0].lower() in ("legibility"):
                        value = re.sub("\r", "\n",
                                       str(new_list[row][1]).replace('<', '&lt;').replace('>', '&gt;').strip())
                        lang = classify(value)[0]
                        if "Unmapped" in gen_cate_dic:
                            gen_cate_dic["Unmapped"].append({lang: value})
                        else:
                            gen_cate_dic["Unmapped"] = [{lang: value}]

                # Newly added
            elif new_list[row][0] == "None" and re.sub("\r|-", " ", new_list[row][1].lower()) in ['storage conditons',
                                                                                                  'weight statement',
                                                                                                  'claims',
                                                                                                  'warning statement',
                                                                                                  'nutritional panel']:
                cnt = re.sub("\r|-", " ", new_list[row][1])
                classified_output = arnotts_model.predict(laser.embed_sentences(cnt, lang='en'))
                probability1 = arnotts_model.predict_proba(laser.embed_sentences(cnt, lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]
                if prob1 > 0.75:
                    classified_output = classified_output[0]
                else:
                    classified_output = 'Unmapped'

                #             print(new_list[row],classified_output,prob1)

                if len(new_list[row]) >= 2:
                    value = re.sub("\r", "\n", str(new_list[row][2]).replace('<', '&lt;').replace('>', '&gt;').strip())
                    if classified_output not in ["NUTRITIONAL_PANEL"]:
                        lang = classify(value)[0]
                        if value not in ["None"]:
                            if classified_output in gen_cate_dic:
                                gen_cate_dic[classified_output].append({lang: value})
                            else:
                                gen_cate_dic[classified_output] = [{lang: value}]

                    elif classified_output in ["NUTRITIONAL_PANEL"]:
                        nutri_list.append(value)

            else:
                for inn_list in range(1, len(new_list[row]) - 1):
                    value = re.sub("\r", "\n",
                                   str(new_list[row][inn_list]).replace('<', '&lt;').replace('>', '&gt;').strip())
                    lang = classify(value)[0]
                    if value not in ["None"]:
                        if "nutrition information" not in value.lower() and "serving size" not in value.lower():
                            if 'Unmapped' in gen_cate_dic:
                                gen_cate_dic['Unmapped'].append({lang: value})
                            else:
                                gen_cate_dic['Unmapped'] = [{lang: value}]
    #     print(nutri_list)
    return gen_cate_dic, nutri_list
    
def remove_nan(lst_of_lst):
    final_list=[]
    for row in range(len(lst_of_lst)):
        temp_list=[]
        for col in range(len(lst_of_lst[row])):
            if lst_of_lst[row][col]!= "None":
                temp_list.append(lst_of_lst[row][col])
        if temp_list:
            final_list.append(temp_list)
    return final_list
    
def updated_gen_cate(pdf_file, page):
    new_gen_cate_dic = {}
    nutri_list = []
    df = tabula.read_pdf(pdf_file, pages=str(page), lattice=True, area=[10, 10, 883, 583],
                         pandas_options={'header': None})
    for table in range(len(df)):
        df[table] = df[table].dropna(axis=0, how='all')
        df[table] = df[table].dropna(axis=1, how='all')
        df[table] = df[table].fillna('None')
        new_list = df[table].values.tolist()
        new_list = remove_nan(new_list)
        #             print(new_list)
        if new_list:
            for row in range(len(new_list)):
                new_list[row] = [txt for txt in new_list[row] if txt != ""]
                #                 print(new_list[row][col],"*********")
                cnt = re.sub("\r|-", " ", new_list[row][0])
                cnt = cnt.replace("torage onditions", "storage use directions")
                classified_output = arnotts_model.predict(laser.embed_sentences(cnt, lang='en'))
                probability1 = arnotts_model.predict_proba(laser.embed_sentences(cnt, lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]
                if prob1 > 0.75:
                    classified_output = classified_output[0]
                else:
                    classified_output = 'Unmapped'

                # print(cnt, classified_output, prob1)

                if classified_output != 'Unmapped':
                    for col in range(1, len(new_list[row])):
                        value = re.sub("\r", "\n",
                                       str(new_list[row][col]).replace('<', '&lt;').replace('>', '&gt;').strip())
                        if classified_output not in ["NUTRITIONAL_PANEL"]:
                            lang = classify(value)[0]
                            if value.strip():
                                if classified_output in new_gen_cate_dic:
                                    if {lang: value} not in new_gen_cate_dic[classified_output]:
                                        new_gen_cate_dic[classified_output].append({lang: value})
                                else:
                                    new_gen_cate_dic[classified_output] = [{lang: value}]
                        else:
                            nutri_list.append(value)
                else:

                    for col in range(0, len(new_list[row])):
                        value = re.sub("\r", "\n",
                                       str(new_list[row][col]).replace('<', '&lt;').replace('>', '&gt;').strip())
                        #                             if classified_output not in ["NUTRITIONAL_PANEL"]:
                        lang = classify(value)[0]
                        if value.strip():
                            if classified_output in new_gen_cate_dic:
                                if {lang: value} not in new_gen_cate_dic[classified_output]:
                                    new_gen_cate_dic[classified_output].append({lang: value})

                            else:
                                new_gen_cate_dic[classified_output] = [{lang: value}]

    return new_gen_cate_dic, nutri_list


def serving_dictionary(serving_list):
    serving_dic = {}
    if serving_list:
        for txt in serving_list:
            for k in serving_key:
                if k in txt:
                    new_txt = txt.split(k)
                    value = new_txt[1].replace('<','&lt;').replace('>','&gt;').strip()
                    lang = classify(value)[0]
                    if value:
                        if k in ["SERVINGS PER PACKAGE"]:
                            if "Servings Per Package" in serving_dic:
                                serving_dic["Servings Per Package"].append({lang: value})
                            else:
                                serving_dic["Servings Per Package"] = [{lang: value}]
                        elif k in ["SERVING SIZE"]:
                            if "Serving Size" in serving_dic:
                                serving_dic["Serving Size"].append({lang: value})
                            else:
                                serving_dic["Serving Size"] = [{lang: value}]

    return serving_dic


def non_english_nutri_dic(non_eng_list_of_list):
    non_eng_list_of_list = [re.sub(r'\xa0|<b>|</b>|\n', '', ('').join(i)).strip() for i in non_eng_list_of_list]

    #     print(non_eng_list_of_list)
    value_list = []
    #     key_list = []
    for i in non_eng_list_of_list:
        value_reg = re.findall(r'((<)?(Lessthan)?\s?(\d+)?(\,\d+)?(\.\d+)?\s?(mg|kj|Cal|kJ|g|ก|มก|%|mcg|Not Detected))',
                               i)  # nutri units may change depends of lan
        #         key_reg = ('').join(re.findall(r'([^(&lt;)?\s?(\d+)?(\,\d+)?(\.\d+)?\s?(mg|kj||kJ|g|%|mcg|ก|มก)])',i))  # nutri units may change depends of lan
        value_list.append(value_reg)
    non_eng_nutri_dic = {}
    if len(non_eng_list_of_list) == len(value_list):
        for j in range(0, len(value_list)):
            for n in range(0, len(value_list[j])):
                for k in cnt_keys:
                    if k in non_eng_list_of_list[j]:
                        if value_list[j][n][0].strip() not in ['']:
                            final_value = value_list[j][n][0].replace('<','&lt;').replace('>','&gt;').strip()
                            if k in non_eng_nutri_dic:
                                if '%' not in value_list[j][n][0]:
                                    non_eng_nutri_dic[k].append({'Value': {'en': final_value}})
                                else:
                                    non_eng_nutri_dic[k].append({'PDV': {'en': final_value}})
                            else:
                                if '%' not in value_list[j][n][0]:
                                    non_eng_nutri_dic[k] = [{'Value': {'en': final_value}}]
                                else:
                                    non_eng_nutri_dic[k] = [{'PDV': {'en': final_value}}]

    return non_eng_nutri_dic


def gs1_key(dictionary):  # Input dictionary must be in standard format.

    final_dic = {}
    for keys, value in dictionary.items():
        cnt = re.sub(r'\xa0|<b>|</b>|\n|-', '', keys).strip()
        classified_output_1 = classifier.predict(laser.embed_sentences(cnt, lang='en'))
        probability_1 = classifier.predict_proba(laser.embed_sentences(cnt, lang='en'))
        probability_1.sort()
        prob_1 = probability_1[0][-1]
        if prob_1 > 0.65:  # Threshold can be changed depends on the scenario.
            classified_output_key = classified_output_1[0].strip()
        else:
            classified_output_key = 'None'

        #         print(cnt,classified_output_key,prob_1)
        if classified_output_key != 'None':
            if classified_output_key in final_dic:
                final_dic[classified_output_key].append(value)
            else:
                final_dic[classified_output_key] = value
        else:
            if cnt in final_dic:
                final_dic[cnt].append(value)
            else:
                final_dic[cnt] = value

    return final_dic


def nutri_dictionary(nutri_list):
    if nutri_list:
        text = nutri_list[0].split('\n')
        size = len(text)
        idx_list = [idx for idx, val in
                    enumerate(text) if any(k in val.strip() for k in cnt_keys)]
        res = None
        if idx_list:
            res = [text[i: j] for i, j in
                   zip([0] + idx_list, idx_list +
                       ([size] if idx_list[-1] != size else []))]

        if res:
            new_nutri_list = []
            serving_list = []
            for row in range(0, len(res)):
                for col in range(0, len(res[row])):
                    for key in cnt_keys:
                        if key in res[row][col] and key != "*":
                            new_nutri_list.append(res[row])
                        elif any(k in res[row][col] for k in serving_key):
                            serving_list.append(res[row][col])
                            break

            serving_dic = serving_dictionary(serving_list)
            nutri_dic = non_english_nutri_dic(new_nutri_list)
            final_nutri_dic = gs1_key(nutri_dic)
            return serving_dic, final_nutri_dic

def pdf_to_docx(pdf_file,page,docx_location):
    # docx_file = path + 'file_p2.docx'
    parse(pdf_file, docx_location,pages = [page-1])
    return docx_location


def pdf_to_content_list(docx_file):
    #     docx_file = pdf_to_docx(file,page)
    html = mammoth.convert_to_html(docx_file).value
    soup = BeautifulSoup(html, "html.parser")
    #     print(soup)
    table_content_list_all = []
    for tables in soup.find_all('p'):
        raw_html = str(tables).replace('<strong>', '&lt;b&gt;').replace('</strong>', '&lt;/b&gt;').replace('<br/>',
                                                                                                           '\n').replace(
            '\t', '')
        #         raw_html = str(tables).replace('<strong>','&lt;b&gt;').replace('</strong>','&lt;/b&gt;').replace('\t','').replace('<br/>','\n')
        #         print(raw_html)
        cleantext = BeautifulSoup(raw_html, "html").text.strip()
        cleantext = cleantext.split('\n')
        #         print(cleantext)
        if cleantext:
            for cnt in cleantext:
                table_content_list_all.append(cnt.strip())

    #     print(table_content_list_all)
    return table_content_list_all


class recursive(object):
    def __init__(self, _list, index, score, text, src_text):
        self.score = score
        self.index = index
        self._list = _list
        self.text = text
        self.src_text = src_text

    def try_recursion(self):
        combine_next_seg = lambda x: ''.join((self.text, self._list[x]))  # one line function # Changed to x from x+1(out of range)
        try:
            temp_text = combine_next_seg(self.index)
        except:
            temp_text = self.text
        temp_score = fuzz.ratio(re.sub("<.*?>", "", temp_text.lower()), self.src_text.lower())
        if temp_score > self.score:
            self.score = temp_score
            self.index = self.index + 1
            self.text = temp_text
            self.try_recursion()
        # print(f"return value ========>{self.score}---->{self.index}")
        return self.score, self.index


def search_bold_content(text, content_list):
    score_dict = {}
    for index, div_text in enumerate(content_list):
        score = fuzz.ratio(text, re.sub("<.*?>", "", div_text))
        #         print(score)
        if score > 30:
            temp_score_recur, upto_index_recur = recursive(content_list, index, score, div_text,
                                                           text).try_recursion()
            # print(index,upto_index_recur)
            score_dict[temp_score_recur] = " ".join(content_list[index:upto_index_recur + 1])

    if score_dict and max(score_dict) > 80:
        #         print(score_dict[max(score_dict)])
        return score_dict[max(score_dict)]

def bold_text_dic(dictionary,pdf_file,page,docx_location):
    new_dict={}
    if dictionary:
        if any(k in list(dictionary.keys()) for k in ["INGREDIENTS_DECLARATION","ALLERGEN_STATEMENT"]):
            docx_file = pdf_to_docx(pdf_file,page,docx_location)
            cnt_list = pdf_to_content_list(docx_file)
    #         print(cnt_list)
            for key,value in dictionary.items():
                if key in ["INGREDIENTS_DECLARATION","ALLERGEN_STATEMENT"]:
    #                 print(dictionary)
                    for dic in value:
                        for lang,txt in dic.items():
                            temp_list=[]
                            txt = txt.split('\n')
                            for text in txt:
                                bold_txt = search_bold_content(text,cnt_list)
                                if bold_txt:
                                    temp_list.append(bold_txt)
                                else:
                                    temp_list.append(text)
    #                                 print(temp_list)
                            if temp_list:
                                bold_txt = ('\n').join(temp_list)
        #                         print(bold_txt)
                                if bold_txt:
                                    bold_txt = bold_txt.replace('<b>','&lt;b&gt;').replace('</b>','&lt;/b&gt;').strip()
    #                                 if any(k in bold_txt for k in cnt_keys):
    #                                     bold_txt = [bold_txt.replace(s,"") for s in cnt_keys if s in bold_txt][0]
    #                                 else:
    #                                     bold_txt = bold_txt
                                    if key in new_dict:
                                        new_dict[key].append({lang:bold_txt})
                                    else:
                                        new_dict[key] = [{lang:bold_txt}]
                                else:
                                    if key in new_dict:
                                        new_dict[key].append({lang:txt})
                                    else:
                                        new_dict[key] = [{lang:txt}]
                else:
                    new_dict[key] = value
        else:
            new_dict = dictionary

    return new_dict

from .utils import GetInput
def arnott_cate_route(pdf_file, page):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    converted_docx = f'{temp_directory.name}/converted.docx'
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    get_input = GetInput(pdf_file, input_pdf_location)
    pdf_file = get_input()
    with pdfplumber.open(pdf_file) as pdf:
        if int(page) <= len(pdf.pages):
#             gen_cate_dic, nutri_list = arnott_gen_cate(pdf_file, str(page))
            gen_cate_dic, nutri_list = updated_gen_cate(pdf_file, str(page))
            new_gen_cate_dic = bold_text_dic(gen_cate_dic,pdf_file,page,converted_docx)
            # new_gen_cate_dic = gen_cate_dic  # without bold
            if nutri_list:
                serving_dic, nutri_dic = nutri_dictionary(nutri_list)
                nutriiton_dic = {}
                nutriiton_dic['NUTRITION_FACTS'] = [nutri_dic]
                oveall_dict = {**new_gen_cate_dic, **serving_dic, **nutriiton_dic}
            else:
                oveall_dict = new_gen_cate_dic
#                 serving_dic, nutriiton_dic = {}, {}
            # oveall_dict = {**new_gen_cate_dic, **serving_dic, **nutriiton_dic}
            return oveall_dict
        else:
            return {}


def arnott_main(pdf_file, pages):
    t1 = time.time()
    final_dict = {}
    for page in pages.split(","):
        page_response = arnott_cate_route(pdf_file, int(page))
        final_dict[page] = page_response

    t2 = time.time()
    print(f'Complted in {t2 - t1} secs')
    return final_dict
