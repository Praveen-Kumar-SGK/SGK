import pdfplumber
import cv2,imutils
from pdf2image import convert_from_path
from sklearn.metrics.pairwise import cosine_similarity
from bs4 import BeautifulSoup
import io
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
from fuzzywuzzy import fuzz
from pdf2docx import parse
import tempfile
import pikepdf
import mammoth
from .nestle_sydney import main
from .Nestle_china import NestleChina
from bidi.algorithm import get_display

from .excel_processing import *

table_check = {'receipe':['recipe'],'nutrition_table':['nutrition information','nutrition information typical values','nutrition declaration']}

nutrition_check = ['dietry fibre','protein','Salt','Saturated fatty acids','carbohydrate','energy','fat']

class Nestle_processing(object):
    def __init__(self):
        self.input_pdf = None
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self.input_pdf_location = f'{self.temp_directory.name}/input_pdf.pdf'
        self.output_io = io.StringIO()
        self.input_file = io.BytesIO()
        self.converted_docx = f'{self.temp_directory.name}/converted.docx'
        self.pdfplumber_pdf = None

    def get_input(self,input_pdf):
        if input_pdf.startswith('\\'):
            print('connecting to SMB share')
            try:
                with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    self.input_file.write(f.read())
                    self.input_file.seek(0)
                    print('file found')
            except:
                smbclient.reset_connection_cache()
                with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    self.input_file.write(f.read())
                    self.input_file.seek(0)
                    print('file found')

            finally:
                smbclient.reset_connection_cache()
                pike_input_pdf = pikepdf.open(self.input_file)
                pike_input_pdf.save(self.input_pdf_location)
            return self.input_pdf_location
        else:
            return document_location+input_pdf

    def pdf_to_image(self,input_pdf):
        images = convert_from_path(input_pdf)
        for index, image in enumerate(images):
            image.save(f'{self.temp_directory.name}/{index + 1}.png')
        return 'success'

    def find_contours(self,input_image):
        im = cv2.imread(input_image)
        height = im.shape[0]
        width = im.shape[1]
        de_img = cv2.GaussianBlur(im, (7, 7), 0)
        can_img = cv2.Canny(de_img, 8, 200, 100)
        cnts = cv2.findContours(can_img.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        cnts1 = imutils.grab_contours(cnts)
        cnts2 = [cnt for cnt in cnts1 if cv2.contourArea(cnt)]
        i = 0
        for contour in cnts2:
            if cv2.contourArea(contour) > 4000:                 # 4000 for lase footer subject localization ...normal : 50000
                x, y, w, h = cv2.boundingRect(contour)
                i = i + 1
                yield (width / (x - 10), height / (y - 10), width / (x + w + 20), height / (y + h + 30))

    def content_inside_bounding_box(self,input_pdf, page_no, coordinates_percent):
        pdf = self.pdfplumber_pdf
        page = pdf.pages[page_no - 1]
        self.pages = len(pdf.pages)                                 #getting total pages
        height, width = float(page.height), float(page.width)
        w0, h0, w1, h1 = coordinates_percent
        coordinates = (width / w0, height / h0, width / w1, height / h1)
        # print(coordinates)
        # print(coordinates)
        ROI = page.within_bbox(coordinates, relative=False)
        table_custom = ROI.extract_tables(
            table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4})
        table_normal = ROI.extract_tables()
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

    def nutrition_or_receipe_table(self,text):
        if str(text).strip():
            for header, value in table_check.items():
                similarity = cosine_similarity(laser.embed_sentences(text, lang='en'),
                                               laser.embed_sentences(value, lang='en').mean(0).reshape(1, 1024))[0][0]
                if similarity > 0.80:
                    return header
            else:
                return False

    def nutrition_table_processing(self,df):
        headings = []
        nutrition_data = {}
        rows, columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows):
                if df[column][row]:
                    header = df[column][row]
                    header = re.sub(r"\(.*\)","",header).strip()
                    output = self.classifier(header)['output']
                    # output = base('ferrero_header', ferrero_header_model).prediction(get_display(header))['output']
                    if output == 'nutrition_header':
                        for col_head in range(columns)[1:]:
                            if df[col_head][row]:
                                if '%' in str(df[col_head][row]):
                                    headings.append('PDV')
                                else:
                                    headings.append('Value')
                    else:
                        for col_head in range(columns)[1:]:
                            if df[col_head][row]:
                                if output in nutrition_data:
                                    nutrition_data[output].append(str(df[col_head][row]))
                                else:
                                    nutrition_data[output] = [str(df[col_head][row])]
        # print('headings------>', headings)
        # print('nutrition_data------>', nutrition_data)
        final_nutrition = {}
        try:
            for nutrient, value_list in nutrition_data.items():
                for index, value in enumerate(value_list):
                    if nutrient in final_nutrition:
                        try:
                            final_nutrition[nutrient].append({headings[index]: {'en': value}})
                        except:
                            final_nutrition[nutrient].append({headings[index - len(headings)]: {'en': value}})
                    else:
                        try:
                            final_nutrition[nutrient] = [{headings[index]: {'en': value}}]
                        except:
                            final_nutrition[nutrient] = [{headings[index - len(headings)]: {'en': value}}]
        except:
            for nutrient, value_list in nutrition_data.items():
                for index, value in enumerate(value_list):
                    if nutrient in final_nutrition:
                        if re.search(r'(kcal|kj|g|mg)',value,re.IGNORECASE):
                            final_nutrition[nutrient].append({'Value': {'en': value}})
                        else:
                            final_nutrition[nutrient].append({'PDV': {'en': value}})
                    else:
                        if re.search(r'(kcal|kj|g|mg)',value,re.IGNORECASE):
                            final_nutrition[nutrient] = [{'Value': {'en': value}}]
                        else:
                            final_nutrition[nutrient] = [{'PDV': {'en': value}}]
        return final_nutrition

    def receipe_table_processing(self,df):
        functional_name = []
        rows, columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows)[1:]:
                if df[column][row]:
                    functional_name.append({'en': df[column][row]})
        return {'FUNCTIONAL_NAME': functional_name}

    def normal_table_processing(self,df,page):
        local_dict = {}
        rows, columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows):
                if df[column][row]:
                    out = self.classifier(str(df[column][row]))
                    output = out['output']
                    probability = out['probability']
                    print(f'{str(df[column][row])}---------->{output}----------->{probability}')
                    if output in nutrition_check:
                        result = self.nutrition_table_processing(df)
                        return result
                    if output not in ['None']:
                        for _col in range(columns)[1:]:
                            if df[_col][row] and df[_col][row] not in ['FOP']:
                                content = None
                                if output == 'ALLERGEN_STATEMENT':
                                    content_modified = self.attribute_checking(str(df[_col][row]),int(page))
                                    if content_modified:
                                        content_modified = re.sub(r'<\D?p>', '', str(content_modified))
                                        content = str(content_modified)
                                        # print(f'attr content----->{content}')
                                else:
                                    content = str(df[_col][row])
                                # print(f'final content---->{output} ----->{content}')
                                # content = str(df[_col][row])
                                if output in local_dict:
                                    local_dict[output].append({'en': content})
                                else:
                                    local_dict[output] = [{'en': content}]
        return local_dict

    def normal_content_processing(self,text):
        if text:
            print()
            output = self.classifier(text)['output']
            print(f'normal processing ----> {text}------>{output}')
            if output not in ['None'] and output in ['INGREDIENTS_DECLARATION','nutrition_table_reference']:
                # print(f'normal processing ----> {text}------>{output}')
                print(f'-------------------------')
                return output
            else:
                return False

    def get_cleantext_from_pdfminer_pdf_to_html(self,input_pdf, input_text):
        if not self.output_io.getvalue():
            with open(self.input_pdf, 'rb') as input:
                extract_text_to_fp(input, self.output_io,
                                   laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                                   output_type='html', codec=None)
        html = BeautifulSoup(self.output_io.getvalue(), 'html.parser')
        # print(html)
        for div in html.find_all('div'):
            # print(div.text)
            score = fuzz.ratio(div.text.lower(), input_text)
            if score > 85:
                return div.text

    def pdf_to_docx_to_html(self,input_pdf, page_no):  # 3
        docx_name = f'{self.temp_directory.name}/{page_no}.docx'
        if not os.path.exists(docx_name):
            parse(input_pdf, docx_name, start=page_no - 1, end=page_no)
        x = mammoth.convert_to_html(docx_name, style_map="b => b").value
        html = BeautifulSoup(x,'html.parser')
        return html

    def classifier(self,text):
        if os.path.exists(nestle_model_location):
            model = joblib.load(nestle_model_location)
        else:
            print('model training')
            df = pd.read_excel(nestle_model_dataset,engine='openpyxl')
            df = df.sample(frac=1)
            X_train_laser = laser.embed_sentences(df['text'], lang='en')
            model = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
                                  random_state=0, shuffle=True)
            model.fit(X_train_laser, df['category'])
            joblib.dump(model, nestle_model_location)
        # lang_detected = classify(text)[0]
        prediction = model.predict(laser.embed_sentences([text], lang='en'))
        probability = model.predict_proba(laser.embed_sentences([text], lang='en'))
        probability[0].sort()
        max_probability = max(probability[0])
        # print(f'max_probability---{text}------>{max_probability}')
        if max_probability > 0.80:
            pred_output = prediction[0]
        else:
            pred_output = 'None'
        return {'probability': max_probability, 'output': pred_output}

    def attribute_checking(self,text,page_no):
        print(f'attr checking text ------>{text}')
        dict_final_attr = {}
        # def try_recursion(_list, index, score, text, src_text):
        #     # text = text
        #     # text = self.get_cleantext_from_pdfminer_pdf_to_html(self.input_pdf,text)
        #     score = score
        #     combine_next_seg = lambda x: ''.join((text, _list[x + 1].text))             # one line function
        #     temp_text = combine_next_seg(index)
        #     temp_score = fuzz.ratio(temp_text.lower(), src_text.lower())
        #     next_index = index + 1
        #     if temp_score > score:
        #         print("======" * 10)
        #         print(f'{temp_text}=======>{temp_score}===========>{next_index}')
        #         print("======" * 10)
        #         try_recursion(_list, next_index, temp_score, temp_text, src_text)
        #     return score, next_index
        html = self.pdf_to_docx_to_html(self.input_pdf,page_no)
        _list = html.find_all('p')
        print("list_item--------->",_list)
        # print(f'html-------> {[t.text for t in _list]}')
        for index, div in enumerate(_list):
            t = div.text
            score = fuzz.ratio(t.lower(), text.lower())
            if score > 95:
                dict_final_attr[int(score)] = str(div)
                continue
            # elif  70 < score > 90:
            elif score >= 40 and score <= 95:
                # temp_score_recur, upto_index_recur = try_recursion(_list, index, score, t, text)
                print(f'{text}------{t}-------->{score}')
                temp_score_recur, upto_index_recur = recursive(_list, index, score, t, text).try_recursion()
                print(f"recursion values---->{temp_score_recur}-------->{upto_index_recur}")
                final_attr_list = [str(li) for li in _list[index:upto_index_recur + 1]]
                final_text =  ' '.join(final_attr_list)
                final_text = re.sub(r"\s\s",'',final_text)
                dict_final_attr[int(temp_score_recur)] =final_text
            else:
                print(f'else score {t} -----> {score}')
                pass
        if dict_final_attr:
            print(f'max dict ----> {dict_final_attr}')
            return dict_final_attr[max(dict_final_attr)]
        else:
            return None

    def main(self,input_pdf, pages):
        if not self.input_pdf:
            self.input_pdf = self.get_input(input_pdf)
            self.pdfplumber_pdf = pdfplumber.open(self.input_pdf)
        final_dict = {}
        pdf_to_image_status = self.pdf_to_image(self.input_pdf)
        assert pdf_to_image_status == 'success', 'pdf to image conversion failed'
        for page in pages.split(','):
            print(f'{page}')
            if int(page)-1 in range(len(self.pdfplumber_pdf.pages)):
                page_dict = {}
                input_image = f'{self.temp_directory.name}/{page}.png'
                for bounding_box in self.find_contours(input_image):
                    for content, type in self.content_inside_bounding_box(self.input_pdf, int(page), bounding_box):
                        # print('------------------------')
                        # print(f'content inside bb----> {content}')
                        # print('------------------------')
                        if type == 'table':
                            df = pd.DataFrame(content[0])
                            if self.nutrition_or_receipe_table(str(df[0][0])) == 'nutrition_table':
                                # nutrition_table.append(nutrition_table_processing(df))
                                result = self.nutrition_table_processing(df)
                                if 'NUTRITION_FACTS' in page_dict:
                                    page_dict['NUTRITION_FACTS'].append(result)
                                else:
                                    page_dict['NUTRITION_FACTS'] = [result]
                            elif self.nutrition_or_receipe_table(str(df[0][0])) == 'receipe':
                                result = self.receipe_table_processing(df)
                                page_dict = {**result, **page_dict}
                            else:
                                result = self.normal_table_processing(df,page)
                                nutri_dict = {}
                                for key,value in result.items():
                                    if key not in nutrition_check:
                                        if key in page_dict:
                                            page_dict[key].extend(value)
                                        else:
                                            page_dict[key] = value
                                    else:
                                        print(f'{key}------>this is nutrition')
                                        nutri_dict[key] = value
                                if nutri_dict:
                                    if 'NUTRITION_FACTS' in page_dict:
                                        page_dict['NUTRITION_FACTS'].append(nutri_dict)
                                    else:
                                        page_dict['NUTRITION_FACTS'] = [nutri_dict]
                                # if 'NUTRITION_FACTS' in page_dict:
                                #     for nutri_table in page_dict['NUTRITION_FACTS']:
                                #         for nutri_header in nutri_table.keys():
                                #             page_dict.pop(nutri_header,None)
                                # page_dict = {**result, **page_dict}
                        elif type == 'content':
                            content_processed = str(content).replace(':', '').replace('\n', ' ').strip()
                            result = self.normal_content_processing(content_processed)
                            if result:
                                # print(f'content------>{content}')
                                content_modified = self.attribute_checking(content,int(page))
                                # print('--------------------------')
                                # print(f'content------>{content_modified}')
                                if content_modified:
                                    content_modified = re.sub(r'<\D?p>', '', str(content_modified))
                                    if result in page_dict:
                                        page_dict[result].append({'en': content_modified})
                                    else:
                                        page_dict[result] = [{'en': content_modified}]
                                else:
                                    if result in page_dict:
                                        page_dict[result].append({'en': str(content)})
                                    else:
                                        page_dict[result] = [{'en': str(content)}]
                            else:
                                if result:
                                    if result in page_dict:
                                        page_dict[result].append({'en': content})
                                    else:
                                        page_dict[result] = [{'en': content}]
                final_dict[int(page)] = page_dict
        self.temp_directory.cleanup()
        self.output_io.close()
        self.input_file.close()
        return final_dict

    def routing(self,file,pages):
        self.input_pdf = self.get_input(file)
        self.pdfplumber_pdf = pdfplumber.open(self.input_pdf)
        page = self.pdfplumber_pdf.pages[0]
        text = page.extract_text()
        if "label copy report" in text.lower() and "general info" in text.lower():
            print("Nestle Manchester")
            return self.main(file,pages)
        elif "product labelling information" in text.lower() or "product detail information" in text.lower():
            print("Nestle Sydney")
            return main(file,pages)
        elif "interoffice memorandum" in text.lower():
            print("Nestle China")
            return NestleChina().main(file,pages)
        else:
            print("not any template")

class recursive(object):
    def __init__(self,_list, index, score, text, src_text):
        self.score = score
        self.index = index
        self._list = _list
        self.text = text
        self.src_text = src_text

    def try_recursion(self):
        combine_next_seg = lambda x: ''.join((self.text, self._list[x + 1].text))             # one line function
        temp_text = combine_next_seg(self.index)
        temp_score = fuzz.ratio(temp_text.lower(), self.src_text.lower())
        if temp_score > self.score:
            self.score = temp_score
            self.index = self.index+1
            self.text = temp_text
            self.try_recursion()
        print(f"return value ========>{self.score}---->{self.index}")
        return self.score, self.index



# import time
#
# start = time.perf_counter()
# ooo = Nestle_processing().main(input_pdf2,'1,2,3,4,5,6,7')
# stop = time.perf_counter()
# print(f'overall time taken ---> {stop-start}')