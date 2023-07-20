##################################################         SC Johnson -China   ##################################################
import io
import re
import copy
import joblib
import tempfile
import PyPDF2
import pdfplumber
from fuzzywuzzy import fuzz, process
from bs4 import BeautifulSoup
from langid import classify
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import warnings
from .dev_constants import *
warnings.filterwarnings("ignore")
# ---------------------------------------------------------------------------------------------------------------------
# Loading model
from laserembeddings import Laser
import tempfile

from .excel_processing import *

# ----------------------------------------------------------------------------------------------------------------------------------
model_file = sc_johnson_china
# ----------------------------------------------------------------------------------------------------------------------------------
class HTMLconverter:  # HyperMarkup
    def __init__(self, html, threshold=95, tags=["p"]):
        self.html = html
        self.modified_html = copy.deepcopy(html)
        self.soup = BeautifulSoup(self.modified_html, "html.parser")
        self.tags_to_group = []
        self.tags_text_to_group = []
        self.threshold = threshold
        self.tags = tags
        self.score, self.partial_score = 0, 0

    def clean_text(self, text):
        ''' clean text to compare fuzzywuzzy'''
        # < b > to empty
        # ((br/)) to new line \n
        text = re.sub(r"\s{1,}", " ", str(text)).strip().lower()  # remove unwanted spaces or multiple spaces
        return text

    def extract(self, input_text):
        for tag in self.soup.find_all(self.tags):
            if not tag.text.strip():
                continue
            if self.tags_text_to_group:
                # print("tags present")
                temp_text = " ".join(self.tags_text_to_group + [tag.text])
            else:
                # print("tags not present")
                temp_text = tag.text

            score = fuzz.ratio(self.clean_text(temp_text), self.clean_text(input_text))
            partial_score = fuzz.partial_ratio(self.clean_text(temp_text), self.clean_text(input_text))
            # print("temp_text-------->",repr(temp_text))
            # print("temp_text-------->",repr(input_text))
            # print("score----->",score)
            # print("partial score----->",partial_score)
            # print("------"*10)

            if self.tags_text_to_group:
                if score <= self.score and partial_score < self.partial_score:
                    self.tags_to_group = []
                    self.tags_text_to_group = []
                    score = fuzz.ratio(self.clean_text(tag.text), self.clean_text(input_text))
                    partial_score = fuzz.partial_ratio(self.clean_text(tag.text), self.clean_text(input_text))

            if score > self.threshold and partial_score > self.threshold:
                self.tags_text_to_group.append(tag.text)
                self.tags_to_group.append(tag)
                # print(tag.name, "----->", tag.text)
                break
            elif score < self.threshold and partial_score > self.threshold:
                self.tags_text_to_group.append(tag.text)
                self.tags_to_group.append(tag)
                self.score = score
                self.partial_score = partial_score

        return self.tags_to_group


# Function for pdf file format
def bold_function1(input_pdf, page):
    output_io = io.StringIO()
    with open(input_pdf, 'rb') as input:
        extract_text_to_fp(input, output_io, page_numbers=[int(page) - 1],
                           laparams=LAParams(line_margin=1, line_overlap=0.9, all_texts=False),
                           output_type='html', codec=None)
    bold_text_finder = HTMLconverter(html=output_io.getvalue(), tags=['div'], threshold=90)
    return bold_text_finder


def bold_funtion2(soup_list):
    bold_list = []

    soup_list = ''.join([str(soup1) for soup1 in soup_list])
    soup_text = soup_list.replace('<br/>', '\n')
    for check_span in BeautifulSoup(soup_text, 'html.parser').find_all('span'):
        if 'bold' in check_span.get('style', 'none').lower():
            add_bold_tag = "<b>" + check_span.text + "</b>"
            bold_list.append(add_bold_tag)
        else:
            add_bold_tag = check_span.text
            bold_list.append(add_bold_tag)
    bold_string = ''.join(bold_list)
    return bold_string.strip()


def bold_funtion3(path, page, fvalues, fkeys):
    bvalues = []
    bold_text_finder = bold_function1(path, page)
    for index, v in enumerate(fvalues):
        tv = []
        for val in v:
            if fkeys[index] != 'Unmapped':
                soup_list = bold_text_finder.extract(v)
                if soup_list:
                    bold_string = bold_funtion2(soup_list)
                    tv.append({classify(bold_string)[0]: bold_string.strip()})
                else:
                    tv.append({classify(str(val))[0]: str(val).strip()})
            else:
                tv.append({classify(str(val))[0]: str(val).strip()})
        bvalues.append(tv)
    return bvalues


# ----------------------------------------------------------------------------------------------------------------------------------
def get_input(input_file, input_pdf_location):
    if input_file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location + input_file
# ----------------------------------------------------------------------------------------------------------------------------------
def table_chunk(path, page):
    plumb = pdfplumber.open(path)
    lines = plumb.pages[page - 1].extract_tables()[0]

    indices = []
    for index, row in enumerate(lines):
        if row[0].strip().startswith('Text_'):
            indices.append(index)

    paras = []
    if len(indices) == 1:
        if indices[0] == 0:
            paras.append(lines)
        else:
            paras.append(lines[:indices[0]])
            paras.append(lines[indices[0]:])
    elif indices:
        for index, i in enumerate(indices):
            if index == 0 and i == 0:
                paras.append(lines[0:indices[1]])
            elif index == 0 and i != 0:
                paras.append(lines[0:i])
                paras.append(lines[i:indices[1]])
            elif len(indices) - 1 == index:
                paras.append(lines[i:])
            else:
                paras.append(lines[i:indices[index + 1]])
    else:
        paras.append(lines)
    return paras


