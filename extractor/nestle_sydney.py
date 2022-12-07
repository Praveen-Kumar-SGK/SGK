import pandas as pd
import numpy as np
from langid import classify
import time
from laserembeddings import Laser
import warnings
import cv2
import imutils
import tempfile
from pdf2image import convert_from_path
import pikepdf
import io
import openpyxl
import sys
from pdfminer.pdfinterp import PDFResourceManager, PDFPageInterpreter
from pdfminer.pdfpage import PDFPage
from pdfminer.converter import XMLConverter, HTMLConverter, TextConverter
from pdfminer.layout import LAParams
import io
from fuzzywuzzy import fuzz , process
from pdfminer.high_level import extract_text_to_fp
from sklearn.neural_network import MLPClassifier

warnings.filterwarnings("ignore")
import joblib
from bs4 import BeautifulSoup
import mammoth
import re
from pdfminer.high_level import extract_text
from pdf2docx import Converter
from pdf2docx import parse
import pdfplumber


from environment import MODE
#
if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

from .excel_processing import *

# path_to_bpe_codes = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/93langs.fcodes'
# path_to_bpe_vocab = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/93langs.fvocab'
# path_to_encoder = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/bilstm.93langs.2018-12-26.pt'

laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)

path = document_location

master_nutrition_keys = ['Calcium',
                         'Calories',
                         'Carbohydrate',
                         'Cholesterol',
                         'Energy',
                         'Fibre',
                         'Fluoride',
                         'Folic acid',
                         'Includes Added Sugars',
                         'Inulin',
                         'Iodine',
                         'Iron',
                         'Magnesium',
                         'Monounsaturated Fat',
                         'Niacin',
                         'Omega 3 fatty acids',
                         'Pantothenic acid',
                         'Phosphorus',
                         'Polydextrose',
                         'Polyols',
                         'Polyunsaturated Fat',
                         'Protein',
                         'Salt',
                         'Saturated Fat',
                         'Selenium',
                         'Sodium',
                         'Starch',
                         'Sugars',
                         'Total Fat',
                         'Trans Fat',
                         'Vitamin A',
                         'Vitamin B1',
                         'Vitamin B12',
                         'Vitamin B2',
                         'Vitamin B6',
                         'Vitamin C',
                         'Vitamin D',
                         'Vitamin E',
                         'Vitamin K',
                         'Zinc',
                         'Potassium',
                         'Total Sugar',
                         'Vitamin B3',
                         'Vitamin B5',
                         'Biotin',
                         'Manganese', 'Copper', 'Dietary Fibre', 'Folate', 'Gluten']


classifier = joblib.load(nestle_sydney_location)

product_details_key = ['Product Name', 'Barcode', 'Date Marking', 'Country of Origin Statement',
                       'Consumer unit']

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
            try:
                print("saving via pikepdf")
                pike_obj = pikepdf.open(input_pdf_location)
                pike_obj.save(input_pdf_location)
            except:
                pass
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        try:
            print("saving via pikepdf")
            pike_obj = pikepdf.open(document_location + input_pdf)
            pike_obj.save(input_pdf_location)
            return input_pdf_location
        except:
            return document_location + input_pdf



def pdf_to_docx(file, pages,converted_docx):
    # convert pdf to docx
    # converted_docx= path + 'nestle_file_p1.docx'
    parse(file,converted_docx, pages=[pages - 1])
    return converted_docx


def docx_content(docx):
    html = mammoth.convert_to_html(docx).value
    soup = BeautifulSoup(html, "html.parser")
    table_content_list_all = []
    for tables in soup.find_all('table'):
        for row in tables.find_all('tr'):
            column_list = []
            for column in row.find_all('td'):
                #             column_list.append(str(column).replace('<td>','').replace('</td>','').replace('</p>','').replace('<p>','').replace('<td colspan="2">','').strip())
                raw_html = str(column).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace('</p>', '\n').replace('<br/>', '\n').strip()
                cleantext = BeautifulSoup(raw_html, "html.parser").text
                column_list.append(cleantext.replace('start_bold', '<b>').replace('end_bold', '</b>').replace('\t', '\n').replace('<','&lt;').replace('>', '&gt;'))
            if column_list not in table_content_list_all:
                table_content_list_all.append(column_list)
    return table_content_list_all



