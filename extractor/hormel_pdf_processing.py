# import re ,joblib
# from langid import classify
import pdfplumber
import cv2,imutils
from pdf2image import convert_from_path
import tempfile , shutil
# import pandas as pd
import camelot
# import matplotlib.pyplot as plt
# import numpy as np
# from laserembeddings import Laser

from .excel_processing import *
from .utils import GetInput

# path_to_bpe_codes = r"/Users/vijaykanagaraj/PycharmProjects/pre_trained_models/Laser/93langs.fcodes"
# path_to_bpe_vocab = r"/Users/vijaykanagaraj/PycharmProjects/pre_trained_models/Laser/93langs.fvocab"
# path_to_encoder = r"/Users/vijaykanagaraj/PycharmProjects/pre_trained_models/Laser/bilstm.93langs.2018-12-26.pt"
#
# laser = Laser(path_to_bpe_codes,path_to_bpe_vocab,path_to_encoder)
#
# document_location = r"/Users/vijaykanagaraj/PycharmProjects/testing/"
# source_pdf = r"TSR 03545 S0049055-17 02-08-2022.pdf"

def daily_intake_extract(df) -> list:
    is_content_available = False
    rows , columns = df.shape
    daily_intake = []
    for column in range(columns)[:1]:
        daily_intake_temp = []
        for row in range(rows):
            cell_content = df[column][row]
            if cell_content and str(cell_content).strip():
                if str(cell_content).strip().startswith("*"):
                    if daily_intake_temp:
                        daily_intake.append("\n".join(daily_intake_temp))
                        daily_intake_temp = []
                    daily_intake_temp.append(str(cell_content))
                    df[column][row] = ""
                    is_content_available = True
                    continue
                if is_content_available and str(cell_content).strip().endswith("."):
                    daily_intake_temp.append(str(cell_content))
                    df[column][row] = ""
                    is_content_available = False
                    continue
                if is_content_available:
                    daily_intake_temp.append(str(cell_content))
                    df[column][row] = ""
        if daily_intake_temp:
            daily_intake.append("\n".join(daily_intake_temp))
    return daily_intake

def ocr_data_loss_preprocessing(text:str):
    replace_dict = {"carb.":"carbohydrates","serv.":"serving","saturated":"saturated fat","trans":"trans fat","includes":"sugar","folate":"folic acid","thiamin":"vitamin b1","riboflavin":"vitamin b2"}
    text = str(text).lower()
    for text_to_replace , with_text in replace_dict.items():
        text = text.replace(text_to_replace,with_text)
    text = re.sub(r"\b(o)(\s{0,2})(g|mg|mcg)\b",lambda pat: "0"+pat.group(2)+pat.group(3),text,flags=re.M|re.I)
    return text

is_df_with_multiple_columns = lambda x: True if len(x[0]) > 1 else False

