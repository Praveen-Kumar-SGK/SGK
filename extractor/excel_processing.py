import re
from collections import namedtuple , defaultdict
import pandas as pd
import numpy as np
# from sentence_transformers import SentenceTransformer , models
from sklearn.neural_network import MLPClassifier
from laserembeddings import Laser
from langid import classify
import joblib
import os
import string
import time
import smbclient
from environment import MODE
from whatlangid import WhatLangId
from sentence_transformers import SentenceTransformer

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

from .models import *

# Initialize Laser
laser = Laser(path_to_bpe_codes,path_to_bpe_vocab,path_to_encoder)

# Initialize Labse embedding
labse_model = SentenceTransformer(labse_location)

# Initialize language detector
language_model = WhatLangId(custom_model=whatlangid_model)
lang_detect = language_model.predict_lang
# lang_detect = classify

class base:
    def __init__(self,mode = None , model= None):
        self.mode = mode
        self.model = model

    def regex_parsers_generator(self,list):
        self.regex = regex_patterns
        for value in list:
            for key, pattern in regex_patterns.items():
                finding = re.findall(pattern, value, (re.IGNORECASE | re.MULTILINE))
                if finding:
                    yield key, finding[0]

    def model_training(self,method=None):
        print('model_training----->',self.mode)
        _category = None
        _text = None
        if self.mode == 'msd':
            query_result = msd_dataset.objects.values('category','text')
            _category = [result['category'] for result in query_result]
            _text = [result['text'] for result in query_result]
        elif self.mode == 'msd_content':
            query_result = msd_content.objects.values('category','text')
            _category = [result['category'] for result in query_result]
            _text = [result['text'] for result in query_result]
        elif self.mode == 'ferrero_header':
            query_result = ferrero_header.objects.values('category','text')
            _category = [result['category'] for result in query_result]
            _text = [result['text'] for result in query_result]
        elif self.mode == 'general':
            query_result = general_dataset.objects.values('category','text')
            _category = [result['category'] for result in query_result]
            _text = [result['text'] for result in query_result]
        else:
            pass
        if method == 'labse':
            print('labse training')
            df = pd.DataFrame.from_dict({'category':_category,'text':_text})
            # df = pd.read_excel(self.dataset)
            X_train_laser = labse_model.encode(df['text'])
        else:
            print('laser training')
            # df = pd.read_excel(self.dataset)
            df = pd.DataFrame.from_dict({'category': _category, 'text': _text})
            df = df.sample(frac=1)
            X_train_laser = laser.embed_sentences(df['text'],lang='en')
        # mlp = MLPClassifier(hidden_layer_sizes=(70,), solver='adam', activation='tanh', max_iter=500, random_state=0, shuffle=True)
        # mlp = MLPClassifier(hidden_layer_sizes=(80,),solver='adam',activation='tanh',max_iter=440,random_state=0,shuffle=True)
        mlp = MLPClassifier(hidden_layer_sizes=(80,),solver='adam',activation='tanh',max_iter=750,random_state=0,shuffle=True)
        mlp.fit(X_train_laser, df['category'])
        joblib.dump(mlp,self.model)
        return mlp

    def prediction(self,text,method=None):
        if os.path.exists(self.model):
            classifier = joblib.load(self.model)
        else:
            # classifier = self.model_training(method='labse')
            classifier = self.model_training()

        if method == 'labse':
            prediction = classifier.predict(labse_model.encode([text]))
            probability = classifier.predict_proba(labse_model.encode([text]))
        else:
            # lang_detected = detect(text)
            # lang_detected = lang_detect(text)[0]
            lang_detected = classify(text)[0]
            prediction = classifier.predict(laser.embed_sentences([text], lang=lang_detected))
            probability = classifier.predict_proba(laser.embed_sentences([text], lang=lang_detected))
        probability[0].sort()
        # print(probability)
        max_probability = max(probability[0])
        if (max_probability > 0.65) or ((max_probability/2) > probability[0][-2]):
        # if (max_probability > 0.65) or ((max_probability-max_probability/2) > probability[0][-2]):
        # if (max_probability > 0.80):
            pred_output = prediction[0]
        else:
            pred_output = 'None'
            # print(text)
            # print('{}-------------->{}'.format(max(probability[0]), pred_output))
        print(text)
        print('{}-------------->{}'.format(max(probability[0]), pred_output))
        return ({'probability': max(probability[0]), 'output': pred_output, 'actual_output': prediction[0]})