def attribute(input_pdf, pages, text):
    text_out = []
    output_io = io.StringIO()
    with open(input_pdf, 'rb') as input:
        extract_text_to_fp(input, output_io, page_numbers=[int(pages) - 1],
                           laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                           output_type='html', codec=None)

    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    results = html.find_all(
        lambda tag: tag.name == "div" and fuzz.ratio(text.lower(), tag.text.lower().replace('/n', '')) > 80)
    if results:
        if 'bold' in str(results[-1]).lower():
            for span in results[-1]:
                if 'bold' in span['style'].lower():
                    new_text = span.text.split('\n')
                    text_out.append(f'<b>{new_text[0]}</b>')
                if 'bold' not in span['style'].lower():
                    #                 print('yes')
                    new_text = span.text.split('\n')
                    text_out.append(new_text[0])
            # print(' '.join(text_out))
            return ' '.join(text_out)
        else:
            return None


def nestle_calssifier(table_content_list_all):
    final_content_list = []
    serving_list = []
    ingre_dic = {}
    for k in range(0, len(table_content_list_all)):
        print("====="*10)
        print("value----------------->",table_content_list_all[k])
        print("====="*10)
        if table_content_list_all[k]:
            #                 split = table_content_list_all[k][0].split('\n')
            classified_output = classifier.predict(laser.embed_sentences(
                table_content_list_all[k][0].replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n',
                                                                                                        '').lower(),
                lang='en'))
            probability1 = classifier.predict_proba(laser.embed_sentences(
                table_content_list_all[k][0].replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n',
                                                                                                        '').lower(),
                lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            #                 if classified_output in nutri_keys_para:
            if classified_output in master_nutrition_keys:
                if classified_output.lower() == 'energy':
                    contents = [table_content_list_all[k], classified_output.strip()]
                    final_content_list.append(contents)
                    if 'cal' in ('').join(table_content_list_all[k + 1]).lower():
                        contents = [table_content_list_all[k + 1], 'Calories']
                        final_content_list.append(contents)

                else:
                    contents = [table_content_list_all[k], classified_output.strip()]
                    final_content_list.append(contents)

            elif 'servings per pack' in table_content_list_all[k][0].lower() and 'serving size' in \
                    table_content_list_all[k][0].lower():
                serving_list.append(table_content_list_all[k][0])

            elif classified_output in ['INGREDIENTS_DECLARATION', 'NUTRITION_TABLE_CONTENT']:

                lang = classify(table_content_list_all[k][0])[0]
                if classified_output in ingre_dic:
                    ingre_dic[classified_output].append({lang: table_content_list_all[k][0].replace('<b> </b>', '')})
                else:
                    ingre_dic[classified_output] = [{lang: table_content_list_all[k][0].replace('<b> </b>', '')}]

    return final_content_list, ingre_dic, serving_list


def nutrition_dic(final_content_list):
    nutri_dic = {}
    for p in range(0, len(final_content_list)):
        for d in range(1, len(final_content_list[p][0])):
            if final_content_list[p][0][d].strip().lower() not in ['']:
                if 'not detected' in final_content_list[p][0][d].lower():
                    reg1 = re.findall(r'((NOT DETECTED)?\s+?(mg|kj|g|kcal|Kcal|%|mcg|大卡|公克|毫克|克|千卡))',
                                      str(final_content_list[p][0][d]))
                    for txt in reg1:
                        final_content_list[p][0][d] = txt[0]
                        if '%' in final_content_list[p][0][d]:
                            if final_content_list[p][1] in nutri_dic:
                                nutri_dic[final_content_list[p][1]].append({'PDV': {
                                    'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                        '&lt;').replace(
                                        '>', '&gt;')}})
                            else:
                                nutri_dic[final_content_list[p][1]] = [{'PDV': {
                                    'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                        '&lt;').replace(
                                        '>', '&gt;')}}]
                        else:
                            if final_content_list[p][1] in nutri_dic:
                                nutri_dic[final_content_list[p][1]].append({'Value': {
                                    'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                        '&lt;').replace(
                                        '>', '&gt;')}})
                            else:
                                nutri_dic[final_content_list[p][1]] = [{'Value': {
                                    'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                        '&lt;').replace(
                                        '>', '&gt;')}}]
                else:

                    if '%' in final_content_list[p][0][d]:
                        if final_content_list[p][1] in nutri_dic:
                            nutri_dic[final_content_list[p][1]].append({'PDV': {
                                'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                    '&lt;').replace('>',
                                                                                                                    '&gt;').replace(
                                    ' ', '')}})
                        else:
                            nutri_dic[final_content_list[p][1]] = [{'PDV': {
                                'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                    '&lt;').replace('>',
                                                                                                                    '&gt;').replace(
                                    ' ', '')}}]
                    else:
                        if final_content_list[p][1] in nutri_dic:
                            nutri_dic[final_content_list[p][1]].append({'Value': {
                                'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                    '&lt;').replace('>',
                                                                                                                    '&gt;').replace(
                                    ' ', '')}})
                        else:
                            nutri_dic[final_content_list[p][1]] = [{'Value': {
                                'en': final_content_list[p][0][d].strip().replace('\n', '').replace('<',
                                                                                                    '&lt;').replace('>',
                                                                                                                    '&gt;').replace(
                                    ' ', '')}}]
    return nutri_dic