# ----------------------------------------------------------------------------------------------------------------------------------
def data(chunks, temp_key):
    keys = []
    values = []
    pattern = r'\d{1,2}/\d{1,2}/\d{2}\s\d{1,2}:\d{2}\s(?:AM|PM)'
    matches = ['Master', 'English', 'Chinese', 'Spanish', 'Japanese']
    for index, chunk in enumerate(chunks):
        element_temp = ''
        # print('\n',index+1)
        for line in chunk:
            line = [j for j in line if j and re.sub(pattern, '', str(j)).strip()]
            if 'Element Type' in line[0]:
                if len(chunks) - 1 == index:
                    element_temp = line[0].replace('Element Type', '').strip()
                    temp_key = element_temp
                else:
                    element_temp = line[0].replace('Element Type', '').strip()

            elif any(1 for match in matches if match in str(line[0])) and len(line) >= 2 and 'language' not in str(
                    line[0]).lower():
                if element_temp:
                    keys.append(element_temp)
                    values.append(line[1:])
                elif temp_key:
                    keys.append(temp_key)
                    values.append(line[1:])
                else:
                    keys.append('Unmapped')
                    values.append(line[1:])
            else:
                keys.append('Unmapped')
                values.append(line)

    return keys, values, temp_key


# ----------------------------------------------------------------------------------------------------------------------------------
def first_page(path, page):
    plumb = pdfplumber.open(path)
    lines = plumb.pages[page - 1].extract_text().split('\n')
    if 'Web' in lines[0]:
        keys = []
        values = []
        for line in lines:
            keys.append('Unmapped')
            values.append([str(line).strip()])
        return keys, values

    else:
        return [], [[]]
# ----------------------------------------------------------------------------------------------------------------------------------
def missing_data(chunks):
    missing_dict = {}
    for attri in chunks:
        if "attributes" in attri[0][0].lower():
            for level1 in attri:
                if "mm_" in level1[0].lower():
                    for x1 in range(1, len(level1)):
                        value_attr = level1[x1]
                        if "SERIAL_NUMBER" in missing_dict:
                            missing_dict["SERIAL_NUMBER"].append({classify(value_attr)[0]: value_attr.strip()})
                        else:
                            missing_dict["SERIAL_NUMBER"] = [{classify(value_attr)[0]: value_attr.strip()}]
    return missing_dict


# ----------------------------------------------------------------------------------------------------------------------------------
def load_model(model_file):
    classifier_model = joblib.load(model_file)
    return classifier_model


def model_trained(classifier_model, key):
    if key != "Unmapped":
        x_key = classifier_model.predict_proba(laser.embed_sentences(key, lang="en"))[0]
        x_key.sort()
        classified = classifier_model.predict(laser.embed_sentences(key, lang="en"))[0]
        if x_key[-1] > 0.60:
            classified_key = classified
        else:
            classified_key = "Unmapped"
        return str(classified_key)
    else:
        return "Unmapped"


# ----------------------------------------------------------------------------------------------------------------------------------
# Function to create dict with same key with multiple values in list
def multi_key_value(keys, values):
    file = {}
    for i in range(len(keys)):
        file.setdefault(keys[i], []).extend(values[i])
    return file
# ----------------------------------------------------------------------------------------------------------------------------------

def val_lang(fvalues):
    bvalues = []
    for v in fvalues:
        tv = []
        for val in v:
            tv.append({classify(str(val))[0]: str(val).strip()})
        bvalues.append(tv)

    return bvalues
# ----------------------------------------------------------------------------------------------------------------------------------

def sc_johnson_cn_main(path,pages):
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    path = get_input(path,input_pdf_location)
    page_number = [int(x) for x in pages.split(",")]
    global temp_key
    temp_key = ''
    out = {}
    for page in page_number:
        with pdfplumber.open(path) as pdf:
            if (page - 1) in range(len(pdf.pages)):
                chunks = table_chunk(path, page)
                # ---------------------------
                missing_mm = missing_data(chunks)
                # ---------------------------
                keys1, values1 = first_page(path, page)
                keys2, values2, temp_key = data(chunks, temp_key)
                if keys1:
                    fkeys = keys1 + keys2
                    fvalues = values1 + values2
                else:
                    fkeys = keys2
                    fvalues = values2
                # ---------------------------
                CN_model = load_model(model_file)
                gs1_keys = [model_trained(CN_model, key) for key in fkeys]
                # bvalues = bold_funtion3(path, page, fvalues, gs1_keys)
                bvalues= val_lang(fvalues)
                final_dict = multi_key_value(gs1_keys, bvalues)
                overall_dict = {**missing_mm, **final_dict}
                out[page]= overall_dict
            else:
                out[page]={}
    return out


# ----------------------------------------------------------------------------------------------------------------------------------