class Excel_extraction(base):
    def __init__(self,file_location,data_frame=pd.DataFrame()):
        super().__init__()
        self.file_location = file_location
        self.data_frame = data_frame
        self.regex_captures = defaultdict(list)
        self.all_unit = ['mg','µg','kJ','g','kcal','mcg']

    def extract_cells(self,method=None):       # extract cells on iterating sheets
        if self.file_location.startswith('\\'):
            try:
                with smbclient.open_file(r"{}".format(self.file_location), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    excel = pd.ExcelFile(f)
                    print('file found')
            except:
                smbclient.reset_connection_cache()
                with smbclient.open_file(r"{}".format(self.file_location), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    excel = pd.ExcelFile(f)
                    print('file found')
            finally:
                smbclient.reset_connection_cache()
        else:
            file = document_location + self.file_location
            print(file)
            excel = pd.ExcelFile(file)
        # excel = pd.ExcelFile(self.file_location)
        for sheet in excel.sheet_names:
            self.data_frame = pd.read_excel(file,header=None,sheet_name=sheet)
            rows , columns = self.data_frame.shape
            for column in range(columns):
                for row in range(rows):
                    yield column, row

    def extract_sheet(self):
        t5 = time.perf_counter()
        sentences = set()
        nutrition = namedtuple('nutrition', ['name', 'value', 'unit'])
        nutrition_dict = defaultdict(set)
        print('extract_sheet')
        for column , row in self.extract_cells():
            df = self.data_frame
            text = str(df[column][row])
            web_address = re.findall(r'^www\.[a-z0-9_]+\.\D{1,3}$', text)
            if web_address:
                self.regex_captures['website'].append(text)
            findings = re.findall(r'(.*)\s?:\s?(\d+(\.\d+)?)\s?(µg|mg|kJ|g|kcal|mcg)', text)       # return list if tuple 4 values (name , value , empty/partial value,unit)
            if findings:
                for finding in findings:
                    nutrition_dict[finding[0]].add(nutrition(finding[0],finding[1],finding[3]))
            if text != 'nan' and len(text.split()) >= 3:  # this is for classifier # threshold to extract sentence
                sentences.add(text)
            elif text and text != 'nan':  # for conventional programming
                if any(unit == text for unit in self.all_unit):  # looking backward/upward for value and nutrition content
                    if (column - 1 in df.columns) and (column - 2 in df.columns):
                        if (isinstance(df[column - 1][row], int) or isinstance(df[column - 1][row], float)) and str(
                                df[column - 1][row]) != 'nan':
                            nutrition_dict[df[column - 2][row]].add(
                                nutrition(df[column - 2][row], df[column - 1][row], df[column][row]))
                    if (row-1 in df.index) and (row-2 in df.index):
                        if (isinstance(df[column][row - 1], int) or isinstance(df[column][row - 1], float)) and str(
                                df[column][row - 1]) != 'nan':
                            nutrient = " ".join((str(df[column][row-2]),str(df[column-1][row-1]),str(df[column][row])))
                            print(nutrient)
                            nutrition_dict[df[column][row - 2]].add(
                                nutrition(df[column][row - 2], df[column][row - 1], df[column][row]))
                else:
                    pass
            else:
                pass
        t6 = time.perf_counter()
        print(f'extract sheet finished in {t6-t5} seconds')
        return sentences , nutrition_dict

    def nutrition_alignment(self,nutrition_dict):
        t3 = time.perf_counter()
        nutrition_final = {}
        for key, nutrition_tuple_list in nutrition_dict.items():
            gross_value = max(nutrition_tuple_list)
            pdv_value = min(nutrition_tuple_list)
            if len(nutrition_tuple_list) == 2:
                nutrition_final[str(gross_value.name) + '_value'] = " ".join(
                    (str(gross_value.value), str(gross_value.unit)))
                nutrition_final[str(pdv_value.name) + '_pdv'] = " ".join((str(pdv_value.value), str(pdv_value.unit)))
            elif len(nutrition_tuple_list) == 1:
                nutrition_final[str(pdv_value.name)] = " ".join(
                    (str(pdv_value.value), str(pdv_value.unit)))
        t4 = time.perf_counter()
        print(f'nutrition alignment finishes in {t4-t3} seconds')
        return nutrition_final

    def classifier(self,sentences):
        classified_sentence = {}
        for sentence in sentences:
            # result = super().prediction(sentence)
            result = base('extractor',model_location).prediction(sentence)
            output = result['output']
            if output not in excel_data_exclusion:
                lang = lang_detect(sentence.replace('\n',' '))
                # lang = classify(sentence)[0]
                if output in classified_sentence:
                    classified_sentence[output].append({lang:sentence})
                else:
                    classified_sentence[output] = [{lang:sentence}]
        return classified_sentence

    def main(self):
        t1 = time.perf_counter()
        sentences , nutrition = self.extract_sheet()
        classified_sentence , aligned_nutrition = self.classifier(sentences),self.nutrition_alignment(nutrition)
        # final_touch
        if aligned_nutrition:
            classified_sentence.pop('nutrition',None)
            classified_sentence['nutrition'] = aligned_nutrition
        classified_sentence = {**classified_sentence,**self.regex_captures}
        t2 = time.perf_counter()
        print(f'Finished in {t2-t1} seconds')
        return classified_sentence