def serving_dic(serving_list):
    serving_dic = {}
    if serving_list:
        split_cnt = re.split('serving size', serving_list[0].lower())
        for cnt in split_cnt:
            if 'servings per pack' in cnt:
                lang = classify(cnt)[0]
                if '&lt;/b&gt;' in cnt:
                    cnt = cnt.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace(':', '').replace(
                        'servings per pack', '')
                    if 'Servings_Per_Package' in serving_dic:
                        serving_dic['Servings_Per_Package'].append({lang: (
                                    '&lt;b&gt;' + str(cnt) + '&lt;/b&gt;').replace('\n',
                                                                                   '&lt;/b&gt;\n&lt;b&gt;').replace(
                            '&lt;b&gt;&lt;/b&gt;', '').strip()})
                    else:
                        serving_dic['Servings_Per_Package'] = [{lang: ('&lt;b&gt;' + str(cnt) + '&lt;/b&gt;').replace(
                            '\n', '&lt;/b&gt;\n&lt;b&gt;').replace('&lt;b&gt;&lt;/b&gt;', '').strip()}]
                else:
                    if 'Servings_Per_Package' in serving_dic:
                        serving_dic['Servings_Per_Package'].append({lang: str(cnt)})
                    else:
                        serving_dic['Servings_Per_Package'] = [{lang: str(cnt)}]
            else:
                lang = classify(cnt)[0]
                if '&lt;/b&gt;' in cnt:
                    cnt = cnt.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace(':', '')
                    if 'Serving_Size' in serving_dic:
                        serving_dic['Serving_Size'].append({lang: ('&lt;b&gt;' + str(cnt) + '&lt;/b&gt;').replace('\n',
                                                                                                                  '&lt;/b&gt;\n&lt;b&gt;').replace(
                            '&lt;b&gt;&lt;/b&gt;', '').strip()})
                    else:
                        serving_dic['Serving_Size'] = [{lang: ('&lt;b&gt;' + str(cnt) + '&lt;/b&gt;').replace('\n',
                                                                                                              '&lt;/b&gt;\n&lt;b&gt;').replace(
                            ' ', '').replace('&lt;b&gt;&lt;/b&gt;', '').strip()}]
                else:
                    if 'Serving_Size' in serving_dic:
                        serving_dic['Serving_Size'].append({lang: str(cnt)})
                    else:
                        serving_dic['Serving_Size'] = [{lang: str(cnt)}]
    return serving_dic


def pdf_content(pdf_file, pages):
    content_list_1 = []
    with pdfplumber.open(pdf_file) as pdf:
        #     for i in range(0,len(pdf.pages)):
        page = pdf.pages[pages - 1]
        #         print(len(pdf.pages))
        text = page.extract_text().replace('<', '&lt;').replace('>', '&gt;').split('\n')
        content_list_1.append(text)
    return content_list_1


