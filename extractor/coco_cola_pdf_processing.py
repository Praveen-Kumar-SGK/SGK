import camelot
import pandas as pd
import joblib
from langid import classify
from .cocacola_pdf_austria import coca_cola_austria_main
import pdfplumber
import tempfile
from environment import MODE
import re

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

from .excel_processing import laser
from .utils import GetInput

class coco_cola:
    def __init__(self,input_pdf=None,pages=None):
        self._input_pdf = None
        self._pages = None
        self.model = joblib.load(coca_cola_model)
        self.laser = laser
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self._input_pdf_location = f'{self.temp_directory.name}/input_pdf.pdf'
        if input_pdf and pages:
            self.input_pdf = input_pdf   # setter method
            self.pages = pages  # setter method

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
        get_input = GetInput(input_pdf_value, self._input_pdf_location)
        self._input_pdf = get_input()

    def main(self,input_pdf,pages):
        self.input_pdf = input_pdf
        self.pages = pages
        self.pdfplumber_pdf = pdfplumber.open(self.input_pdf)
        # diverting plr pdf to plr code
        extracted_text = self.pdfplumber_pdf.pages[0].extract_text()
        if re.findall(r"austria", extracted_text, flags=re.I|re.M|re.S):
            print("redirecting to cocacola austria")
            return coca_cola_austria_main(self.input_pdf,pages)
        final_dict = {}
        for page in self._pages.split(","):
            page_dict = {}
            pdf = camelot.read_pdf(self._input_pdf, lattice=True, line_scale=60, pages=page)
            for table_number in range(len(pdf)):
                df = pdf[table_number].df
                df = df.iloc[:,-2:]
                df.columns = range(df.shape[1])
                table_dict = self.df_to_json_old(df)
                page_dict = {**page_dict,**table_dict}
            final_dict[page] = page_dict
        return final_dict

    def df_to_json_old(self,input:pd.DataFrame):
        table_dict = {}
        df = input
        # Iteration through the dataframe
        rows , columns = df.shape
        for column in range(columns)[:1]:
            for row in range(rows):
                nutrition = df[column][row]
                class_predicted = self.predict(nutrition)
                for _col in range(columns)[1:]:
                    content = df[_col][row]
                    if isinstance(content,str) and str(content).strip():
                        lang = classify(content)[0]
                        if class_predicted in table_dict:
                            table_dict[class_predicted].append({lang: content})
                        else:
                            table_dict[class_predicted] = [{lang: content}]
        return table_dict

    def predict(self,input,threshold=0.90,ignore_element:tuple=("None")):
        if not isinstance(input,str):
            return
        predicted_class = self.model.predict(self.laser.embed_sentences(input,lang="en"))[0]
        predicted_class_probability = self.model.predict_proba(self.laser.embed_sentences(input,lang="en"))
        predicted_class_probability[0].sort()
        max_predicted_class_probability = max(predicted_class_probability[0])
        print("class_predicted---->", input, "--------->", predicted_class,'------->',max_predicted_class_probability)
        if max_predicted_class_probability > threshold and predicted_class not in ignore_element:
            return predicted_class
        else:
            return "UNMAPPED"