class Hormel_Processing:
    def __init__(self):
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self.input_pdf_temp = f'{self.temp_directory.name}/input_pdf.pdf'

    def get_input(self,input_pdf):
        return document_location+input_pdf

    def pdf_to_image(self,input_pdf):
        images = convert_from_path(input_pdf)
        for index, image in enumerate(images):
            image.save(f'{self.temp_directory.name}/{index + 1}.png')
        return 'success'

    @staticmethod
    def regex_nutrition_extract(x):
        element_list = []
        value_list = []
        regex_extracted = re.findall(
            r"([\w\,\/\-\s]*?)\s+(\<?\s?\-?\d{0,3}\.?\d{0,2}\s?(%|g added sugars|g\b|kj|kcal|mg|mcg|cal\b))", x,
            flags=re.I)
        if not regex_extracted:
            regex_extracted = re.findall(r"([\w\,\-\s]*?)\s+((\<?\s?\-?\d{0,3}\.?\d{0,2}\s?))", x, flags=re.I)
        for tuple_content in regex_extracted:
            if tuple_content[0] and tuple_content[0].strip() not in ("-"):
                element_list.append(tuple_content[0])
            if tuple_content[1]:
                value_list.append(tuple_content[1])
        return {" ".join(element_list).strip(): value_list}

    def extract_nutrition_data(self, df):
        others_dict = {}
        nutri_dict = {}
        rows = df.index.tolist()
        _, column_count = df.shape
        # nutrition_model = joblib.load(r"/Users/vijaykanagaraj/PycharmProjects/Dataset/master_nutrition.pkl")
        nutrition_model = joblib.load(master_nutrition_model_location)
        get_row_list = lambda df, row: [value for value in df.loc[row].tolist() if not pd.isna(value) and value]

        def nutri_extract_classifier(nutri_key):
            nutri_key = nutri_key.split("/")
            nutrition_class = nutrition_model.predict(laser.embed_sentences(nutri_key, lang="en"))[0].strip()
            nutrition_class_probability = np.max(
                nutrition_model.predict_proba(laser.embed_sentences(nutri_key, lang="en")))
            # print(nutrition_class, "------------>", nutrition_class_probability)
            if nutrition_class_probability > 0.90:
                for value in value_list:
                    if nutrition_class in ("Calories"):
                        value = re.sub("%", "", str(value)).strip()
                    nutri_header = "PDV" if "%" in str(value) else "Value"
                    nutri_dict.setdefault(nutrition_class, []).append({nutri_header: {"en": str(value).strip()}})
                    # print(nutrition_class)
            else:
                nutri_key = ocr_data_loss_preprocessing(row_list[0])
                nutri_key = nutri_key.split("/")
                nutrition_class = nutrition_model.predict(laser.embed_sentences(nutri_key, lang="en"))[0]
                nutrition_class_probability = np.max(
                    nutrition_model.predict_proba(laser.embed_sentences(nutri_key, lang="en")))
                if nutrition_class_probability > 0.90:
                    for value in row_list[1:]:
                        if nutrition_class in ("Calories"):
                            value = re.sub("%", "", str(value)).strip()
                        nutri_header = "PDV" if "%" in str(value) else "Value"
                        nutri_dict.setdefault(nutrition_class, []).append(
                            {nutri_header: {"en": str(value).strip()}})
                else:
                    for value in row_list:
                        if str(value).strip() not in ("nan"):
                            lang = classify(str(value))[0]
                            others_dict.setdefault("OTHER_INSTRUCTIONS", []).append({lang: str(value).strip()})

        for row in rows:
            row_list = get_row_list(df, row)
            print(row_list)
            row_list_string = " ".join(row_list)
            row_list_string = ocr_data_loss_preprocessing(row_list_string)
            # print("row_string+_list----->",row_list_string)
            nutri_key_value_dict = self.regex_nutrition_extract(row_list_string)
            # print(nutri_key_value_dict)

            for nutri_key, value_list in nutri_key_value_dict.items():
                if "calories" in "".join(row_list).lower() or re.search(r"^\d+$", "".join(row_list).lower().strip()):
                    for value in row_list:
                        if re.search(r"\d", str(value)):
                            value = re.sub(r"calories", "", str(value), flags=re.I).strip()
                            nutri_header = "PDV" if "%" in str(value) else "Value"
                            nutri_dict.setdefault("Calories", []).append({nutri_header: {"en": value}})
                    continue

                elif "serving" in "".join(row_list).lower() and "container" in "".join(row_list).lower() and re.search(
                        r"\d", " ".join(row_list).lower().strip()):
                    for value in row_list:
                        if value not in ("nan"):
                            others_dict.setdefault("NUMBER_OF_SERVINGS_PER_PACKAGE", []).append({"en": str(value).strip()})
                    continue

                # elif ("serving" in "".join(row_list).lower() and "per" not in "".join(row_list).lower()) or re.search(r"\d+\s+[a-zA-Z]+\s+(\(\d+\s{0,2}(ml|g|mcg|mg|kg)\))", " ".join(row_list).lower()):
                elif ("serving" in "".join(row_list).lower() and "per" not in "".join(row_list).lower()) or re.search(r"\(\d{0,3}?\.?\d{0,3}?\s{0,2}(ml|g|mcg|mg|kg|lb|oz)\)", " ".join(row_list).lower()):
                    # \d+\s+[a-zA-Z]+\s+(\(\d+\s{0,2}(ml|g|mcg|mg|kg|lb|oz)\s{0,2}\d{0,2}\s{0,2}(ml|g|mcg|mg|kg|lb|oz)?\)) we can use this also for regex serving size match
                    for value in row_list:
                        if re.search(r"\d", str(value)):
                            if value not in ("nan"):
                                others_dict.setdefault("SERVING_SIZE", []).append({"en": str(value).strip()})
                    continue

                elif nutri_key and str(nutri_key).strip() and value_list and "%" not in row_list[0] and "serving" not in \
                        row_list[0] and column_count > 1:
                    nutri_extract_classifier(nutri_key)

                elif nutri_key and str(nutri_key).strip() and value_list and "serving" not in row_list[
                    0] and column_count == 1:
                    nutri_extract_classifier(nutri_key)

                else:
                    for value in row_list:
                        if value not in ("nan"):
                            lang = classify(str(value))[0]
                            others_dict.setdefault("OTHER_INSTRUCTIONS", []).append({lang: str(value).strip()})
        # print({"NUTRITION_FACTS": [nutri_dict], **others_dict})
        if nutri_dict and others_dict:
            return {"NUTRITION_FACTS": [nutri_dict], **others_dict}
        elif not nutri_dict and others_dict:
            return others_dict
        elif nutri_dict and not others_dict:
            return {"NUTRITION_FACTS": [nutri_dict]}


    @staticmethod
    def get_general_elements_from_plumb_data(input_pdf):
        keyword_match = {"lcm": "ADDITIONAL_PRODUCT_VARIANT_INFORMATION", "item number": "INTERNAL_PACKAGE_IDENTIFIER",
                         "formula": "ADDITIONAL_PRODUCT_VARIANT_INFORMATION", "true product name": "FUNCTIONAL_NAME",
                         "bioengineered": "QUALITY_STATEMENTS",
                         "hormel product name": "BRAND_NAME"}
        plumb_pdf = pdfplumber.open(input_pdf)
        page_text = plumb_pdf.pages[0].extract_text()  # extract only first page
        general_dict = {}
        if page_text:
            page_text_list = page_text.split("\n")
            for index, content in enumerate(page_text_list):
                for text_to_match, gs1 in keyword_match.items():
                    if text_to_match.lower() in content.lower():
                        if text_to_match == "true product name" and index < len(page_text_list):
                            content_selected = page_text_list[index + 1]
                        elif text_to_match == "bioengineered":
                            content_selected = content
                        elif "#" in content:
                            content_selected = content.split("#")[-1].strip()
                        else:
                            content_selected = content.split("-")[-1].strip()
                        general_dict.setdefault(gs1, []).append({"en": content_selected})
        return general_dict

    @staticmethod
    def content_data_extraction(content):
        content_data_dict = {}
        if not content and pd.isna(content):
            return content_data_dict
        content = str(content)
        if "other information required on the label" in content.lower():
            for value in content.split("\n"):
                content_data_dict.setdefault("OTHER_INSTRUCTIONS",[]).append({"en":value.strip()})
        elif "ingredient" in content.lower():
            content_data_dict.setdefault("INGREDIENTS_DECLARATION", []).append({"en": content.strip()})
        # elif re.match(r"\d+\s+[a-zA-Z]+\s+(\(\d+\s{0,2}(ml|g|mcg|mg|kg|lb|oz)\s{0,2}\d{0,2}\s{0,2}(ml|g|mcg|mg|kg|lb|oz)?\))",content):
        # elif re.search(r"/\d+\.?\d{0,3}?\s+[a-zA-Z]+\s+(\(\d+\s{0,2}(ml|g|mcg|mg|kg|lb|oz)\s{0,2}\d{0,2}\s{0,2}(ml|g|mcg|mg|kg|lb|oz)?\))|[a-zA-Z\s]+\s+\d+\.?\d{0,2}?\s+(ml|g|mcg|mg|kg|lb|oz)\s?\(\d+\.?\d{0,3}\s{0,2}(ml|g|mcg|mg|kg|lb|oz)?\)",content,flags=re.I|re.M):
        elif re.search(r"\(\d{0,3}?\.?\d{0,3}?\s{0,2}(ml|g|mcg|mg|kg|lb|oz)\)",content,flags=re.I|re.M):
            content_data_dict.setdefault("SERVING_SIZE", []).append({"en":content})
        return content_data_dict

    @staticmethod
    def table_data_extraction(table_list):
        table_data_dict = {}
        if not table_list:
            return table_data_dict

        mapping_dict = {"Net Content":"NET_CONTENT_STATEMENT","Product Name Qualifier":"OTHER_INSTRUCTIONS"}
        nan_replace = lambda x: str(x).strip() if not pd.isna(x) and x and str(x).strip() else ""
        df = pd.DataFrame(table_list).T
        df = df.applymap(nan_replace)
        rows , columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows):
                key = df[column][row]
                if not pd.isna(key):
                    for mapping_key , gs1 in mapping_dict.items():
                        if mapping_key.lower() in key.lower():
                            for _col in range(columns)[1:]:
                                value = df[_col][row]
                                if value and str(value).strip() and not pd.isna(value):
                                    table_data_dict.setdefault(gs1, []).append({"en": value})
        return table_data_dict

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
                # yield (width / (x - 10), height / (y - 10), width / (x + w + 20), height / (y + h + 30))
                yield (width / (x), height / (y), width / (x + w), height / (y + h))

    def content_inside_bounding_box(self,input_pdf,page_no, coordinates_percent):
        nan_replace = lambda x: x.strip() if x and str(x).strip() else np.nan
        # remove_empty_element = lambda list_to_be_cleaned: [str(value).strip() for value in list_to_be_cleaned if value and str(value).strip()]
        pdf = self.pdfplumber_pdf
        page = pdf.pages[page_no - 1]
        self.pages = len(pdf.pages)                                 #getting total pages
        height, width = float(page.height), float(page.width)
        print("height---->",height,"   ","width--->",width)
        w0, h0, w1, h1 = coordinates_percent
        coordinates = (width / w0, height / h0, width / w1, height / h1)
        print("original_camelot_coordinates------>",coordinates)
        coordinates_int = [int(value) for value in coordinates]
        # coordinates_int = [int(width)-coordinates_int[0],int(height)-coordinates_int[1],int(width)-coordinates_int[2],int(height)-coordinates_int[3]] # mostly working scenario
        coordinates_int = [coordinates_int[0],int(height)-coordinates_int[1],coordinates_int[2],int(height)-coordinates_int[3]]
        print("camelot_coordinates------?",f'{coordinates_int[0]},{int(coordinates_int[1])},{coordinates_int[2]},{coordinates_int[3]}')
        ROI = page.within_bbox(coordinates, relative=False)
        try:
            # camelot_table = camelot.read_pdf(self.input_pdf,flavor="stream",row_tol=10,table_areas=[f'{coordinates_int[2]},{int(coordinates_int[1])},{coordinates_int[0]},{coordinates_int[3]}'],pages=str(page_no)) # mostly working
            camelot_table = camelot.read_pdf(self.input_pdf,flavor="stream",row_tol=10,table_areas=[f'{coordinates_int[0]},{int(coordinates_int[1])},{coordinates_int[2]},{coordinates_int[3]}'],pages=str(page_no))
        except:
            camelot_table = []
        if camelot_table:
            for table in camelot_table:
                df = table.df
                print(df)
                df = df.applymap(nan_replace)
                df.dropna(how='all', axis=1, inplace=True)
                table_list = df.values.tolist()
                # table_list = [remove_empty_element(nested_list) for nested_list in table_list]
                if is_df_with_multiple_columns(table_list):
                    yield ([table_list], 'table')
                else:
                    text_extracted = ROI.extract_text()
                    if text_extracted:
                        yield (text_extracted, "content")
        else:
            text_extracted = ROI.extract_text()
            if text_extracted:
                yield (text_extracted,"content")

    def main(self, input_pdf, pages):
        # lambda functions
        nan_replace = lambda x: str(x).strip() if x and str(x).strip() else np.nan
        correct_data_orientation = lambda x:" ".join(str(x).split("\n")[::-1]) if re.search(r"^\d{0,3}\.?\d{0,2}\s?(%|g\b|kj|kcal|mg|mcg|cal\b)\s", str(x)) else str(x)  # 5% iron ----> Iron 5%

        # self.input_pdf = self.get_input(input_pdf)
        get_input = GetInput(input_pdf, self.input_pdf_temp,clean_pdf=False)
        self.input_pdf = get_input()
        self.pdfplumber_pdf = pdfplumber.open(self.input_pdf)

        final_dict = {}
        pdf_to_image_status = self.pdf_to_image(self.input_pdf)
        assert pdf_to_image_status == 'success', 'pdf to image conversion failed'
        for page in pages.split(','):
            print(f'{page}')
            if int(page) - 1 in range(len(self.pdfplumber_pdf.pages)):

                is_nutrition_table_available = False
                # check for nutrition facts in this page
                content = self.pdfplumber_pdf.pages[int(page)-1].extract_text()
                if "nutrition facts" in content.lower():
                    is_nutrition_table_available = True

                page_dict = {}
                if page == "1":
                    page_dict = self.get_general_elements_from_plumb_data(self.input_pdf)
                input_image = f'{self.temp_directory.name}/{page}.png'
                for bounding_box in self.find_contours(input_image):
                    for content, type in self.content_inside_bounding_box(self.input_pdf, int(page), bounding_box):
                        print(type,"---------->",content)
                        if type == "content":
                            content_dict = self.content_data_extraction(content)
                            for key, value_list in content_dict.items():
                                page_dict.setdefault(key, []).extend(value_list)
                            print(content_dict)
                        else:
                            if "nutrition facts" in str(content[0][0][0]).lower():
                                df = pd.DataFrame(content[0])
                                daily_intake_statements = daily_intake_extract(df)
                                print("daily intake statement---->", daily_intake_statements)
                                for daily_intake_statement in daily_intake_statements:
                                    lang = classify(daily_intake_statement)[0]
                                    page_dict.setdefault("nutrition_table_contents", []).append({lang: daily_intake_statement})
                                # print(df[0].apply(correct_data_orientation))
                                df[0] = df[0].apply(correct_data_orientation)
                                df = df.applymap(nan_replace)
                                df.dropna(inplace=True, axis=0, how="all")
                                nutrition_table_dict = self.extract_nutrition_data(df)
                                for key, value_list in nutrition_table_dict.items():
                                    if value_list:
                                        page_dict.setdefault(key, []).extend(value_list)
                            table_dict = self.table_data_extraction(content[0])
                            for key, value_list in table_dict.items():
                                if value_list:
                                    page_dict.setdefault(key, []).extend(value_list)
                            print(table_dict)
                        print('------------------------')
                        # print("bounding_box---->", bounding_box)
                        # print(f'content inside bb----> {content}')
                        # print(f'content inside bb type----> {type}')
                        # print('------------------------')
                        # page_dict.setdefault(type,[]).append(content)   ### extracted raw content
                if "NUTRITION_FACTS" not in page_dict and is_nutrition_table_available:
                    camelot_tables = camelot.read_pdf(self.input_pdf, flavor="stream", row_tol=10,edge_tol=1000,pages=str(page))
                    for table in camelot_tables:
                        df = table.df
                        df = df.applymap(nan_replace)
                        df.dropna(how='all', axis=1, inplace=True)
                        table_list = df.values.tolist()
                        # table_list = [remove_empty_element(nested_list) for nested_list in table_list]
                        if is_df_with_multiple_columns(table_list) and ("nutrition facts" in str(df[0][0]).lower() or any([True for key in df.loc[:,0].to_list() if "fat" in str(key).lower() or "calories" in str(key).lower()])):
                            daily_intake_statements = daily_intake_extract(df)
                            print("daily intake statement---->", daily_intake_statements)
                            for daily_intake_statement in daily_intake_statements:
                                lang = classify(daily_intake_statement)[0]
                                page_dict.setdefault("daily_intake_statement", []).append({lang: daily_intake_statement})
                            # print(df[0].apply(correct_data_orientation))
                            df[0] = df[0].apply(correct_data_orientation)
                            df = df.applymap(nan_replace)
                            df.dropna(inplace=True, axis=0, how="all")
                            nutrition_table_dict = self.extract_nutrition_data(df)
                            # nutrition_facts = nutrition_table_dict.get("NUTRITION_FACTS", None)
                            # if nutrition_facts:
                            #     page_dict["NUTRITION_FACTS"] = nutrition_facts
                            #     page_dict.pop("NUTRITION_FACTS",None)
                            for key, value_list in nutrition_table_dict.items():
                                if value_list:
                                    page_dict.setdefault(key, []).extend(value_list)
                        table_dict = self.table_data_extraction(table_list)
                        for key, value_list in table_dict.items():
                            if value_list:
                                page_dict.setdefault(key, []).extend(value_list)
                final_dict[int(page)] = page_dict
        try:
            self.temp_directory.cleanup()
        except:
            shutil.rmtree(self.temp_directory.name)
        finally:
            print("temp_folder_cleaned")
        return final_dict

# x = Hormel_Processing().main(source_pdf,"1,2,3,4,5,6,7")