def nestle_gen_calssifier(table_content_list_all):
    gen_keys = ['PREPARATION_INSTRUCTIONS', 'STORAGE_INSTRUCTIONS', 'ADDRESS_INFORMATION', 'WARNING_STATEMENTS']
    gen_dic = {}
    for k in range(0, len(table_content_list_all[0])):
        if table_content_list_all[0][k].strip():
            if 'barcode' not in table_content_list_all[0][k].lower():
                #                 split = table_content_list_all[k][0].split('\n')
                classified_output = classifier.predict(laser.embed_sentences(
                    table_content_list_all[0][k].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace(
                        '<b>', '').replace('\n', '').lower(), lang='en'))
                probability1 = classifier.predict_proba(laser.embed_sentences(
                    table_content_list_all[0][k].replace('&lt;', '').replace('&gt;', '').replace('</b>', '').replace(
                        '<b>', '').replace('\n', '').lower(), lang='en'))
                probability1.sort()
                prob1 = probability1[0][-1]
                if prob1 > 0.70:
                    classified_output = classified_output[0]
                else:
                    classified_output = 'None'

                if classified_output in gen_keys:
                    if classified_output == 'ADDRESS_INFORMATION':
                        if 'product name' not in table_content_list_all[0][k].lower():
                            lang = classify(table_content_list_all[0][k])[0]
                            if classified_output in gen_dic:
                                gen_dic[classified_output].append({lang: table_content_list_all[0][k].strip().replace(
                                    '<b> </b>', '').replace('<', '&lt;').replace('>', '&gt;')})
                            else:
                                gen_dic[classified_output] = [{lang: table_content_list_all[0][k].strip().replace(
                                    '<b> </b>', '').replace('<', '&lt;').replace('>', '&gt;')}]
                    else:
                        lang = classify(table_content_list_all[0][k])[0]
                        if classified_output in gen_dic:
                            gen_dic[classified_output].append({lang: table_content_list_all[0][k].strip().replace(
                                '<b> </b>', '').replace('<', '&lt;').replace('>', '&gt;')})
                        else:
                            gen_dic[classified_output] = [{lang: table_content_list_all[0][k].strip().replace(
                                '<b> </b>', '').replace('<', '&lt;').replace('>', '&gt;')}]

                elif classified_output in ['CONTACT_INFORMATION']:
                    if 'call' in table_content_list_all[0][k].lower():
                        lang = classify(table_content_list_all[0][k])[0]
                        if classified_output in gen_dic:
                            gen_dic[classified_output].append({lang: table_content_list_all[0][k].strip().replace(
                                '<b> </b>', '').replace('<', '&lt;').replace('>', '&gt;')})
                        else:
                            gen_dic[classified_output] = [{lang: table_content_list_all[0][k].strip().replace(
                                '<b> </b>', '').replace('<', '&lt;').replace('>', '&gt;')}]

    return gen_dic


def product_details(content_list_1):
    start_idx = 0
    end_idx = 0
    product_dic = {}
    for i in range(0, len(content_list_1[0])):
        for key in product_details_key:
            if key != 'Consumer unit' and key in content_list_1[0][i]:
                split_cnt = content_list_1[0][i].split(key)
                if '(ean)' not in split_cnt[1].lower():
                    if split_cnt[1].strip():
                        lang = classify(split_cnt[1])[0]
                        if key in product_dic:
                            product_dic[key].append({lang: split_cnt[1].strip()})
                        else:
                            product_dic[key] = [{lang: split_cnt[1].strip()}]

            elif key in ['Consumer unit'] and key in content_list_1[0][i]:
                if content_list_1[0][i + 1].strip():
                    lang = classify(content_list_1[0][i + 1])[0]
                    if key in product_dic:
                        product_dic[key].append({lang: content_list_1[0][i + 1].strip()})
                    else:
                        product_dic[key] = [{lang: content_list_1[0][i + 1].strip()}]

            ## Newly added script for product description
            elif 'Date Marking' in content_list_1[0][i]:
                start_idx = i + 1

            elif 'Country of Origin Statement' in content_list_1[0][i]:
                end_idx = i

    product_des = []
    product_des.append(('\n').join(content_list_1[0][start_idx:end_idx]))
    if product_des:
        if 'product description' in product_des[0].lower():
            lang = classify(product_des[0])[0]
            product_des[0] = product_des[0].replace('Product Description', '').replace('\n\n', ' \n ').strip()
            if 'product description' in product_dic:
                product_dic['product description'].append({lang: product_des[0]})
            else:
                product_dic['product description'] = [{lang: product_des[0]}]

    return product_dic


def product_keys(dictionary):
    product_dic = {}
    for keys, value in dictionary.items():
        classified_output_1 = classifier.predict(
            laser.embed_sentences(keys.replace('\xa0', '').replace('&lt;', '').replace('&gt;', ''), lang='en'))
        probability_1 = classifier.predict_proba(
            laser.embed_sentences(keys.replace('\xa0', '').replace('&lt;', '').replace('&gt;', ''), lang='en'))
        probability_1.sort()
        prob_1 = probability_1[0][-1]
        if prob_1 > 0.65:
            classified_output_key = classified_output_1[0]
        else:
            classified_output_key = 'None'

        if classified_output_key != 'None':

            if classified_output_key in product_dic:

                product_dic[classified_output_key].append(value)
            else:
                product_dic[classified_output_key] = value

        else:

            if keys in product_dic:

                product_dic[keys].append(value)
            else:
                product_dic[keys] = value

    return product_dic


