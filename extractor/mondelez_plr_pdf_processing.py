import warnings
warnings.filterwarnings("ignore")
from bs4 import BeautifulSoup
import pdfplumber
import tabula
import tempfile
from fuzzywuzzy import fuzz
import io
from pdfminer.high_level import extract_text_to_fp
from pdfminer.layout import LAParams

from .excel_processing import *
laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)
keywords = ['storage instruction','shelf life','registration approval number','manufacturing plant',
           'instructions for graphics','net content','count per container','variant','brand name',
           'legal designation','handling statement','distributor name and address','warning statement','nutrition notes']

nutri_keys = ['energy','total fat','saturated fat','transfat','cholesterol','sodium','carbohydrate',
                  'dietary fiber','total sugars','includes added sugars','protein','servings per package',
                  'serving size','calories','servings per container','trans fat','sugar']

cnt_keys = ['Ingredient Declaration','Signature Line','Claims and Symbols','Other Labeling Information']

model_location = mondelez_pdf_plr_nutrition_model_location
classifier = joblib.load(model_location)

mondelz_model_loc = mondelez_pdf_plr_model_location
mondelz_model = joblib.load(mondelz_model_loc)


def old_cnt_dict(pdf_file, page):
    pdf = pdfplumber.open(pdf_file)
    page = pdf.pages[int(page) - 1]
    text = page.extract_text().split('\n')
    cnt_keys = ['Ingredient Declaration', 'Signature Line', 'Claims and Symbols', 'Other Labeling Information']
    size = len(text)
    idx_list = [idx + 1 for idx, val in
                enumerate(text) if val.strip() in cnt_keys]
    res = None
    if idx_list:
        res = [text[i: j] for i, j in
               zip([0] + idx_list, idx_list +
                   ([size] if idx_list[-1] != size else []))]

    #         res = [cnt.replace(s,"") for cnt in res for s in cnt_keys if s in cnt] # New for multi item

    cnt_dict = {}
    if res:
        for lst in res:
            cnt = ('\n').join(lst)

            # ###            cnt = [cnt.replace(s,"") if s in cnt else cnt for s in cnt_keys][0]
            if any(k in cnt for k in cnt_keys):
                #                 print(cnt,"BEfore   **************")
                cnt = [cnt.replace(s, "") for s in cnt_keys if s in cnt][0]
            else:
                cnt = cnt

            #             print(cnt,"After       **********")
            classified_output = mondelz_model.predict(laser.embed_sentences(cnt, lang='en'))
            probability1 = mondelz_model.predict_proba(laser.embed_sentences(cnt, lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            if classified_output in ["INGREDIENTS_DECLARATION", "SIGNATURE_LINE"]:
                #             print(cnt,"*********",prob1,classified_output)
                lang = classify(cnt)[0]
                if classified_output in cnt_dict:
                    cnt_dict[classified_output].append({lang: cnt.strip()})
                else:
                    cnt_dict[classified_output] = [{lang: cnt.strip()}]

    return cnt_dict


def attribute(input_pdf, pages, text):
    text_out = []
    output_io = io.StringIO()
    if not output_io.getvalue():
        with open(input_pdf, 'rb') as input_1:
            extract_text_to_fp(input_1, output_io, page_numbers=[int(pages) - 1],
                               laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                               output_type='html', codec=None)
    else:
        pass

    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    results = html.find_all(
        lambda tag: tag.name == "div" and fuzz.ratio(text.lower(), tag.text.lower().replace('/n', '')) > 70)
    if results:
        #         print(results)
        if 'bold' in str(results[-1]).lower():
            for span in results[-1]:
                if 'bold' in span['style'].lower():
                    new_text = span.text.split('\n')
                    text_out.append(f'&lt;b&gt;{new_text[0]}&lt;/b&gt;')
                if 'bold' not in span['style'].lower():
                    #                 print('yes')
                    new_text = span.text.split('\n')
                    text_out.append(new_text[0])
            # print(' '.join(text_out))
            return ' '.join(text_out)
        else:
            return None

def bold_text(input_pdf,page,cnt):
    prep_list=[]
    cnt_dict ={}
    split_cnt = cnt.split('\n')
    for new_cnt in split_cnt:
        if new_cnt.strip():
            output = attribute(input_pdf,page,new_cnt)
            if output:
                final_txt = output
            else:
                final_txt = new_cnt
            prep_list.append(final_txt)
    if prep_list:
        final_txt = ('\n').join(prep_list)
        return final_txt


def final_dict(input_pdf, page, dictionary):
    new_dict = {}
    for key, value in dictionary.items():
        if key in ['INGREDIENTS_DECLARATION']:
            for dic in value:
                for lang, text in dic.items():
                    final_txt = bold_text(input_pdf, page, text)
                    if 'INGREDIENTS_DECLARATION' in new_dict:
                        new_dict['INGREDIENTS_DECLARATION'].append({lang: final_txt})
                    else:
                        new_dict['INGREDIENTS_DECLARATION'] = [{lang: final_txt}]

        else:
            new_dict[key] = value

    return new_dict

def temp_dic(new_list):
    temp_dict={}
    for lst in range(0,len(new_list)):
        for item in range(1,len(new_list[lst])):
            if new_list[lst][item]!= 'None':
                if new_list[lst][0] in temp_dict:
                    temp_dict[new_list[lst][0]].append(new_list[lst][item])
                else:
                    temp_dict[new_list[lst][0]] = [new_list[lst][item]]

    return temp_dict


def list_items_append(dictionary):
    final_dict = {}
    for key, value in dictionary.items():
        for k in keywords:
            if k in key.lower():
                merge_txt = ('\n').join(value).strip()
                lang = classify(merge_txt)[0]
                if k in final_dict:
                    final_dict[k].append({lang: merge_txt})
                else:
                    final_dict[k] = [{lang: merge_txt}]

    return final_dict


def gs1_element(dictionary):
    nutri_dic = {}
    for keys, value in dictionary.items():

        classified_output_1 = mondelz_model.predict(laser.embed_sentences(
            keys.replace('\xa0', '').replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', ''),
            lang='en'))
        probability_1 = mondelz_model.predict_proba(laser.embed_sentences(
            keys.replace('\xa0', '').replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', ''),
            lang='en'))
        probability_1.sort()
        prob_1 = probability_1[0][-1]
        if prob_1 > 0.65:
            classified_output_key = classified_output_1[0]
        else:
            if keys == "nutrition notes":  # Newly added for nutrition notes
                classified_output_key = "NUTRITIONAL_CLAIM"
            else:
                classified_output_key = keys

        if classified_output_key in nutri_dic:

            nutri_dic[classified_output_key].append(value)
        else:
            nutri_dic[classified_output_key] = value

    return nutri_dic


def gen_cate(df):
    dict_list = []
    for table in range(len(df)):
        df[table] = df[table].dropna(axis=0, how='all')
        df[table].loc[:, 0] = df[table].loc[:, 0].ffill()
        df[table] = df[table].fillna('None')
        new_list = df[table].values.tolist()
        temp_dict = temp_dic(new_list)
        final_dict = list_items_append(temp_dict)
        dict_list.append(final_dict)

    temp_final_dict = {k: v for x in dict_list for k, v in x.items()}
    new_final_dict = gs1_element(temp_final_dict)

    return new_final_dict


def nutrition_extraction(dataframe):
    nutri_list = dataframe.fillna('None').values.tolist()
    #     print(nutri_list)
    for leng in range(0, len(nutri_list)):
        if nutri_list[leng][0].lower() == 'nutrition declaration':
            nutri_list = nutri_list[leng:]
            break

    if nutri_list:
        nutri_header_dic = {}
        for lis in nutri_list:
            if len(lis) >= 2:
                if '项目' in lis[0] and '%' in lis[1]:
                    item = (' ').join(lis)
                    header = item.split(' ', 2)
                    for value in header:
                        if "NUTRI_TABLE_HEADERS" in nutri_header_dic:
                            nutri_header_dic["NUTRI_TABLE_HEADERS"].append({"en": value.strip()})
                        else:
                            nutri_header_dic["NUTRI_TABLE_HEADERS"] = [{"en": value.strip()}]

        final_nutri_list = []
        for lst in nutri_list:
            if lst[0] != 'None':
                classified_output = classifier.predict(laser.embed_sentences(lst[0].replace('-', ''), lang='en'))
                probability1 = classifier.predict_proba(laser.embed_sentences(lst[0].replace('-', ''), lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]
                if prob1 > 0.75:
                    classified_output = classified_output[0]
                else:
                    classified_output = 'None'

                if classified_output.lower() in nutri_keys:
                    #             outcome = []
                    final_nutri_list.append([lst, classified_output])

        if final_nutri_list:
            nutri_dic = {}
            reg_list = []
            for i in final_nutri_list:
                reg = re.findall(r'((&lt;)?\s?(\d+)(\.\d+)?\s?(千焦|克|毫克|mg|kj|g|ก|มก|%|mcg))', i[0][1])
                reg_list.append(reg)


            for j in range(0, len(reg_list)):
                for n in range(0, len(reg_list[j])):
                    if reg_list[j][n][0] != '':
                        if final_nutri_list[j][1] in nutri_dic:
                            if '%' not in reg_list[j][n][0]:
                                nutri_dic[final_nutri_list[j][1]].append({'Value': {'en': reg_list[j][n][0].strip()}})
                            else:
                                nutri_dic[final_nutri_list[j][1]].append({'PDV': {'en': reg_list[j][n][0].strip()}})
                        else:
                            if '%' not in reg_list[j][n][0]:
                                nutri_dic[final_nutri_list[j][1]] = [{'Value': {'en': reg_list[j][n][0].strip()}}]
                            else:
                                nutri_dic[final_nutri_list[j][1]] = [{'PDV': {'en': reg_list[j][n][0].strip()}}]
                # Newly added for source nutrition names
                else:
                    if final_nutri_list[j][1] in nutri_dic:
                        nutri_dic[final_nutri_list[j][1]].append(
                            {'copy_notes': {'en': final_nutri_list[j][0][0].strip()}})
                    else:
                        nutri_dic[final_nutri_list[j][1]] = [
                            {'copy_notes': {'en': final_nutri_list[j][0][0].strip()}}]
            final_nutri_dic = {}
            final_nutri_dic['NUTRITION_FACTS'] = [nutri_dic]
            return {**final_nutri_dic,**nutri_header_dic}


def cate_routing(file, page):
    with pdfplumber.open(file) as pdf:
        if int(page) <= len(pdf.pages):
            df = tabula.read_pdf(file, area=[10, 10, 783, 583], pages=str(page), stream=True,
                                 pandas_options={'header': None}, multiple_tables=False, columns=[165])

            gen_cate_dic = gen_cate(df)
            content_dict = old_cnt_dict(file, page)
            try:
                if content_dict:
                    new_cnt_dic = final_dict(file, page, content_dict)
                else:
                    new_cnt_dic = {}
            except:
                new_cnt_dic = content_dict

            nutri_list = df[0].fillna('None').values.tolist()
            flag = 0
            for leng in range(0, len(nutri_list)):
                if nutri_list[leng][0].lower() == 'nutrition declaration':
                    flag = 1
            if flag == 1:
                nutrition_dic = nutrition_extraction(df[0])
            else:
                nutrition_dic = {}

            return {**gen_cate_dic, **nutrition_dic, **new_cnt_dic}

        else:
            return {}


def mondelez_main_plr(file, pages):
    t5 = time.time()
    page_dict = {}

    for page in pages.split(','):
        out = cate_routing(file, int(page))
        page_dict[page] = out

    t6 = time.time()
    print(f'Finished in {t6 - t5}seconds')
    return page_dict
