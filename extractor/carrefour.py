from langid import classify
import langid
from laserembeddings import Laser
# from textblob import TextBlob
import warnings
import joblib
from .excel_processing import language_model
import langdetect as lang_det
from langdetect import DetectorFactory
import re

DetectorFactory.seed = 1

warnings.filterwarnings("ignore")

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

# modelname1 = r"/Users/sakthivel/Documents/SGK/Carrefour/carrefour_cep_model.sav"
classifier1 = joblib.load(carrefour_CEP_model_location)

# path_to_bpe_codes = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/93langs.fcodes'
# path_to_bpe_vocab = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/93langs.fvocab'
# path_to_encoder = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/bilstm.93langs.2018-12-26.pt'

laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)

def language_detection(text):
    language_set = ['en', 'fr', 'es','nl','it','pl','ro','pt']
    langid.set_languages(['en', 'fr', 'es','nl','it','pl','ro','pt'])
    fasttext_output = language_model.predict_pro(text)[0]
    # print(f'fasttext---->{fasttext_output}')
    if fasttext_output[0] in language_set:
        if fasttext_output[1] > 0.50:
            return fasttext_output[0]
    langid_output = classify(text)[0]
    # print(f'langid---->{langid_output}')
    if langid_output in language_set:
        if langid_output == fasttext_output[0]:
            return langid_output
    langdetect_output = lang_det.detect_langs(text)[0]
    # print(f'langdetect---->{langdetect_output}')
    langdetect_lang , lang_detect_prob = str(langdetect_output).split(':')
    if langdetect_lang in language_set:
        if float(lang_detect_prob) > 0.70:
            return langdetect_lang
    return classify(text)[0]

def carrefour_cep_proccessing(cep_body):
    # # reading the data from the file
    # with open(textfile) as f:
    #     contents = f.read()
    #
    # # reconstructing the data as a dictionary
    # dictionary = json.loads(contents)
    final_dic = {}
    for layer, layer_value in cep_body.items():
        if layer not in ['Dimensions','Legend']:
            for data_dict in layer_value:
                for text_frame_no , data in data_dict.items():
                    # item = data.replace('\x03',' ')
    #                 item = item.lower()
    #                 item = str(item).split('\r')
                    item = re.sub(r"(\/)(?!min)","\r",str(data))
                    item = re.split(r"\r|\u0003",str(item))
                    # print(f'{text_frame_no}------>{item}')
                    for k1 in item:
                        split = k1.split(u'\u2022')
                        for k in split:
                            # language = classify(k)[0]
                            k = str(k).strip()
                            language = language_detection(k)
                            if len(k.split()) > 0:
                                classified_output = classifier1.predict(laser.embed_sentences(re.sub(r"[a-z]{1}[^a-z0-9]{1}(0|1)","",k.lower().replace('\t','')), lang='en'))
                                probability1 = classifier1.predict_proba(laser.embed_sentences(re.sub(r"[a-z]{1}[^a-z0-9]{1}(0|1)","",k.lower().replace('\t','')), lang='en'))
                                probability1.sort()
                                prob1 = probability1[0][-1]
            #                     if (prob1 > 0.65) or ((prob1 / 2) > probability1[0][-2]):
                                print(f"{k}----------------->[{classified_output}<---->{prob1}]")
                                if prob1 > 0.73 and "variety" not in classified_output[0].lower():
                                    classified_output1 = classified_output[0]
                                elif "variety" in classified_output[0].lower() and prob1 > 0.90:
                                    print("---------------->",k)
                                    classified_output1 = "variety"
                                else:
                                    classified_output1 = 'Unmapped'

                                if classified_output1 not in ['Design Instruction','Address','None']:
                                    if classified_output1 in final_dic:
                                        final_dic[classified_output1].append({f'{language}':k})
                                    else:
                                        final_dic[classified_output1]=[{f'{language}':k}]
                            else:
                                if 'Unmapped' in final_dic:
                                    final_dic['Unmapped'].append({f'{language}':k})
                                else:
                                    final_dic['Unmapped'] = [{f'{language}':k}]
        else:
            pass
    # print(item,classified_output1)

    unwanted_key = []
    unwanted_value = []
    for key , value in final_dic.items():
        if 'variety' in key.lower():
            unwanted_key.append(key)
            unwanted_value.extend(value)
    for un_key in unwanted_key:
        try:
            final_dic.pop(un_key, None)
        except:
            pass
    final_dic["variety"] = unwanted_value

    final_cleaned_dict = {}
    for category , value_list in final_dic.items():
        final_cleaned_dict[category] = sorted(list({frozenset(list_element.items()) : list_element for list_element in value_list}.values()),key=lambda d: list(d.keys()))
    return final_cleaned_dict