def pdf_to_image(input_pdf,image_location):
    images = convert_from_path(input_pdf)
    for index, image in enumerate(images):
        image.save(f'{image_location}/{index + 1}.png')
        # image.save(f'{path}{index + 1}.png')
    return 'success'


def find_contours(input_image):
    # print(input_image)
    im = cv2.imread(input_image)
    height = im.shape[0]
    width = im.shape[1]
    # de_img = cv2.GaussianBlur(im, (7, 7), 0)
    gray_scale = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    gray_scale[gray_scale < 250] = 0
    th1, img_bin = cv2.threshold(gray_scale, 150, 225, cv2.THRESH_BINARY)
    img_bin = ~img_bin
    line_min_width_horizontal = 50
    line_min_width_vertical = 30
    kernal_h = np.ones((1, line_min_width_horizontal), np.uint8)
    kernal_v = np.ones((line_min_width_vertical, 1), np.uint8)
    img_bin_h = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernal_h)
    img_bin_v = cv2.morphologyEx(img_bin, cv2.MORPH_OPEN, kernal_v)
    img_bin_final = img_bin_h | img_bin_v
    final_kernel = np.ones((3, 3), np.uint8)
    img_bin_final_dilation = cv2.dilate(img_bin_final, final_kernel, iterations=1)
    can_img = cv2.Canny(img_bin_final_dilation, 8, 200, 100)
    cnts = cv2.findContours(can_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    cnts1 = imutils.grab_contours(cnts)
    cnts2 = [cnt for cnt in cnts1 if cv2.contourArea(cnt) > 5000]
    i = 0
    for contour in cnts2:
        if cv2.contourArea(contour) > 3000:
            x, y, w, h = cv2.boundingRect(contour)
            i = i + 1
            yield ((width / (x - 10), height / (y - 10), width / (x + w + 20), height / (y + h + 30)))


def content_inside_bounding_box(input_pdf, page_no, coordinates_percent):
    pdf = pdfplumber.open(input_pdf)
    page = pdf.pages[page_no - 1]
    pages = len(pdf.pages)  # getting total pages
    height, width = float(page.height), float(page.width)
    # layout, dim = utils.get_page_layout(self.input_pdf)
    w0, h0, w1, h1 = coordinates_percent
    coordinates = (width / w0, height / h0, width / w1, height / h1)
    # x1,y1,x2,y2 = coordinates
    ROI = page.within_bbox(coordinates, relative=False)
    table_custom = ROI.extract_tables(
        table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4})
    table_normal = ROI.extract_tables()
    # try:
    #     camelot_table = camelot.read_pdf(self.input_pdf,table_regions=[f'{x1},{y1},{x2},{y2}'],pages=str(page_no))
    #     print('camelot_table---->',camelot_table[0].df)
    # except:
    #     pass
    if table_normal and table_custom:
        table_custom_shape = pd.DataFrame(table_custom[0]).shape[1]
        table_normal_shape = pd.DataFrame(table_normal[0]).shape[1]
        if table_normal_shape == table_custom_shape:
            table = table_custom
        elif table_normal_shape > table_custom_shape:
            table = table_normal
        else:
            table = table_custom
        yield (table, 'table')
    elif table_normal and not table_custom:
        table = table_normal
        yield (table, 'table')
    elif table_custom and not table_normal:
        table = table_custom
        yield (table, 'table')
    else:
        content = ROI.extract_text()
        yield (content, 'content')


