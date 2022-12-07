import warnings
from bs4 import BeautifulSoup
import mammoth
from pdfminer.high_level import extract_text
from pdf2docx import parse
import pdfplumber
import tempfile

from .excel_processing import *

warnings.filterwarnings("ignore")

# location = r"/Users/sakthivel/Documents/SGK/Unilever - PDF/Dataset/Unilever_pdf_model.pkl"
classifier = joblib.load(unilever_pdf_model_location)

# filename_nutri = r"/Users/sakthivel/Documents/SGK/Mondelez-Word/Penang/Dataset/mondelez_word_nutri_cate_model.sav"
classifier_key = joblib.load(mondelez_word_nutrition_model_location)

nutri_keys_para = ['energy', 'total fat', 'fat, total', 'saturated fat', 'saturated', 'transfat', 'cholesterol',
                   'sodium',
                   'carbohydrate', 'dietary fiber', 'total sugars', 'includes added sugars', 'protein',
                   'calories', 'servings per container', 'trans fat', 'sugars', 'dietary fibre', 'potassium']

def get_input(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location + input_pdf


def pdf_to_docx(file, pages, input_docx_location):
    parse(file, input_docx_location, pages=[pages - 1])
    return input_docx_location

def content_list(docx_file):
    html = mammoth.convert_to_html(docx_file).value
    soup = BeautifulSoup(html, "html.parser")
    table_content_list_all = []
    for tables in soup.find_all('table'):
        for row in tables.find_all('tr'):
            column_list = []
            for column in row.find_all('td'):
                #             column_list.append(str(column).replace('<td>','').replace('</td>','').replace('</p>','').replace('<p>','').replace('<td colspan="2">','').strip())
                raw_html = str(column).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace(
                    '</p>', '\n').strip()
                cleantext = BeautifulSoup(raw_html, "lxml").text
                column_list.append(cleantext.replace('<','&lt;').replace('>','&gt;').replace('start_bold', '<b>').replace('end_bold', '</b>'))
            table_content_list_all.append(column_list)

    return table_content_list_all


def unilever_calssifier(table_content_list_all):
    final_content_list = []
    for k in range(0, len(table_content_list_all)):
        if table_content_list_all[k]:
            split = table_content_list_all[k][0].split('\n')
            classified_output = classifier.predict(laser.embed_sentences(
                split[0].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', '').replace('\n',
                                                                                                                '').lower(),
                lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(
                split[0].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', '').replace('\n',
                                                                                                                '').lower(),
                lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            if classified_output not in ['None', 'INGREDIENTS_DECLARATION', 'NUTRITION_TABLE_CONTENT',
                                         'ALLERGEN_STATEMENT', 'NUTRITIONS', 'PREPARATION_INSTRUCTIONS']:
                contents = [table_content_list_all[k], classified_output.strip()]
                final_content_list.append(contents)

    return final_content_list


def ingredients_dic(table_content_list_all):
    ingre_dic = {}
    for k in range(0, len(table_content_list_all)):
        if table_content_list_all[k]:
            classified_output = classifier.predict(laser.embed_sentences(
                table_content_list_all[k][0].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>',
                                                                                                                 '').replace(
                    '\n', '').lower(), lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(
                table_content_list_all[k][0].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>',
                                                                                                                 '').replace(
                    '\n', '').lower(), lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            if classified_output in ['INGREDIENTS_DECLARATION', 'NUTRITION_TABLE_CONTENT', 'ALLERGEN_STATEMENT',
                                     'PREPARATION_INSTRUCTIONS']:

                lang = classify(table_content_list_all[k][0])[0]
                if classified_output in ingre_dic:
                    ingre_dic[classified_output].append({lang: table_content_list_all[k][0].replace('<b> </b>', '')})
                else:
                    ingre_dic[classified_output] = [{lang: table_content_list_all[k][0].replace('<b> </b>', '')}]

    return ingre_dic


def gen_cate_dic(final_content_list):
    gen_cate_dic = {}
    for p in range(0, len(final_content_list)):
        if len(final_content_list[p][0]) == 2:
            for d in range(1, len(final_content_list[p][0])):
                if final_content_list[p][1] == 'LEGAL_PRODUCT NAME':
                    if final_content_list[p][0][d].strip().lower() not in ['', 'ingredient']:
                        lang = classify(final_content_list[p][0][d])[0]
                        if final_content_list[p][1] in gen_cate_dic:
                            gen_cate_dic[final_content_list[p][1]].append(
                                {lang: final_content_list[p][0][d].replace('<b> </b>', '')})
                        else:
                            gen_cate_dic[final_content_list[p][1]] = [
                                {lang: final_content_list[p][0][d].replace('<b> </b>', '')}]

                else:
                    if final_content_list[p][0][d].strip() != '':
                        lang = classify(final_content_list[p][0][d])[0]
                        if final_content_list[p][1] in gen_cate_dic:
                            gen_cate_dic[final_content_list[p][1]].append(
                                {lang: final_content_list[p][0][d].replace('<b> </b>', '')})
                        else:
                            gen_cate_dic[final_content_list[p][1]] = [
                                {lang: final_content_list[p][0][d].replace('<b> </b>', '')}]


        elif len(final_content_list[p][0]) == 1:
            if final_content_list[p][1] == 'NET_CONTENT_STATEMENT':
                split = final_content_list[p][0][0].split('\n')
                if split[1].strip() != '':
                    lang = classify(split[1])[0]
                    if final_content_list[p][1] in gen_cate_dic:
                        gen_cate_dic[final_content_list[p][1]].append({lang: split[1].replace('<b> </b>', '')})
                    else:
                        gen_cate_dic[final_content_list[p][1]] = [{lang: split[1].replace('<b> </b>', '')}]
            else:
                lang = classify(final_content_list[p][0][0])[0]
                if final_content_list[p][0][0].strip() != '':
                    if final_content_list[p][1] in gen_cate_dic:
                        gen_cate_dic[final_content_list[p][1]].append(
                            {lang: final_content_list[p][0][0].replace('<b> </b>', '')})
                    else:
                        gen_cate_dic[final_content_list[p][1]] = [
                            {lang: final_content_list[p][0][0].replace('<b> </b>', '')}]

    return gen_cate_dic


def nutri_table_cnt(table_content_list_all, gen_cate_dic):
    for i in range(0, len(table_content_list_all)):
        for j in range(0, len(table_content_list_all[i])):
            if "percentage daily" in table_content_list_all[i][j].lower():
                split = table_content_list_all[i][j].split("Percentage Daily")
                for cnt in split:
                    #                 print(cnt)
                    if 'intakes' in cnt.lower():
                        lang = classify(str(cnt))[0]
                        if "NUTRITION_TABLE_CONTENT" in gen_cate_dic:
                            gen_cate_dic["NUTRITION_TABLE_CONTENT"].append({lang: "Percentage Daily" + str(cnt)})
                        else:
                            gen_cate_dic["NUTRITION_TABLE_CONTENT"] = [{lang: "Percentage Daily" + str(cnt)}]

    return gen_cate_dic


def nutrition(pdf_file, page_no):
    content_list = []
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[int(page_no) - 1]
        text = page.extract_text().split('\n')
        content_list.append(text)

    cont_list = sum(content_list, [])

    nutri_list = []
    serving_list = []
    nutrit_para_dic = {}
    for i in range(0, len(cont_list)):
        if 'nutrition information' in cont_list[i].lower():
            nutri_list.append(cont_list[i:])
            nutri_list = sum(nutri_list, [])
        elif 'serving size' in cont_list[i].lower() or 'servings per package' in cont_list[i].lower():
            serving_list.append(cont_list[i])

    if not nutri_list:
        for i in range(0, len(cont_list)):
            for k in nutri_keys_para:
                if k in cont_list[i].lower().split()[0]:
                    nutri_list.append(cont_list[i])

    if nutri_list:
        regex_list = []
        for j in range(0, len(nutri_list)):
            for k in nutri_keys_para:
                if k == 'energy' and k in nutri_list[j].lower():
                    regex_list.append(nutri_list[j])
                    if 'cal' in nutri_list[j + 1].lower():
                        item = str(nutri_list[j + 1]) + ' calories'
                        regex_list.append(item)
                    break
                elif k in nutri_list[j].lower():
                    regex_list.append(nutri_list[j])

        para_regex_new_list = []
        for j in regex_list:
            para_reg1 = re.findall(r'(<?\s?(\d+)(\.\d+)?\s?(mg|kj|kJ|g|%|mcg|Cal))', str(j))
            para_regex_new_list.append(para_reg1)

        nutrition_list = []

        for l5 in range(0, len(para_regex_new_list)):
            for m5 in range(0, len(para_regex_new_list[l5])):
                for keys in nutri_keys_para:
                    if keys in regex_list[l5].lower().replace('\xa0', '').replace('\n', ''):
                        if '%' in para_regex_new_list[l5][m5][0]:
                            if keys in nutrit_para_dic:
                                nutrit_para_dic[keys].append({'PDV': {'en': para_regex_new_list[l5][m5][0].strip()}})
                            else:
                                nutrit_para_dic[keys] = [{'PDV': {'en': para_regex_new_list[l5][m5][0].strip()}}]
                        else:
                            if keys in nutrit_para_dic:
                                nutrit_para_dic[keys].append({'Value': {'en': para_regex_new_list[l5][m5][0].strip()}})
                            else:
                                nutrit_para_dic[keys] = [{'Value': {'en': para_regex_new_list[l5][m5][0].strip()}}]

    serving_dic = {}

    for k in range(0, len(serving_list)):
        serv_split = serving_list[k].split(':')
        lang = classify(serv_split[1])[0]
        if serv_split[0] in serving_dic:
            serving_dic[serv_split[0]].append({lang: serv_split[1].strip()})
        else:
            serving_dic[serv_split[0]] = [{lang: serv_split[1].strip()}]
    #     nutrition_list.append(nutrit_para_dic)
    return nutrit_para_dic, serving_dic


def storage_instru(pdf_file, page_no):
    text = extract_text(pdf_file, page_numbers=[int(page_no) - 1])
    txt_list = text.split('\n\n')

    dic = {}
    for i in range(0, len(txt_list)):
        if "storage instructions" in txt_list[i].lower().replace('\n', ''):
            lang = classify(txt_list[i + 1])[0]
            classified_output = classifier.predict(laser.embed_sentences(
                txt_list[i + 1].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', '').replace(
                    '\n', '').lower(), lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(
                txt_list[i + 1].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', '').replace(
                    '\n', '').lower(), lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75 and classified_output == "STORAGE_INSTRUCTIONS":
                if "STORAGE_INSTRUCTIONS" in dic:
                    dic["STORAGE_INSTRUCTIONS"].append({lang: txt_list[i + 1]})
                else:
                    dic["STORAGE_INSTRUCTIONS"] = [{lang: txt_list[i + 1]}]

    return dic


def remove_duplicates(dictionary):
    final_cleaned_dict = {}
    for category, value_list in dictionary.items():
        final_cleaned_dict[category] = sorted(
            list({frozenset(list_element.keys()): list_element for list_element in value_list}.values()),
            key=lambda d: list(d.keys()))
    return final_cleaned_dict


def nutrition_key(dictionary):
    nutri_dic = {}
    for keys, value in dictionary.items():

        classified_output_1 = classifier_key.predict(laser.embed_sentences(
            keys.replace('\xa0', '').replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', ''),
            lang='en'))
        probability_1 = classifier_key.predict_proba(laser.embed_sentences(
            keys.replace('\xa0', '').replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace('<b>', ''),
            lang='en'))
        probability_1.sort()
        prob_1 = probability_1[0][-1]
        if prob_1 > 0.65:
            classified_output_key = classified_output_1[0]
        else:
            classified_output_key = 'None'

        if classified_output_key != 'None':

            if classified_output_key in nutri_dic:

                nutri_dic[classified_output_key].append(value)
            else:
                nutri_dic[classified_output_key] = value

        else:

            if keys in nutri_dic:

                nutri_dic[keys].append(value)
            else:
                nutri_dic[keys] = value

    return nutri_dic


def unilever_pdf_main(pdf_file, page_no):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_docx_location = f'{temp_directory.name}/input_docx.docx'
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    t1 = time.time()
    pdf_file = get_input(pdf_file,input_pdf_location)
    pdf_plumb = pdfplumber.open(pdf_file)
    if int(page_no)-1 in range(len(pdf_plumb.pages)):
        docx_file = pdf_to_docx(pdf_file, page_no,input_docx_location)
        table_content_list = content_list(docx_file)
        final_list = unilever_calssifier(table_content_list)
        ingre_dic = ingredients_dic(table_content_list)
        gen_dic = gen_cate_dic(final_list)
        nutrition_dic, serving_dic = nutrition(pdf_file, page_no)

        if 'NUTRITION_TABLE_CONTENT' not in gen_dic.keys():
            gen_dic = nutri_table_cnt(table_content_list, gen_dic)
        else:
            pass

        nutri_dic = {}
        if nutrition_dic:
            nutrition_list = nutrition_key(nutrition_dic)
            if 'NUTRITION_FACTS' in nutri_dic:
                nutri_dic['NUTRITION_FACTS'].append(nutrition_list)
            else:
                nutri_dic['NUTRITION_FACTS'] = [nutrition_list]
        else:
            pass

        new_gen_dic = remove_duplicates(gen_dic)

        ## New Script for stroage Instruction
        if 'STORAGE_INSTRUCTIONS' in new_gen_dic.keys():
            new_gen_dic.pop('STORAGE_INSTRUCTIONS')

        storage_dic = storage_instru(pdf_file, page_no)

        final_dic = {**new_gen_dic, **nutri_dic, **ingre_dic, **serving_dic, **storage_dic}
        t2 = time.time()
        print(f'Completed in {t2 - t1} secs')
        return final_dic
    else:
        return {}

def unilever_main(pdf_file,pages):
    final_dict={}
    for page in pages.split(","):
        page_response = unilever_pdf_main(pdf_file, int(page))
        final_dict[page] = page_response
    return final_dict