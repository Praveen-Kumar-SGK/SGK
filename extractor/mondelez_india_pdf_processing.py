import pandas as pd
import pdfplumber
# from pdf2image import convert_from_path
from sklearn.metrics.pairwise import cosine_similarity
import cv2
import imutils
import tempfile
from bidi.algorithm import get_display
import camelot
from pdf2docx import parse , Converter
import mammoth
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz , process
from termcolor import colored

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

from .excel_processing import *

def content_to_chinese_nutrition_table(df):
    is_nutrition_table = False
    rows, columns = df.shape
    table = []
    for row in range(rows):
        row_values = "\n".join(list(df.loc[row]))
        if "项目" in row_values:
            is_nutrition_table = True
            print("nutrition_table_available")
        elif is_nutrition_table:
            # table_content = "\n".join(list(df.loc[row])).split("\n")
            table_content = row_values.split("\n")
            print("table_content--->",table_content)
            table.append(table_content)
    return pd.DataFrame(table)

class mondelez_india_pdf(object):
    def __init__(self):
        self.input_pdf = None
        self.table_check = ['INFORMASI NILAI GIZI','nutrition information','nutrition information typical values','nutrition declaration']    #indonesian and english
        self.table_check_chinese = ['营养成分表','nutrition']
        self.table_check_thai = ['ข้อมูลโภชนำกำร','ขอ้ มูลโภชนาการ']
        self.table_check_japanese = ['栄養成分表示']
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self.input_pdf_location = f'{self.temp_directory.name}/input_pdf.pdf'
        self.input_pdf_original = f'{self.temp_directory.name}/original.pdf'
        self.converted_docx = f'{self.temp_directory.name}/converted.docx'
        self.bold_contents_tuple = tuple()
        self.bold_contents_dict = {}
        self.pdfplumber_pdf = None
        self.is_nutrition_data_in_table = False

    def get_input(self,input_pdf):
        if input_pdf.startswith('\\'):
            print('connecting to SMB share')
            try:
                with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                    with open(self.input_pdf_location, 'wb') as pdf:
                        pdf.write(f.read())
                    print('file found')
            except:
                smbclient.reset_connection_cache()
                with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                    with open(self.input_pdf_location, 'wb') as pdf:
                        pdf.write(f.read())
                    print('file found')
            finally:
                smbclient.reset_connection_cache()
                import fitz
                doc = fitz.Document(self.input_pdf_location)
                for page in range(doc.page_count):
                    for a in doc[page].annots():
                        print(a.xref)
                        doc[page].delete_annot(a)
                doc.save(self.input_pdf_original,pretty=True)
                print('pdf cleaned')
                return self.input_pdf_original
                # return self.input_pdf_location
        else:
            import fitz
            doc = fitz.Document(document_location+input_pdf)
            for page in range(doc.page_count):
                for a in doc[page].annots():
                    print(a.xref)
                    doc[page].delete_annot(a)
            doc.save(self.input_pdf_original, pretty=True)
            print('pdf cleaned')
            return self.input_pdf_original

    def pdf_to_docx_to_bold_contents(self):
        try:
            parse(self.input_pdf,self.converted_docx)
        except:
            pass
        x = mammoth.convert_to_html(self.converted_docx, style_map="b => b").value
        soup = BeautifulSoup(x, 'html.parser')
        # print(soup)
        main_content = []
        for data in soup.find_all('td'):
            print(str(data))
            print("--------"*10)
            if str(data.text).strip() and '<b>' in str(data):
            # if str(data.text).strip():
                column = str(data)
                column = re.sub(r'<(?!b|\/b)\D{1,3}?>', '', str(column))
                column = re.sub(r'\<\/?br\/?\>', '\n', str(column))
                # column = re.sub(r"\<\/?(td|tr)\b.*\>", "", str(column),flags=re.I).strip()
                column = re.sub(r"\<\/?(td|tr).*?\>", "", str(column),flags=re.I).strip()
                column = re.sub(r"<b>\s*<\/b>","", str(column)).strip()
                print("column----->", column)
                # column = re.sub(r'<\D{1,2}>([^A-Za-z]*)<\/\D{1,2}>', lambda pat: pat.group(1), str(column))
                self.bold_contents_dict[re.sub(r"<.*?>","",column,flags=re.M)] = column
                print("----------"*10)
                main_content.append(column)
        self.bold_contents_tuple = tuple(main_content)
        # print('tuple_content---->',self.bold_contents_tuple)
        return True

    def get_bold_contents(self,text):
        # print('search text------->',text.strip().split("\n"))
        # print(self.bold_contents_dict.keys())
        # content, score = process.extractOne(text,self.bold_contents_tuple ,scorer=fuzz.token_sort_ratio)
        content, score = process.extractOne(text,self.bold_contents_dict.keys(),scorer=fuzz.ratio)
        _, set_score = process.extractOne(text,self.bold_contents_dict.keys(),scorer=fuzz.token_sort_ratio)
        print('score---------->',score,'------->',self.bold_contents_dict[content].strip().split("\n"))
        print("-----"*10)
        print('set_score---------->',set_score,'------->',self.bold_contents_dict[content])
        # print("----->SFJVFSKJNV",abs(len(text.strip().split("\n")) - len(self.bold_contents_dict[content].strip().split("\n"))))
        if score >= 90 or set_score >= 85:
            if abs(len(text.strip().split("\n")) - len(self.bold_contents_dict[content].strip().split("\n"))) > 3:
                print("text replace method")
                for bold_text in re.finditer(r"<b>(.*?)<\/b>", self.bold_contents_dict[content]):
                    text_to_replace = bold_text.group()
                    if not bold_text.group(1) + " " in text:
                        text_to_replace = bold_text.group() + " "
                    if not " " + bold_text.group(1) in text:
                        text_to_replace = " " + bold_text.group()
                    try:
                        text = text.replace(bold_text.group(1),text_to_replace,1)
                    except:
                        text = re.sub(bold_text.group(1),text_to_replace,text)
                    finally:
                        text = re.sub(r" {2,4}"," ",text)
                        text = re.sub(r"\( ","(",text)
                        text = re.sub(r"^ ", "", text, flags=re.M)
                        text = text.strip()
                    return text
            return self.bold_contents_dict[content]
        else:
            return False

    def find_contours(self,input_image):
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
            if cv2.contourArea(contour) > 4000:
                print('hello contour----->',cv2.boundingRect(contour))
                x, y, w, h = cv2.boundingRect(contour)
                i = i + 1
                yield (width / (x - 10), height / (y - 10), width / (x + w + 20), height / (y + h + 30))

    def content_inside_bounding_box(self, page_no, coordinates_percent):
        pdf = pdfplumber.open(self.input_pdf)
        page = pdf.pages[page_no - 1]
        pages = len(pdf.pages)  # getting total pages
        height, width = float(page.height), float(page.width)
        # layout, dim = utils.get_page_layout(self.input_pdf)
        w0, h0, w1, h1 = coordinates_percent
        coordinates = (width / w0, height / h0, width / w1, height / h1)
        x1,y1,x2,y2 = coordinates
        ROI = page.within_bbox(coordinates, relative=False)
        table_custom = ROI.extract_tables(
            table_settings={"vertical_strategy": "lines", "horizontal_strategy": "lines", "snap_tolerance": 4})
        table_normal = ROI.extract_tables()
        try:
            camelot_table = camelot.read_pdf(self.input_pdf,table_regions=[f'{x1},{y1},{x2},{y2}'],pages=str(page_no))
            print('camelot_table---->',camelot_table[0].df)
        except:
            pass
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

    def is_nutrition_table_or_not(self,text):
        similarity = 0
        print("similarity_check_nutri_data--------->",text)
        if isinstance(text, str):
            if '100' in text and '%' in text:
                return True

        if isinstance(text,str):
            _lang = classify(text)[0].lower()
            if 'zh' in _lang:
                print('chinese table')
                table_check = self.table_check_chinese
                threshold = 0.80
            elif 'th' in _lang:
                print('thaii table')
                table_check = self.table_check_thai
                threshold = 0.80
            elif 'ja' in _lang:
                print('japanese table')
                table_check = self.table_check_japanese
                threshold = 0.80
                text = text.split(':')[0]
            else:
                table_check = self.table_check
                threshold = 0.80
            similarity = cosine_similarity(laser.embed_sentences(text, lang='en'),
                                           laser.embed_sentences(table_check, lang='en').mean(0).reshape(1, 1024))[0][0]
            print(text,'----->', similarity)
            if similarity > threshold:
                return True
            else:
                return False
        elif isinstance(text,list):
            text = [t.split('/')[0] for t in text if isinstance(t,str) and t.strip()][::-1]
            if '项目' in " ".join(text):          # rare case (patch work)
                return True
            _lang = classify(' '.join(text))[0].lower()
            if 'zh' in _lang:
                print('chinese table')
                table_check = self.table_check_chinese
            elif 'th' in _lang:
                print('thai table')
                table_check = self.table_check_thai
            elif 'ja' in _lang:
                print('japanese table')
                table_check = self.table_check_japanese
            else:
                print("**********normal table------")
                table_check = self.table_check
            similarity_check = lambda x : cosine_similarity(laser.embed_sentences(x, lang='en'),
                                           laser.embed_sentences(table_check, lang='en').mean(0).reshape(1, 1024))[0][0]
            print(text,'----->', similarity)
            print('similarity check------->',similarity_check(text[-1]))
            if any(similarity_check(t.replace('\n','')) > 0.80 for t in text if t.strip()):
                return True
            else:
                return False

    def is_nutrition_data(self,data):
        sample_text = ['Fat   \nOf which saturates \nCarbohydrate    \nof which sugars   \nFibre   \nProtein   \nSalt   \nEnergy   \nCalories']
        similarity = cosine_similarity(laser.embed_sentences(data, lang='en'),
                                       laser.embed_sentences(sample_text, lang='en').mean(0).reshape(1, 1024))[0][0]
        # print('Nutrition data check =======>',similarity)
        if similarity > 0.80:
            return True
        else:
            return False

    def penang_nutrition_table_data_split(self,table):
        temp_list = []
        for _list in table:
            for header in _list[:1]:
                header = header.strip()
                header = header.replace('\n','')
                print('penang header spliteer---->',header)
                # if re.search(r"^[^A-Za-z\s]*\s?(\d{1,3}\s?[^A-Za-z\s]{1,3})$", header):
                if re.search(r"(^[^A-Za-z\d]*\s?)(\d{1,3}\s?[^A-Za-z\s]{1,3}\.)$", header):
                    splitted_header = list(
                        # re.findall(r"^([^A-Za-z\s]*\s?)(\d{1,3}\s?[^A-Za-z\s]{1,3})$", header.strip())[0])
                        re.findall(r"(^[^A-Za-z\d]*\s?)(\d{1,3}\s?[^A-Za-z\s]{1,3}\.)$", header)[0])
                    splitted_header.extend(_list[1:])
                    temp_list.append(splitted_header)
                    print(splitted_header)
                else:
                    temp_list.append(_list)
        return temp_list

    def mondelez_classifier(self,text,method=None):
        import os
        if method == 'General':
            model_location = mondelez_pdf_general_model_location
            dataset_location = mondelez_dataset
            if os.path.exists(model_location):
                classifier = joblib.load(model_location)
            else:
                dataframe = pd.read_excel(dataset_location, sheet_name='Sheet2',engine='openpyxl')
                x_train_laser = laser.embed_sentences(dataframe['text'], lang='en')
                classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
                                           random_state=0, shuffle=True)
                classifier.fit(x_train_laser, dataframe['category'])
                joblib.dump(classifier, model_location)
        else:
            model_location = mondelez_pdf_model_location
            dataset_location = mondelez_dataset
            if os.path.exists(model_location):
                classifier = joblib.load(model_location)
            else:
                dataframe = pd.read_excel(dataset_location, engine='openpyxl')
                x_train_laser = laser.embed_sentences(dataframe['text'], lang='en')
                classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750,
                                           random_state=0, shuffle=True)
                classifier.fit(x_train_laser, dataframe['category'])
                joblib.dump(classifier, model_location)
        prediction = classifier.predict(laser.embed_sentences([text], lang='en'))
        probability = classifier.predict_proba(laser.embed_sentences([text], lang='en'))
        probability[0].sort()
        max_probability = max(probability[0])
        if max_probability > 0.50:
            pred_output = prediction[0]
        else:
            pred_output = 'None'
        # print('*****'*5)
        # print(text)
        # print(pred_output,'------>',max_probability)
        # print('*****'*5)
        return {'probability': max_probability, 'output': pred_output}

    def nutrition_table_processing(self,nutrition_df,table_type=None):
        nutrition_dict = {}
        nutrition_headings = {}
        serving_size = {}
        if isinstance(nutrition_df,pd.DataFrame):
            rows , columns = nutrition_df.shape
            for column in range(columns)[:1]:
                for row in range(rows):
                    if table_type == 'Normal':
                        nutrition_header = str(nutrition_df[column][row]).strip().lower()
                        if "serving size" in nutrition_header:
                            if "SERVING_SIZE" in serving_size:
                                serving_size["SERVING_SIZE"].append({'en': str(nutrition_df[column][row]).split(":")[-1]})
                            else:
                                serving_size["SERVING_SIZE"] = [{'en': str(nutrition_df[column][row]).split(":")[-1]}]
                        if "servings per" in nutrition_header:
                            if "SERVING_PER_CONTAINER" in serving_size:
                                serving_size["SERVING_PER_CONTAINER"].append({'en': str(nutrition_df[column][row]).split(":")[-1]})
                            else:
                                serving_size["SERVING_PER_CONTAINER"] = [{'en': str(nutrition_df[column][row]).split(":")[-1]}]
                        if nutrition_header in ("项目"):
                            header_list = list(nutrition_df.loc[row])
                            header_list = [header for header in header_list if header and header.strip()]
                            for header in header_list:
                                print("nutrition_header---->", header)
                                if "NUTRI_TABLE_HEADERS" in nutrition_headings:
                                    nutrition_headings["NUTRI_TABLE_HEADERS"].append({'en': header})
                                else:
                                    nutrition_headings["NUTRI_TABLE_HEADERS"] = [{'en': header}]
                            print("nutrition_headings------>",header_list)
                            continue
                        if nutrition_header:
                            nutrition_header = str(nutrition_df[column][row]).split('/')[0]
                            nutrition_header = re.sub(r"\b(mg|g|kcal)","",nutrition_header).strip()
                        elif any(('kcal' in str(nutrition_df[_col][row]).lower() for _col in range(columns)[column + 1:] if str(nutrition_df[_col][row]).strip())):
                            nutrition_header = 'calories'
                        else:
                            continue
                        nutrition_output = base('ferrero_header', mondelez_pdf_plr_nutrition_model_location).prediction(get_display(nutrition_header))
                        print(nutrition_header)
                        if nutrition_output['output'] not in ['None','header','nutrition_table_reference','Nutrition information'] and nutrition_output['probability'] > 0.70 :
                            for _col in range(columns)[column+1:]:
                                value = nutrition_df[_col][row]
                                if isinstance(value,str) and str(nutrition_df[_col][row]).strip():
                                    value = str(nutrition_df[_col][row]).strip()
                                    print("inside--->",value)
                                    value_header = 'PDV' if "%" in value else "Value"
                                    if nutrition_output['output'] in nutrition_dict:
                                        print("appending---->",value)
                                        nutrition_dict[nutrition_output['output']].append({value_header:{'en':value}})
                                    else:
                                        nutrition_dict[nutrition_output['output']] = [{value_header:{'en':value}}]
                            else:
                                # placing copy_notes
                                if nutrition_output['output'] in nutrition_dict:
                                    nutrition_dict[nutrition_output['output']].append({"copy_notes": {'en': str(nutrition_df[column][row])}})
                                else:
                                    nutrition_dict[nutrition_output['output']] = [{"copy_notes": {'en': str(nutrition_df[column][row])}}]
        if serving_size:
            return {"NUTRITION_FACTS":nutrition_dict,**nutrition_headings,**serving_size}
        else:
            return {"NUTRITION_FACTS": nutrition_dict, **nutrition_headings}

    def nutrition_table_processing_old(self,page_no, table_type=None):
        print('inside nutrition table processing')
        nutrition_dict = {}
        nutrition_headings = {}
        serving_size = {}
        # tables = camelot.read_pdf(self.input_pdf, pages=str(page_no), flavor='stream', row_tol=9)
        # tables = camelot.read_pdf(self.input_pdf, pages=str(page_no), flavor='stream', row_tol=9,edge_tol=150)
        tables = camelot.read_pdf(self.input_pdf, pages=str(page_no), flavor='stream', row_tol=9)
        no_of_tables = len(tables)
        nutrition_df = None
        nutrition_start_index = None
        nutrition_table = None
        if no_of_tables < len(camelot.read_pdf(self.input_pdf,flavor="lattice",pages=str(page_no))):
            for table in tables:
                temp_nutri_df = table.df
                print("lattice tables----->",table.df.values.tolist())
                rows,columns = temp_nutri_df.shape
                for row in range(rows):
                    if "项目" in temp_nutri_df.loc[row].to_list() or "项目" in " ".join(temp_nutri_df.loc[row].to_list()):
                        print("chinese table found")
                        nutrition_start_index = row
                        nutrition_table = temp_nutri_df
            if nutrition_start_index:
                nutrition_df = nutrition_table.loc[nutrition_start_index:]
                nutrition_df.columns = range(nutrition_df.shape[1])
                nutrition_df = nutrition_df.reset_index(drop=True)
                if isinstance(nutrition_df,pd.DataFrame) and "\n" in nutrition_df[0][0]:
                    nutrition_df_chinese = content_to_chinese_nutrition_table(nutrition_table)
                    if isinstance(nutrition_df_chinese, pd.DataFrame):
                        nutrition_df = nutrition_df_chinese
                print("stripped table---->", nutrition_df)
            # print("busssssss---->",list(tables[0].df.iloc[:, 0]))
            # if "项目" in list(tables[0].df.iloc[:, 0]):
            #     for index,value in enumerate(list(tables[0].df.iloc[:, 0])):
            #         if value.strip() == "项目":
            #             nutrition_df = tables[0].df.loc[index:]
            #             nutrition_df.columns = range(nutrition_df.shape[1])
            #             nutrition_df = nutrition_df.reset_index(drop=True)
            #             print("stripped table---->",nutrition_df)
        if not isinstance(nutrition_df,pd.DataFrame):
            for table_no in range(no_of_tables):
                print(f"{table_no}------>",tables[table_no].df)
                table = tables[table_no].data
                table = self.penang_nutrition_table_data_split(table)
                # df = tables[table_no].df
                df = pd.DataFrame(table)
                # if self.is_nutrition_table_or_not(str(df[0][0]).split('/')[0]):
                if self.is_nutrition_table_or_not(df.loc[0].to_list()):
                    print(df)
                    nutrition_df = df

        if isinstance(nutrition_df,pd.DataFrame):
            rows , columns = nutrition_df.shape
            for column in range(columns)[:1]:
                for row in range(rows):
                    if table_type == 'Normal':
                        nutrition_header = str(nutrition_df[column][row]).strip().lower()
                        if "serving size" in nutrition_header:
                            if "SERVING_SIZE" in serving_size:
                                serving_size["SERVING_SIZE"].append({'en': str(nutrition_df[column][row]).split(":")[-1]})
                            else:
                                serving_size["SERVING_SIZE"] = [{'en': str(nutrition_df[column][row]).split(":")[-1]}]
                        if "servings per" in nutrition_header:
                            if "SERVING_PER_CONTAINER" in serving_size:
                                serving_size["SERVING_PER_CONTAINER"].append({'en': str(nutrition_df[column][row]).split(":")[-1]})
                            else:
                                serving_size["SERVING_PER_CONTAINER"] = [{'en': str(nutrition_df[column][row]).split(":")[-1]}]
                        if nutrition_header in ("项目"):
                            header_list = list(nutrition_df.loc[row])
                            header_list = [header for header in header_list if header and header.strip()]
                            for header in header_list:
                                print("nutrition_header---->", header)
                                if "NUTRI_TABLE_HEADERS" in nutrition_headings:
                                    nutrition_headings["NUTRI_TABLE_HEADERS"].append({'en': header})
                                else:
                                    nutrition_headings["NUTRI_TABLE_HEADERS"] = [{'en': header}]
                            print("nutrition_headings------>",header_list)
                            continue
                        if nutrition_header:
                            nutrition_header = str(nutrition_df[column][row]).split('/')[0]
                        elif any(('kcal' in str(nutrition_df[_col][row]).lower() for _col in range(columns)[column + 1:] if str(nutrition_df[_col][row]).strip())):
                            nutrition_header = 'calories'
                        else:
                            continue
                        nutrition_output = base('ferrero_header', mondelez_pdf_plr_nutrition_model_location).prediction(get_display(nutrition_header))
                        print(nutrition_header)
                        if nutrition_output['output'] not in ['None','header','nutrition_table_reference'] and nutrition_output['probability'] > 0.70 :
                            for _col in range(columns)[column+1:]:
                                value = nutrition_df[_col][row]
                                if isinstance(value,str) and str(nutrition_df[_col][row]).strip():
                                    value = str(nutrition_df[_col][row]).strip()
                                    print("inside--->",value)
                                    value_header = 'PDV' if "%" in value else "Value"
                                    if nutrition_output['output'] in nutrition_dict:
                                        print("appending---->",value)
                                        nutrition_dict[nutrition_output['output']].append({value_header:{'en':value}})
                                    else:
                                        nutrition_dict[nutrition_output['output']] = [{value_header:{'en':value}}]
                            else:
                                # placing copy_notes
                                if nutrition_output['output'] in nutrition_dict:
                                    nutrition_dict[nutrition_output['output']].append({"copy_notes": {'en': str(nutrition_df[column][row])}})
                                else:
                                    nutrition_dict[nutrition_output['output']] = [{"copy_notes": {'en': str(nutrition_df[column][row])}}]
                    else:
                        print("nutrition table not normal process")
                        header = str(nutrition_df[column][row]).strip()
                        header = re.sub(r"\(.*\)", '', header)
                        if header and 'serving' not in header.lower():
                            nutrition_header = re.findall(r"^\n?([A-Za-z].*)\s?\/", header, re.I | re.MULTILINE)
                            # print('nutrition_header----->', nutrition_header)
                            if nutrition_header:
                                nutrition_header = nutrition_header[0]
                                value = re.findall(r"(\<?s?\d?\.?\d{1,2}\s?(g|kj|kcal|mg|mcg))",str(nutrition_df[column][row]), re.I)
                                # print('value------>', value)
                                if value:
                                    value_header_regex = "PDV" if "%" in value else "Value"
                                    value = value[0][0]
                                    if value.strip():
                                        if nutrition_header in nutrition_dict:
                                            nutrition_dict[nutrition_header].append({value_header_regex: {'en': value}})
                                        else:
                                            nutrition_dict[nutrition_header] = [{value_header_regex: {'en': value}}]
                                for _col in range(columns)[column + 1:]:
                                    value = nutrition_df[_col][row]
                                    if isinstance(value,str) and str(nutrition_df[_col][row]).strip():
                                        value = str(nutrition_df[_col][row]).strip()
                                        value_header = 'PDV' if "%" in value else "Value"
                                        if nutrition_header in nutrition_dict:
                                            nutrition_dict[nutrition_header].append({value_header: {'en': value}})
                                        else:
                                            nutrition_dict[nutrition_header] = [{value_header: {'en': value}}]
        # print('Nutrition_dictionary---->',nutrition_dict)
        if nutrition_dict:
            if serving_size:
                return {"NUTRITION_FACTS":nutrition_dict,**nutrition_headings,**serving_size}
            else:
                return {"NUTRITION_FACTS": nutrition_dict, **nutrition_headings}
        # else:
        #     return {}

    def normal_table_processing(self,df):
        normal_dict = {}
        nutrition_dict = {}
        rows , columns = df.shape
        # print(df)
        if columns == 1:
            print('inside column 1 ---- normal table')
            for column in range(columns)[:1]:
                for row in range(rows):
                    header = str(df[column][row]).strip()
                    # cleaned_header = re.sub(r"\(.*\)",'',header)
                    # cleaned_header = cleaned_header.split('/')[0]
                    classifier_output = self.mondelez_classifier(get_display(header),method='General')
                    # lang = classify(header)[0]
                    try:
                        lang = lang_detect(header)
                    except:
                        lang = classify(header)[0]
                    # print('detected sentence---->', header)
                    print(classifier_output['output'], '------>', classifier_output['probability'])
                    # classifier_output = base('general', model_location).prediction(get_display(cleaned_header))
                    if classifier_output['output'] in ['INGREDIENTS_DECLARATION','ALLERGEN_STATEMENT'] and classifier_output['probability'] > 0.70:
                        # print('detected sentence---->', header)
                        header = re.sub(r"(\s?\n\s{0,1}){2,5}\n?","\n",header)
                        bold_content = self.get_bold_contents(header)
                        print("original_content------>",header)
                        print("bold_content------>",bold_content)
                        if bold_content:
                            header = bold_content
                        header = str(header).replace('<', '&lt;').replace('>', '&gt;')
                        if 'INGREDIENTS_DECLARATION' in normal_dict:
                            normal_dict['INGREDIENTS_DECLARATION'].append({lang: header})
                        else:
                            normal_dict['INGREDIENTS_DECLARATION'] = [{lang: header}]
                    else:
                        header = str(header).replace('<', '&lt;').replace('>', '&gt;')
                        if 'OTHER_INSTRUCTIONS' in normal_dict:
                            normal_dict['OTHER_INSTRUCTIONS'].append({lang: header})
                        else:
                            normal_dict['OTHER_INSTRUCTIONS'] = [{lang: header}]
        else:
            print('more than one column')
            print(df)
            for column in range(columns)[:1]:
                for row in range(rows):
                    if isinstance(df[column][row],str):
                        header = str(df[column][row]).strip()
                        cleaned_header = re.sub(r"\(.*\)",'',header)
                        cleaned_header = cleaned_header.split('/')[0].replace("-"," ")
                        classifier_output = self.mondelez_classifier(get_display(cleaned_header))
                        print(colored(f"result------->{classifier_output}----->{cleaned_header}",'blue'))
                        if header:
                            if classifier_output['output'] not in ['None'] and classifier_output['probability'] > 0.70:
                                # if classifier_output['output'] in ['BRAND_NAME','VARIANT','FUNCTIONAL_NAME','NET_CONTENT_STATEMENT','LOCATION_OF_ORIGIN','SERVING_SIZE','SERVING_PER_CONTAINER']:
                                if classifier_output['output'] in ['BRAND_NAME','VARIANT','FUNCTIONAL_NAME','NET_CONTENT_STATEMENT','LOCATION_OF_ORIGIN']:
                                    for _col in range(columns)[column+1:]:
                                        content = df[_col][row]
                                        if isinstance(content,str) and str(content).strip():
                                            bold_content = self.get_bold_contents(str(content))
                                            if bold_content:
                                                content = bold_content
                                                # content = re.sub(r"<.*?>:\s?<.*?>",":",str(content),flags=re.M)
                                            if re.search(r"(\b[A-Z]{2}:)",content,re.M) or re.search(r"(^[A-Z]{2}\s?:)",re.sub(r"\<.*?\>","",str(content)),re.M):
                                                print('inside multi language split')
                                                print(content)
                                                # content = re.sub(r"\b(([A-Z]{2})?\/?[A-Z]{2}:)",lambda pat: "**"+pat.group(1),content,re.MULTILINE)
                                                content = re.sub(r"\b(([A-Z]{2})?\/?[A-Z]{2}:)",lambda pat: "**"+pat.group(1),re.sub(r"\<b\>:\s*?\<\/?b\>",":",content),flags=re.MULTILINE)
                                                print(content)
                                                for splitted in content.split('**'):
                                                    print("splitted_text---->",splitted)
                                                    print("------"*10)
                                                    splitted = str(splitted).replace('<', '&lt;').replace('>', '&gt;')
                                                    splitted = splitted.strip()
                                                    if splitted and isinstance(splitted,str):
                                                        try:
                                                            lang = lang_detect(splitted)
                                                        except:
                                                            lang = classify(splitted)[0]
                                                        if classifier_output['output'] in normal_dict:
                                                            normal_dict[classifier_output['output']].append({lang:splitted})
                                                        else:
                                                            normal_dict[classifier_output['output']] = [{lang:splitted}]
                                            elif re.search(r"\.\s",content):
                                                print("second_elif statement")
                                                for splitted in content.split('.'):
                                                    splitted = str(splitted).replace('<', '&lt;').replace('>', '&gt;')
                                                    splitted = splitted.strip()
                                                    if splitted and isinstance(splitted,str):
                                                        try:
                                                            lang = lang_detect(splitted)
                                                        except:
                                                            lang = classify(splitted)[0]
                                                        if classifier_output['output'] in normal_dict:
                                                            normal_dict[classifier_output['output']].append({lang:splitted})
                                                        else:
                                                            normal_dict[classifier_output['output']] = [{lang:splitted}]
                                            else:
                                                print("second else statement")
                                                for splitted in content.split('\n'):
                                                    splitted = splitted.strip()
                                                    splitted = str(splitted).replace('<', '&lt;').replace('>', '&gt;')
                                                    if splitted and isinstance(splitted,str):
                                                        try:
                                                            lang = lang_detect(splitted)
                                                        except:
                                                            lang = classify(splitted)[0]
                                                        if classifier_output['output'] in normal_dict:
                                                            normal_dict[classifier_output['output']].append({lang:splitted})
                                                        else:
                                                            normal_dict[classifier_output['output']] = [{lang:splitted}]
                                else:
                                    for _col in range(columns)[column+1:]:
                                        content = df[_col][row]
                                        if isinstance(content,str) and str(content).strip():
                                            bold_content = self.get_bold_contents(str(content))
                                            if bold_content:
                                                content = bold_content
                                            content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                            print('final_content-------->',content)
                                            try:
                                                lang = lang_detect(content)
                                            except:
                                                lang = classify(content)[0]
                                            if classifier_output['output'] in normal_dict:
                                                normal_dict[classifier_output['output']].append({lang:content})
                                            else:
                                                normal_dict[classifier_output['output']] = [{lang:content}]
                                            print(colored(normal_dict,'yellow'))
                            elif self.is_nutrition_data(header):            # Nutrition data processing
                                print('inside nutrition data in normal table')
                                header_column = header.split('\n')
                                overall_columns = [header_column]
                                value_column = []
                                for _col in range(columns)[column + 1:]:
                                    content = df[_col][row]
                                    if str(content).strip() and isinstance(content,str):
                                        value_column_content = content.split('\n')
                                        value_column_content = [value.strip() for value in value_column_content]
                                        if len(value_column_content) == len(header_column):
                                            value_column.append(value_column_content)
                                        else:
                                            value_column.clear()
                                            break
                                if value_column:
                                    overall_columns.extend(value_column)
                                    # print('overall_columns--->',overall_columns)
                                    df = pd.DataFrame(overall_columns).transpose()
                                    rows, columns = df.shape
                                    nutrition_dict = {}
                                    for column in range(columns)[:1]:
                                        for row in range(rows)[1:]:
                                            nutrition_header = str(df[column][row]).strip().lower()
                                            if nutrition_header:
                                                nutrition_header = str(df[column][row]).split('/')[0]
                                            elif any(('kcal' in str(df[_col][row]).lower() for _col in
                                                      range(columns)[column + 1:] if str(df[_col][row]).strip())):
                                                nutrition_header = 'calories'
                                            else:
                                                continue
                                            nutrition_output = base('ferrero_header', ferrero_header_model).prediction(
                                                get_display(nutrition_header))
                                            if nutrition_output['output'] not in ['None'] and nutrition_output[
                                                'probability'] > 0.20:
                                                for _col in range(columns)[column + 1:]:
                                                    value = str(df[_col][row]).strip()
                                                    if value:
                                                        value_header = 'PDV' if "%" in value else "Value"
                                                        if nutrition_output['output'] in nutrition_dict:
                                                            nutrition_dict[nutrition_output['output']].append(
                                                                {value_header: {'en': value}})
                                                        else:
                                                            nutrition_dict[nutrition_output['output']] = [
                                                                {value_header: {'en': value}}]
                                    if 'NUTRITION_FACTS' in normal_dict:
                                        normal_dict['NUTRITION_FACTS'].append(nutrition_dict)
                                    else:
                                        normal_dict['NUTRITION_FACTS'] = [nutrition_dict]
                            elif self.is_nutrition_data_in_table:
                                nutrition_output = base('ferrero_header', ferrero_header_model).prediction(get_display(header))
                                if nutrition_output['output'] not in ['None','header'] and nutrition_output['probability'] > 0.70:
                                    for _col in range(columns)[column + 1:]:
                                        value = df[_col][row]
                                        if isinstance(value,str) and str(df[_col][row]).strip():
                                            value = str(df[_col][row]).strip()
                                            value_header = 'PDV' if "%" in value else "Value"
                                            if nutrition_output['output'] in nutrition_dict:
                                                nutrition_dict[nutrition_output['output']].append({value_header:{'en':value}})
                                            else:
                                                nutrition_dict[nutrition_output['output']] = [{value_header:{'en':value}}]
                                print('nutrition dict irukuda')
                                print(nutrition_dict)
                            else:
                                if self.is_nutrition_table_or_not(header) or "NEST TABLE" in header:
                                    print("------"*3)
                                    print(colored("header_check---->","red"),'------>',colored(header,"yellow"))
                                    print("------"*3)
                                    self.is_nutrition_data_in_table = True
                                else:
                                    print('inside else statement and when prob is less than 70 ans not a nutritional table')
                                    if isinstance(df[column+1][row],str) and str(df[column+1][row]).strip():
                                        content = df[column+1][row]
                                        classifier_output = self.mondelez_classifier(content,method='General')
                                        print(classifier_output,'-------->',content)
                                        try:
                                            lang = lang_detect(content)
                                        except:
                                            lang = classify(content)[0]
                                        if classifier_output['probability'] > 0.90:
                                            content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                            if classifier_output['output'] in normal_dict:
                                                normal_dict[classifier_output['output']].append({lang:content})
                                            else:
                                                normal_dict[classifier_output['output']] = [{lang:content}]
                                        # else:
                                        #     content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                        #     if "OTHER_INSTRUCTIONS" in normal_dict:
                                        #         normal_dict["OTHER_INSTRUCTIONS"].append({lang:content})
                                        #     else:
                                        #         normal_dict["OTHER_INSTRUCTIONS"] = [{lang:content}]
                        else:
                            print('inside none exception')
                            for _col in range(columns)[column + 1:]:
                                content = df[_col][row]
                                print(content)
                                if isinstance(content,str) and str(content).strip():
                                    classifier_output = self.mondelez_classifier(get_display(content),method='General')
                                    print(classifier_output)
                                    # lang = classify(content)[0]
                                    try:
                                        lang = lang_detect(content)
                                    except:
                                        lang = classify(content)[0]
                                    if classifier_output['output'] in ['INGREDIENTS_DECLARATION', 'ALLERGEN_STATEMENT'] and classifier_output['probability'] > 0.70:
                                        content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                        if 'INGREDIENTS_DECLARATION' in normal_dict:
                                            normal_dict['INGREDIENTS_DECLARATION'].append({lang: content})
                                        else:
                                            normal_dict['INGREDIENTS_DECLARATION'] = [{lang: content}]
                                    else:
                                        content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                        if 'OTHER_INSTRUCTIONS' in normal_dict:
                                            normal_dict['OTHER_INSTRUCTIONS'].append({lang: content})
                                        else:
                                            normal_dict['OTHER_INSTRUCTIONS'] = [{lang: content}]
                    else:
                        for _col1 in range(columns)[column + 1:column + 2]:
                            if isinstance(df[_col1][row],str):
                                if self.is_nutrition_data(df[_col1][row]):
                                    header_column = str(df[_col1][row]).split('\n')
                                    overall_columns = [header_column]
                                    value_column = []
                                    for _col in range(columns)[_col1 + 1:]:
                                        content = df[_col][row]
                                        # print(content)
                                        if str(content).strip() and isinstance(content, str):
                                            value_column_content = content.split('\n')
                                            value_column_content = [value.strip() for value in value_column_content]
                                            if len(value_column_content) == len(header_column):
                                                value_column.append(value_column_content)
                                            else:
                                                value_column.clear()
                                                break
                                    # print(value_column)
                                    if value_column:
                                        overall_columns.extend(value_column)
                                        # print('overall_columns--->',overall_columns)
                                        df = pd.DataFrame(overall_columns).transpose()
                                        # print(df)
                                        rows, columns = df.shape
                                        nutrition_dict = {}
                                        for column in range(columns)[:1]:
                                            for row in range(rows)[1:]:
                                                nutrition_header = str(df[column][row]).strip().lower()
                                                if nutrition_header:
                                                    nutrition_header = str(df[column][row]).split('/')[0]
                                                    nutrition_header = re.sub(r"\b(g|mg|kcal|kj)\b", "", nutrition_header)
                                                elif any(('kcal' in str(df[_col][row]).lower() for _col in
                                                          range(columns)[column + 1:] if str(df[_col][row]).strip())):
                                                    nutrition_header = 'calories'
                                                else:
                                                    continue
                                                nutrition_output = base('ferrero_header', ferrero_header_model).prediction(
                                                    get_display(nutrition_header))
                                                if nutrition_output['output'] not in ['None'] and nutrition_output[
                                                    'probability'] > 0.20:
                                                    for _col in range(columns)[column + 1:]:
                                                        value = str(df[_col][row]).strip()
                                                        if value:
                                                            value_header = 'PDV' if "%" in value else "Value"
                                                            if nutrition_output['output'] in nutrition_dict:
                                                                nutrition_dict[nutrition_output['output']].append(
                                                                    {value_header: {'en': value}})
                                                            else:
                                                                nutrition_dict[nutrition_output['output']] = [
                                                                    {value_header: {'en': value}}]
                                        print('finisjed--------->',nutrition_dict)
                                        if 'NUTRITION_FACTS' in normal_dict:
                                            normal_dict['NUTRITION_FACTS'].append(nutrition_dict)
                                        else:
                                            normal_dict['NUTRITION_FACTS'] = [nutrition_dict]
                                            # '''
        self.is_nutrition_data_in_table = False
        if nutrition_dict:
            normal_dict['Nutrition'] = nutrition_dict
        return normal_dict

    def check_nan(self,text):
        if isinstance(text, str) and str(text).strip():
            return text
        else:
            return np.nan

    def check_nan_replace_next_column(self,df):
        df_copy = df.copy()
        rows, columns = df.shape
        for column in range(columns):
            for row in range(rows):
                if pd.isna(df[column][row]):
                    try:
                        if isinstance(df[column + 1][row], str):
                            df.iloc[row, column] = df.iloc[row, column + 1]
                            df.iloc[row, column + 1] = np.nan
                    except:
                        pass
        return df_copy

    def get_tables(self,input_pdf, page_no):
        camelot_tables = []
        cv = Converter(input_pdf)
        tables = cv.extract_tables(start=page_no - 1, end=page_no)
        cv.close()
        print("tables------>",tables)
        print(colored(f"tables count------>{len(tables)}","red"))
        cam_table_to_skip = []
        camelot_tables_by_border = camelot.read_pdf(input_pdf,pages=str(page_no),lattice=True)
        # camelot_tables = camelot.read_pdf(input_pdf,pages=str(page_no),flavor="stream")
        for table in tables:
            table_df = pd.DataFrame(table)
            if "<NEST TABLE>" in table_df[0][0] or "nutrition information*" in "".join(table_df[0].apply(func=str)).lower() :
                continue
            elif len(table_df.columns) == 1:
                camelot_tables.append(table)
                continue
            else:
                combination_passed = False
                for idx,cam_tab in enumerate(camelot_tables_by_border):
                    # if str(table_df[0][0]) in cam_tab.df[0][0]:
                    print(colored(f"score_checking--------->{table_df[0][0]}------{cam_tab.df[0][0]}","red"))
                    if str(table_df[0][0]).strip() and fuzz.ratio(str(table_df[0][0]).replace(" ","").strip(),str(cam_tab.df[0][0]).replace(" ","").strip()) > 90:
                        print(colored(f"passed----->{idx}","green"))
                        camelot_tables.append(table)
                        cam_table_to_skip.append(idx)
                        combination_passed = True
                        break
                    elif len(table_df.index) == 1 and not str(table_df[0][0]).strip():
                        if fuzz.ratio(str("".join(table_df.loc[0].to_list())).strip(),str("".join(cam_tab.df.loc[0].to_list())).strip()) > 90:
                            camelot_tables.append(table)
                            cam_table_to_skip.append(idx)
                            combination_passed = True
                            break
                    elif not str(table_df[0][0]).strip() and len(table_df.index) > 1:
                        if str(table_df[0][0]).strip() and fuzz.ratio(str("".join(table_df[0].apply(func=str)).lower()).replace(" ", "").strip(),str("".join(cam_tab.df[0].apply(func=str)).lower()).replace(" ","").strip()) > 90:
                            print(colored(f"passed----->{idx}", "green"))
                            camelot_tables.append(table)
                            cam_table_to_skip.append(idx)
                            combination_passed = True
                            break
                else:
                    if not combination_passed:
                        camelot_tables.append(table)
                        print(colored(f"table not captured in camelot", "green"))

        camelot_tables_by_border_cleaned = []
        for idx, cam_tab in enumerate(camelot_tables_by_border):
            if idx not in cam_table_to_skip:
                camelot_tables_by_border_cleaned.append(cam_tab)

        for can_tab_count,cam_tab in enumerate(camelot_tables_by_border_cleaned):
            first_col = [cam_tab.cols[0][0],cam_tab.cols[-1][-1]]
            last_row = [cam_tab.rows[0][0],cam_tab.rows[-1][-1]]
            coordinates_int = [first_col[0],last_row[0],first_col[-1],last_row[-1]]
            table_stream = camelot.read_pdf(input_pdf, flavor="stream", pages=str(page_no), table_areas=[f'{coordinates_int[0]},{int(coordinates_int[1])},{coordinates_int[2]},{coordinates_int[3]}'])
            table_stream_df = table_stream[0].df
            print("first dataframe------>",table_stream_df)
            if "nutrition information*" in "".join(table_stream[0].df[0].apply(func=str)).lower() and "energy" not in "".join(table_stream[0].df[0].apply(func=str)).lower():
                table_stream_df = table_stream_df.iloc[:,table_stream_df.columns[1]:]
                # table_stream_list = [["NUTRITION INFORMATION"]].extend(table_stream_df.values.tolist())
                table_stream_list = table_stream_df.values.tolist()
                table_stream_list.insert(0,["NUTRITION INFORMATION"])
            else:
                table_stream_list = table_stream_df.values.tolist()
            camelot_tables.append(table_stream_list)
            print("-------"*10)
        table_count = 0

        for table in camelot_tables:
            print("table_number--->",table_count)
            print(colored(page_no,'yellow'))
            print("table_heading----->",table[0][0])
            print(colored(table,'red'))
            df = pd.DataFrame(table)
            rows , columns = df.shape
            if "<NEST TABLE>" in df[0][0] and columns > 1:
            # if "<NEST TABLE>" in df[0][0]:
                print("inside if condition")
                try:
                    cam_table = camelot_tables[table_count].df.values.tolist()
                    print("table picked from camelot")
                    print(colored(cam_table, 'yellow'))
                    yield cam_table
                except:
                    yield table
                finally:
                    table_count = table_count + 1
            elif columns > 1:
                table_count = table_count + 1
                yield table
            else:
                print("inside else condition")
                yield table

    def table_category(self,table):
        df = pd.DataFrame(table)
        df1 = df.copy(deep=True)
        ori_rows, ori_columns = df1.shape
        df = df.applymap(self.check_nan)
        self.check_nan_replace_next_column(df)
        df.dropna(axis=1, how='all', inplace=True)
        df.dropna(axis=0, how='all', inplace=True)
        rows, columns = df.shape
        if (rows, columns) == (ori_rows, ori_columns):
            if columns == 1 and rows == 1:
                yield (table[0][0], 'content')
            elif columns == 1 and rows > 1:
                content = []
                for row in list(df.index):
                    content.append(" ".join([value for value in df.loc[row].tolist() if value]))
                content = "\n".join(content)
                print("content_extracted- new---->", content)
                yield (content, "content")
            else:
                yield (table, 'table')
        else:
            if columns == 1 and rows == 1:
                yield (df.values[0][0], 'content')
            elif columns == 1 and rows > 1:
                content = []
                for row in list(df.index):
                    content.append(" ".join([value for value in df.loc[row].tolist() if value]))
                content = "\n".join(content)
                print("content_extracted- new---->", content)
                yield (content, "content")
            else:
                yield (df.values, 'table')

    def main(self,input_pdf,pages):
        final_dict = {}
        self.input_pdf = self.get_input(input_pdf)
        self.pdfplumber_pdf = pdfplumber.open(self.input_pdf)
        # diverting plr pdf to plr code
        extracted_text = self.pdfplumber_pdf.pages[0].extract_text()
        self.pdf_to_docx_to_bold_contents()
        for page in pages.split(','):
            print(f'{page}')
            if int(page)-1 in range(len(self.pdfplumber_pdf.pages)):
                page_dict = {}
                nutrition_linear_format = re.findall(r"(?<=linear format)(.*)(?=(Additional|for inners:|approx. value))",self.pdfplumber_pdf.pages[int(page)-1].extract_text(),flags=re.M|re.I|re.S)
                design_instruction = re.findall(r"(?=Additional Instructions)(.*)",self.pdfplumber_pdf.pages[int(page)-1].extract_text(),flags=re.M|re.I|re.S)

                if nutrition_linear_format:
                    page_dict.setdefault("NUTRITIONAL_CLAIM",[]).append({classify(str(nutrition_linear_format[0][0]).strip())[0]:str(nutrition_linear_format[0][0]).strip()})
                if design_instruction:
                    page_dict.setdefault("design instruction",[]).append({classify(str(design_instruction[0]).strip())[0]:str(design_instruction[0]).strip()})

                for table in self.get_tables(self.input_pdf,int(page)):
                    for content, type in self.table_category(table):
                        print(colored(type,'magenta'))
                        if type == 'table':
                            # df = pd.DataFrame(content[0])
                            df = pd.DataFrame(content)
                            if df.empty:
                                continue
                            table_heading = str(df[0][0]).split('/')
                            print('table_heading------>', table_heading)
                            table_heading = [split_heading for split_heading in table_heading if split_heading.strip()]
                            print('table_heading-------->', table_heading)
                            type = 'Normal' if len(table_heading) == 1 else 'Arabic'
                            if table_heading and "NEST TABLE" not in table_heading[0]:
                                # if "nutrition information" in "".join(df[0].apply(func=str)).lower() and "energy" in "".join(df[0].apply(func=str)).lower():   # new mondelez account nutrition table processing
                                #     print("puthu maapla")
                                #     nutrition_dict = self.nutrition_table_processing(nutrition_df=df, table_type=type)
                                #     print("nutrition_dict------->",nutrition_dict)
                                #     continue
                                if self.is_nutrition_table_or_not(table_heading[0].strip().split('\n')[0]):
                                    print('inside nutrition table--------->',type)
                                    # need to pass to nutrition table processing
                                    nutrition_dict = self.nutrition_table_processing(nutrition_df=df,table_type=type)
                                    if isinstance(nutrition_dict,dict):
                                        for key,value in nutrition_dict.items():
                                            if key == "NUTRITION_FACTS":
                                                if key in page_dict:
                                                    page_dict[key].append(value)
                                                else:
                                                    page_dict[key] = [value]
                                            else:
                                                if key in page_dict:
                                                    page_dict[key].extend(value)
                                                else:
                                                    page_dict[key] = value
                                    # print('Nutrition----->',nutrition_dict)
                                else:
                                    normal_dict = self.normal_table_processing(df)
                                    if 'Nutrition' in normal_dict:
                                        if 'NUTRITION_FACTS' in page_dict:
                                            page_dict['NUTRITION_FACTS'].append(normal_dict['Nutrition'])
                                        else:
                                            page_dict['NUTRITION_FACTS'] = [normal_dict['Nutrition']]
                                    normal_dict.pop('Nutrition', None)
                                    for key,value in normal_dict.items():
                                        if key in page_dict:
                                            page_dict[key].extend(value)
                                        else:
                                            page_dict[key] = value
                                    # page_dict = {**page_dict,**normal_dict}
                            else:
                                print('inside fault region')
                                normal_dict = self.normal_table_processing(df)
                                if 'Nutrition' in normal_dict:
                                    if 'NUTRITION_FACTS' in page_dict:
                                        page_dict['NUTRITION_FACTS'].append(normal_dict['Nutrition'])
                                    else:
                                        page_dict['NUTRITION_FACTS'] = [normal_dict['Nutrition']]
                                normal_dict.pop('Nutrition', None)
                                page_dict = {**page_dict, **normal_dict}
                        elif type == 'content':
                            if isinstance(content,str) and "NEST TABLE" not in content:
                                # classifier_output = base('general', model_location).prediction(get_display(content))
                                classifier_output = self.mondelez_classifier(get_display(content),method='General')
                                # lang = classify(content)[0]
                                try:
                                    lang = lang_detect(content)
                                except:
                                    lang = classify(content)[0]
                                print('detected sentence---->', content)
                                print(classifier_output['output'],'------>', classifier_output['probability'])
                                if classifier_output['output'] in ['INGREDIENTS_DECLARATION','ALLERGEN_STATEMENT'] and classifier_output['probability'] > 0.70:  # can reduce the probability score
                                    bold_content = self.get_bold_contents(str(content))
                                    if bold_content:
                                        content = bold_content
                                    content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                    if 'INGREDIENTS_DECLARATION' in page_dict:
                                        page_dict['INGREDIENTS_DECLARATION'].append({lang:content})
                                    else:
                                        page_dict['INGREDIENTS_DECLARATION'] = [{lang:content}]
                                elif classifier_output['output'] in ['NUTRITION_FACTS'] and classifier_output['probability'] > 0.70:
                                    nutrition_content = content.lower()
                                    if 'nutrition facts' in nutrition_content and ':' in nutrition_content:
                                        nutrition_content_dict = {}
                                        _content = nutrition_content.split(':')
                                        # print(_content)
                                        _content = _content[-1]
                                        # print(_content)
                                        _content_list = _content.split(',')
                                        # print(_content)
                                        for row_element in _content_list:
                                            row_element = re.sub(r"[^0-9A-Za-z\%\s\.]", "", row_element)
                                            row_element = re.sub(r"\s{1,4}", " ", row_element)
                                            extracted_list_tuple = re.findall(r"(\D*)\s?(\<?s?\d{1,2}?\.?\d{1,2}\s?(g|kj|kcal|mg|mcg))\s?(\<?s?\d?\.?\d{1,2}\s?%)",row_element)      # eg : [('Saturated Fat ', '16 g', 'g', '8 %')]
                                            if extracted_list_tuple:
                                                extracted_list = list(extracted_list_tuple[0])
                                                if len(extracted_list) == 4:
                                                    del extracted_list[2]
                                                    header = str(extracted_list[0]).strip().capitalize()
                                                    for value in extracted_list[1:]:
                                                        value_header = 'PDV' if "%" in value else "Value"
                                                        if value:
                                                            if header in nutrition_content_dict:
                                                                nutrition_content_dict[header].append({value_header: {'en': value}})
                                                            else:
                                                                nutrition_content_dict[header] = [{value_header: {'en': value}}]
                                        if 'NUTRITION_FACTS' in page_dict:
                                            page_dict['NUTRITION_FACTS'].append(nutrition_content_dict)
                                        else:
                                            page_dict['NUTRITION_FACTS'] = [nutrition_content_dict]
                                    else:
                                        content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                        if 'NUTRITIONAL_CLAIM' in page_dict:
                                            page_dict['NUTRITIONAL_CLAIM'].append({lang: content})
                                        else:
                                            page_dict['NUTRITIONAL_CLAIM'] = [{lang: content}]
                                elif 'nutrition' in content.lower() and 'template' in content.lower():
                                    content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                    if 'Nutrition Declaration' in page_dict:
                                        page_dict['Nutrition Declaration'].append({lang: content})
                                    else:
                                        page_dict['Nutrition Declaration'] = [{lang: content}]
                                else:
                                    # print('non detected sentence---->',content)
                                    content = str(content).replace('<', '&lt;').replace('>', '&gt;')
                                    if 'OTHER_INSTRUCTIONS' in page_dict:
                                        page_dict['OTHER_INSTRUCTIONS'].append({lang: content})
                                    else:
                                        page_dict['OTHER_INSTRUCTIONS'] = [{lang: content}]
                            elif "NEST TABLE" in content:
                                nutrition_dict = self.nutrition_table_processing(page_no=page, table_type='Normal')
                                if nutrition_dict:
                                    for key, value in nutrition_dict.items():
                                        if key == "NUTRITION_FACTS":
                                            if key in page_dict:
                                                page_dict[key].append(value)
                                            else:
                                                page_dict[key] = [value]
                                        else:
                                            if key in page_dict:
                                                page_dict[key].extend(value)
                                            else:
                                                page_dict[key] = value
                final_dict[page] = page_dict
        return final_dict