def img_to_df(input_image, input_pdf, page):
    cnt_list = []
    cnt_dict = {}
    for bounding_box in find_contours(input_image):
        for content, type in content_inside_bounding_box(input_pdf, int(page), bounding_box):
            if type == 'content':
                if isinstance(content, str):
                    # print(content)
                    # print("*******")
                    cnt_list.append(content.replace('<', '&lt;').replace('>', '&gt;'))

    prep_list = []
    for cnt in cnt_list:
        if 'endorsements' in cnt.lower() or 'content claims' in cnt.lower():
            lang = classify(cnt)[0]
            cnt = cnt.replace('\n \n', '\n')
            if 'MARKETING_CLAIM' in cnt_dict:
                cnt_dict['MARKETING_CLAIM'].append({lang: cnt.replace('<', '&lt;').replace('>', '&gt;').strip()})
            else:
                cnt_dict['MARKETING_CLAIM'] = [{lang: cnt.replace('<', '&lt;').replace('>', '&gt;').strip()}]
        else:
            classified_output = classifier.predict(
                laser.embed_sentences(cnt.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', '').lower(),
                                      lang='en'))
            probability1 = classifier.predict_proba(
                laser.embed_sentences(cnt.replace('&lt;b&gt;', '').replace('&lt;/b&gt;', '').replace('\n', '').lower(),
                                      lang='en'))
            probability1.sort()
            prob1 = probability1[0][-1]
            if prob1 > 0.75:
                classified_output = classified_output[0]
            else:
                classified_output = 'None'

            if classified_output in ['PREPARATION_INSTRUCTIONS']:
                split_cnt = cnt.split('\n')
                # print(split_cnt)
                # print("*******")
                for new_cnt in split_cnt:
                    if new_cnt.strip():
                        output = attribute(input_pdf, page, new_cnt)
                        if output:
                            final_txt = output
                        else:
                            final_txt = new_cnt
                        prep_list.append(final_txt)

    if prep_list:
        final_txt = ('\n').join(prep_list)
        lang = classify(final_txt)[0]
        if 'PREPARATION_INSTRUCTIONS' in cnt_dict:
            cnt_dict['PREPARATION_INSTRUCTIONS'].append({lang: final_txt.replace('<', '&lt;').replace('>', '&gt;')})
        else:
            cnt_dict['PREPARATION_INSTRUCTIONS'] = [{lang: final_txt.replace('<', '&lt;').replace('>', '&gt;')}]

        return cnt_dict

    else:
        return cnt_dict


def nestle_pdf_sydney(pdf_file, pages,temp_directory):
    converted_docx = f'{temp_directory.name}/converted.docx'
    t5 = time.time()
    with pdfplumber.open(pdf_file) as pdf:
        if int(pages) <= len(pdf.pages):
            docx_file = pdf_to_docx(pdf_file, pages,converted_docx)
            docx_contents = docx_content(docx_file)
            final_content_list, ingre_dict, serving_list = nestle_calssifier(docx_contents)
            nutri_dict = nutrition_dic(final_content_list)
            serving_dict = serving_dic(serving_list)
            pdf_contents = pdf_content(pdf_file, pages)
            gen_dict = nestle_gen_calssifier(pdf_contents)
            product_dict = product_details(pdf_contents)
            product_keys_dict = product_keys(product_dict)

            ## Pdf to image Convertion
            # cnt_dict = {}
            pdf_to_img_stauts = pdf_to_image(pdf_file,temp_directory.name)
            if pdf_to_img_stauts == 'success':
                input_image = f'{temp_directory.name}/{pages}.png'
                # input_image = path +str(pages)+'.png'

                # print(input_image)
                cnt_dict = img_to_df(input_image,pdf_file,pages)

            new_nutri_dic = {}
            if nutri_dict:
                if 'NUTRITION_FACTS' in new_nutri_dic:
                    if isinstance(nutri_dict, list):
                        new_nutri_dic['NUTRITION_FACTS'].extend(nutri_dict)
                    else:
                        new_nutri_dic['NUTRITION_FACTS'].append(nutri_dict)
                else:
                    if isinstance(nutri_dict, list):
                        new_nutri_dic['NUTRITION_FACTS'] = nutri_dict
                    else:
                        new_nutri_dic['NUTRITION_FACTS'] = [nutri_dict]

            final_dict = {**ingre_dict, **serving_dict, **gen_dict, **product_keys_dict, **new_nutri_dic, **cnt_dict}
            t6 = time.time()
            print(f'Finished in {t6 - t5}seconds')
            return final_dict
        else:
            return {}

def main(pdf_file,pages):
    final_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=path)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    pdf_file = get_input(pdf_file, input_pdf_location)
    for page in pages.split(","):
        page_response = nestle_pdf_sydney(pdf_file,int(page),temp_directory)
        final_dict[page] = page_response
    return final_dict

## In views file, make input pages as int
