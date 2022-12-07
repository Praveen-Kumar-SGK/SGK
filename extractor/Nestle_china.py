import pdfplumber
import fitz
import pandas as pd
import re
import joblib
import requests
from langid import classify
import tempfile

# input_pdf = r"/Users/vijaykanagaraj/PycharmProjects/testing/ILNI for CCS SHARKWICH nibbling- milk 20201203.pdf"
# input_pdf = r"/Users/vijaykanagaraj/PycharmProjects/testing/multi_nestle_china.pdf"
# cleaned_pdf = r"/Users/vijaykanagaraj/PycharmProjects/testing/cleaned.pdf"
#
# model_location = r"/Users/vijaykanagaraj/PycharmProjects/Dataset/nestle_china_model.pkl"
# # master_nutrition_model_location = r"/Users/vijaykanagaraj/PycharmProjects/Dataset/master_nutrition.pkl"
# master_nutrition_model_location = r"/Users/vijaykanagaraj/PycharmProjects/Dataset/ferrero_header_model.pkl"
# model = joblib.load(model_location)
# nutrition_model = joblib.load(master_nutrition_model_location)

from .excel_processing import laser, document_location , ferrero_header_model, nestle_china_model
from .utils import GetInput

class NestleChina:
    def __init__(self,input_pdf=None,pages=None):
        self._input_pdf = None
        self._pages = None
        self.model = joblib.load(nestle_china_model)
        self.nutrition_model = joblib.load(ferrero_header_model)
        self.laser = laser
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self._input_pdf_location = f'{self.temp_directory.name}/input_pdf.pdf'
        if input_pdf and pages:
            self.input_pdf = input_pdf   # setter method
            self.pages = pages  # setter method

        self.nutrition_headers = []

    @property
    def pages(self):
        return self._pages

    @pages.setter
    def pages(self,pages_value):
        self._pages = pages_value

    @property
    def input_pdf(self):
        return self._input_pdf

    @input_pdf.setter
    def input_pdf(self,input_pdf_value):
        get_input = GetInput(input_pdf_value, self._input_pdf_location,clean_pdf=True)
        self._input_pdf = get_input()

    def extract_pdf(self,page):
        page_dict = {}
        plumber_object = pdfplumber.open(self._input_pdf)
        i = 0
        if int(page) - 1 in range(len(plumber_object.pages)):
            for table in plumber_object.pages[int(page) - 1].extract_tables():
                df = pd.DataFrame(table)
                print(df)
                print("------" * 10)
                rows, columns = df.shape
                if columns > 1:
                    response = self.df_to_json_general(df)
                    page_dict = {**page_dict, **response}
                else:
                    new_df = self.content_to_nutrition_table(df)
                    response = self.df_to_json_nutrition(new_df)
                    if self.nutrition_headers:
                        print("header_list----->", self.nutrition_headers)
                        for header_list in self.nutrition_headers:
                            for header in header_list:
                                if "NUTRI_TABLE_HEADERS" in page_dict:
                                    page_dict["NUTRI_TABLE_HEADERS"].append({"en":header})
                                else:
                                    page_dict["NUTRI_TABLE_HEADERS"] = [{"en":header}]
                        self.nutrition_headers.clear()
                    if response:
                        if "NUTRITION_FACTS" in page_dict:
                            page_dict["NUTRITION_FACTS"].append(response)
                        else:
                            page_dict["NUTRITION_FACTS"] = [response]
        return page_dict

    def content_to_nutrition_table(self,df):
        is_nutrition_table = False
        rows, columns = df.shape
        table = []
        for row in range(rows):
            row_values = " ".join(list(df.loc[row])).split()
            if "项目" in row_values:
                self.nutrition_headers.append(row_values)
                # print("NUtrition_headers---->",self.nutrition_headers)
                is_nutrition_table = True
            elif is_nutrition_table:
                table_content = " ".join(list(df.loc[row])).split("\n")
                for nutrition_row in table_content:
                    table.append(nutrition_row.split())
        return pd.DataFrame(table)

    def df_to_json_general(self,input: pd.DataFrame):
        table_dict = {}
        df = input
        # Iteration through the dataframe
        rows, columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows):
                header = df[column][row]
                header = re.sub(r"(\(|（)(.*?)(\)|）)", "", str(header).replace("\n", " "), flags=re.M)
                header = header.replace(':', '')
                class_predicted = self.predict(header)
                if class_predicted not in ("NUTRITION_FACTS"):
                    for _col in range(columns)[1:]:
                        content = df[_col][row]
                        if isinstance(content, str) and str(content).strip():
                            lang = classify(content)[0]
                            if class_predicted in table_dict:
                                table_dict[class_predicted].append({lang: content})
                            else:
                                table_dict[class_predicted] = [{lang: content}]
                else:
                    for _col in range(columns)[1:]:
                        content = df[_col][row]
                        if "营养成分表" in content:
                            self.nutrition_headers.append(["营养成分表"])
        return table_dict

    def df_to_json_nutrition(self,input: pd.DataFrame):
        df = input
        nutrition_dict = {}
        rows, columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows):
                header = df[column][row]
                header = re.sub(r"(\(|（)(.*?)(\)|）)", "", str(header).replace("\n", " "), flags=re.M)
                header = header.replace(':', '')
                class_predicted = self.nutrition_model.predict(laser.embed_sentences(header, lang="en"))[0]
                print("nutrition_class_predicted--------->", class_predicted)
                nutrition_dict[class_predicted] = [{"copy_notes":{"en":header}}]
                for _col in range(columns)[1:]:
                    value = df[_col][row]
                    if str(value).strip and isinstance(value, str):
                        nutrition_inner_header = "PDV" if "%" in value else "Value"
                        if class_predicted in nutrition_dict:
                            nutrition_dict[class_predicted].append({nutrition_inner_header: {"en": value}})
                        else:
                            nutrition_dict[class_predicted] = [{nutrition_inner_header: {"en": value}}]
        return nutrition_dict

    def predict(self,input, threshold=0.70, ignore_element: tuple = ("None"),
                unmapped_element_name="OTHER_INSTRUCTIONS"):
        if not isinstance(input, str):
            return
        predicted_class = self.model.predict(laser.embed_sentences(input, lang="en"))[0]
        predicted_class_probability = self.model.predict_proba(laser.embed_sentences(input, lang="en"))
        predicted_class_probability[0].sort()
        max_predicted_class_probability = max(predicted_class_probability[0])
        print("class_predicted---->", input, "--------->", predicted_class, '------->', max_predicted_class_probability)
        if max_predicted_class_probability > threshold and predicted_class not in ignore_element:
            return predicted_class
        else:
            return unmapped_element_name

    def main(self,input_pdf, pages):
        self.input_pdf = input_pdf
        self.pages = pages
        final_dict = {}
        for page in pages.split(","):
            final_dict[page] = self.extract_pdf(page)
        return final_dict




