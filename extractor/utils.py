import os
from google.cloud import translate_v2
from .models import google_api,gs1_elements
from .custom_pipeline import LaserVectorizer
import torch
from torch.nn import functional

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = google_api_creds
translate_client = translate_v2.Client()

class GoogleTranslate():
    def __init__(self, input, to_lang=None):
        if isinstance(input,dict):
            self.input_dict = input
            self.input_text = input["Text"]
            self.input_dict.pop("Text",None)
            self.input_dict.pop("To_Lang",None)
        else:
            self.input_text = input
        if to_lang:
            self.mode = "translate"
        else:
            self.mode = "language_detection"
        self.to_lang = str(to_lang).lower()
        self.output = None
        self.no_of_chars = len(self.input_text)
        self.translate_client = translate_v2.Client()

    def __enter__(self):
        print("processing the text----->",self.input_text)
        if self.mode == "translate":
            self.output = self.translate_client.translate(self.input_text, target_language=self.to_lang)
            #sample response --- > {'translatedText': 'Hello', 'detectedSourceLanguage': 'fr', 'input': 'bonjour'}
            return {"translated_text": self.output["translatedText"]}
        elif self.mode == "language_detection":
            self.output = self.translate_client.detect_language(self.input_text)
            #sample response ------> {'language': 'en', 'confidence': 1, 'input': 'hello'}
            return self.output

    def __exit__(self,exc_type, exc_value, exc_traceback):
        # pass
        print("saving to database")
        # if self.mode == "translate":
        #     try:
        #         self.output = {**self.output,**self.input_dict,**{"length": self.no_of_chars, "to_language": self.to_lang, "mode": self.mode}}
        #     except:
        #         self.output = {**self.output,**{"length": self.no_of_chars, "to_language": self.to_lang, "mode": self.mode}}
        #     print(self.output)
        # elif self.mode == "language_detection":
        #     self.output = {**self.output,**{"length": self.no_of_chars, "mode": self.mode}}
        # try:
        #     google_api(data=self.output).save()
        # except Exception as E:
        #     print(E)
        #     pass

def tag_convert(text):
    if text:
        text_converted = str(text).replace('<', '&lt;').replace('>', '&gt;')
        return text_converted

def cosine_similarity(a,b):
    if not isinstance(a, torch.Tensor):
        a = torch.tensor(a)
    if not isinstance(b, torch.Tensor):
        b = torch.tensor(b)
    if len(a.shape) == 1:
        a = a.unsqueeze(0)
    if len(b.shape) == 1:
        b = b.unsqueeze(0)
    a_norm = functional.normalize(a, p=2, dim=1)
    b_norm = functional.normalize(b, p=2, dim=1)
    return torch.mm(a_norm, b_norm.transpose(0, 1))

def search_similiar_content(input_data, input_list: list, threshold: float=0.70, no_of_similarities:int=7):
    if isinstance(input_data,str):
        print("transform to list")
        input_data = [input_data]
    similiar_texts = []
    transform = LaserVectorizer().transform
    similarity_scores = cosine_similarity(transform(input_data),transform(input_list))[0]
    top_matches = torch.topk(similarity_scores,k=no_of_similarities)
    for score, idx in zip(top_matches[0], top_matches[1]):
        if score > threshold:
            print(input_list[int(idx)],"------->(Score: {:.4f})".format(score))
            similiar_texts.append(input_list[int(idx)])
    return similiar_texts


import smbclient
class GetInput:
    def __init__(self,input_document,location_to_store,clean_pdf=None):
        self.input_document  = input_document
        self.location_to_store = location_to_store
        self.final_location = None
        self.clean_pdf_tag = clean_pdf

    def get_from_smb(self):
        '''get file downloaded from smb share'''
        if self.input_document.startswith('\\'):
            with smbclient.open_file(r"{}".format(self.input_document), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(self.location_to_store, 'wb') as pdf:
                    pdf.write(f.read())
            return self.location_to_store
        else:
            return document_location + self.input_document


    def smb_cache_clear(self):
        '''clearing cache for better connection'''
        smbclient.reset_connection_cache()
        return

    def clean_pdf(self):
        '''cleaning manual annotations in pdf'''
        import fitz
        doc = fitz.Document(self.final_location)
        for page in range(doc.page_count):
            for a in doc[page].annots():
                doc[page].delete_annot(a)
        #doc.save(self.final_location, pretty=True)
        doc.saveIncr()
        return

    def __call__(self, *args, **kwargs):
        '''miin call function'''
        self.smb_cache_clear()
        self.final_location = self.get_from_smb()
        if self.clean_pdf_tag:
            self.clean_pdf()
        return self.final_location

def get_gs1_elements():
    gs1_objects = gs1_elements.objects.all().values()
    gs1_elements_list = [gs1["gs1_element"] for gs1 in gs1_objects]
    return gs1_elements_list

