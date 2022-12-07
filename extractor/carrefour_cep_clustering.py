import re

# from textblob import TextBlob
import warnings
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.metrics import silhouette_samples, silhouette_score
warnings.filterwarnings("ignore")
from sklearn.mixture import GaussianMixture
from sklearn.cluster import KMeans , DBSCAN , SpectralClustering
from collections import Counter
from langid import classify
import langid
import json
import langdetect as lang_det

from termcolor import colored

from .excel_processing import *

def txt_to_dict(txt_file):
    with open(txt_file) as f:
        contents = f.read()
    dictionary = json.loads(contents)
    return dictionary

def dict_to_list(dictionary):
    final_list = []
    for layer, layer_value in dictionary.items():
        if layer not in ['Dimensions','Legend']:
            for data_dict in layer_value:
                for text_frame_no , data in data_dict.items():
                    item = re.sub(r"(\/)(?!min)","\r",str(data))
                    item = re.split(r"\r|\u0003",str(item))
                    # print(f'{text_frame_no}------>{item}')
                    for k1 in item:
                        split = k1.split(u'\u2022')
                        for k in split:
                            if k.strip() and len(k) > 2:
                                final_list.append(str(k).strip())
    return list(set(final_list))


def gauss_cluster_iteration(copy_list):
    print("len of input----->",len(copy_list))
    copy_list = [item for item in copy_list if len(re.sub(r"\D\$[01]","",str(item)).strip()) > 2]
    gauss_dict_list = []
    random_state = 42
    for i in range(0, 20):
        if len(copy_list) > 10:
            print("======"*15)
            print("Iteration number--------->",i)
            print("len of input cleaned----->", colored(len(copy_list),"cyan"))
            print("======"*15)
            gauss_dict = {}
            # new_dataframe = copy_list
            new_dataframe_cleaned = [re.sub(r"\D\$[01]","",str(value)) for value in copy_list]
            new_dataframe_cleaned = [re.sub(r"^\D\s(.*)",lambda pat: pat.group(1),str(value)).strip() for value in new_dataframe_cleaned]
            print(new_dataframe_cleaned)
            new_x_train = laser.embed_sentences(new_dataframe_cleaned, lang='en')
            # new_x_train = labse.encode(new_dataframe_cleaned)

            count = round(len(new_x_train) / 7)
            # optimum_cluster = find_optimum_clusters(new_x_train,random_state)
            # count = optimum_cluster[max(optimum_cluster)]
            db = GaussianMixture(n_components=count,random_state=random_state,covariance_type='spherical')
            # db = DBSCAN(eps=0.3, min_samples=7)
            # db = SpectralClustering(n_clusters=count)
            # db = KMeans(n_clusters=count, init='k-means++', n_init=count+2, max_iter=300)
            db.fit(new_x_train)
            # labels = db.predict(new_x_train)
            labels = db.fit_predict(new_x_train)
            score = silhouette_score(new_x_train, labels)

            result = Counter(labels)

            unmatch_list = []
            new_match_list = []
            for k, v in result.items():
                if v in [5, 6, 7]:
                    #         print(k)
                    new_match_list.append(k)
                else:
                    unmatch_list.append(k)
            # print("match list---------->",new_match_list)
            indx_list = []

            for j in range(0, len(labels)):
                for k in new_match_list:
                    if labels[j] == k:
                        indx_list.append(j)
                        content = str(copy_list[j])
                        tag = re.search(r"(\D\$)[01]",content)
                        if tag:
                            if re.search(r"\D\$0",content) and not re.search(r"\D\$1",content):
                                content = content+str(tag.group(1))+"1"
                            elif not re.search(r"\D\$0",content) and re.search(r"\D\$1",content):
                                content = str(tag.group(1))+"0"+content
                        try:
                            lang = language_detection(re.sub(r"\D\$[01]","",content).strip())
                        except:
                            lang = classify(re.sub(r"\D\$[01]","",content).strip())[0]
                        if 'cluster' + str(k) in gauss_dict:
                            gauss_dict['cluster' + str(k)].append({lang: content})
                        else:
                            gauss_dict['cluster' + str(k)] = [{lang: content}]

            elements_removed = []
            # '''
            gauss_dict_copy = gauss_dict.copy()
            for cluster_name , value_list in gauss_dict_copy.items():
                original_value_list = value_list.copy()
                print("element going for validation------>",colored(value_list,"green"))
                # validation_result , element_to_pop = validation(value_list)
                # validation_result , element_to_pop = validation_upgrade(value_list)
                validation_result , element_to_pop = validation_upgrade_v2(value_list)

                print("validation_result------>", colored(validation_result,"yellow"),"------->",colored(element_to_pop,"red"))
                if validation_result and (len(value_list)-len(element_to_pop)) < 4:
                    validation_result = False
                    print("validation_result changed due to minimum no of elements------>", validation_result)
                if validation_result:
                    for index in element_to_pop:
                        elements_removed.append(list(original_value_list[index].values())[0])
                        original_value_list.pop(index)
                    gauss_dict[cluster_name] = original_value_list
                else:
                    remove_list = [value for mini_dict in value_list for key , value in mini_dict.items()]
                    elements_removed.extend(remove_list)
                    gauss_dict.pop(cluster_name,None)
                    # '''
                print("After validation--------->",original_value_list)

            if gauss_dict:
                gauss_dict_list.append(gauss_dict)
            else:
                random_state = random_state + 1

            indx_list.sort(reverse=True)
            for i in indx_list:
                del copy_list[i]
            copy_list.extend(elements_removed)
            # print("copylist-------->",copy_list)
    return gauss_dict_list, copy_list


def final_dict(gauss_cluster_form):
    final_dict = {}
    count = 0
    if gauss_cluster_form:
        for dic in range(0, len(gauss_cluster_form)):
            for k, v in gauss_cluster_form[dic].items():
                count = count + 1
                if 'CLUSTER_' + str(count) in final_dict:
                    final_dict['CLUSTER_' + str(count)].append(v)
                else:
                    final_dict['CLUSTER_' + str(count)] = v
    return final_dict


def unmapped_dict(copy_list):
    unmapped_dic = {}
    if copy_list:
        for i in range(0, len(copy_list)):
            if copy_list[i].strip():
                content = str(copy_list[i])
                tag = re.search(r"(\D\$)[01]", content)
                if tag:
                    if re.search(r"\D\$0", content) and not re.search(r"\D\$1", content):
                        content = content + str(tag.group(1)) + "1"
                    elif not re.search(r"\D\$0", content) and re.search(r"\D\$1", content):
                        content = str(tag.group(1)) + "0" + content
                try:
                    lang = language_detection(content)
                except:
                    lang = classify(content)[0]
                if 'UNMAPPED' in unmapped_dic:
                    unmapped_dic['UNMAPPED'].append({lang: content})
                else:
                    unmapped_dic['UNMAPPED'] = [{lang: content}]
    return unmapped_dic


from .utils import search_similiar_content
def carrefour_cep_main(dictionary,brand_name=None):
    brand_dict = {}
    t5 = time.time()
    # dictionary = txt_to_dict(txt_file)
    final_list = dict_to_list(dictionary)
    final_list = [item for item in final_list if len(re.sub(r"\D\$[01]","",str(item)).strip()) > 2]
    print(final_list)
    if brand_name:
        brand_names = search_similiar_content([brand_name],final_list,no_of_similarities=8)
        for brand in brand_names:
            if "variety" in brand_dict:
                brand_dict["variety"].append({language_detection(brand):brand})
            else:
                brand_dict["variety"] = [{language_detection(brand): brand}]
            final_list.remove(brand)
        print("brand_names-------->",brand_names)
    print(f'length of list original list {len(final_list)}')
    copy_list = final_list.copy()
    print(f'length of list copy list {len(copy_list)}')
    print('Cluster Iteration begins')
    gauss_cluster_form, gauss_list = gauss_cluster_iteration(copy_list)
    final_dic = final_dict(gauss_cluster_form)
    unmapped_dic = unmapped_dict(gauss_list)
    t6 = time.time()
    print(f'Finished in {t6 - t5} seconds')
    # return final_dic
    return {**brand_dict, **final_dic, **unmapped_dic}

def validation(input_cluster:list):
    # input_cluster_original = input_cluster.copy()
    condition_to_discard = 0
    element_to_pop_index = []
    input_cluster = [re.sub(r"\D\$[01]","",str(value)) for dict in input_cluster for key , value in dict.items()]
    input_cluster = [re.sub(r"^\D\s(.*)", lambda pat: pat.group(1), str(value)).strip() for value in input_cluster]
    for index in range(len(input_cluster)):
        if condition_to_discard < np.ceil(len(input_cluster)/2):
            start_value = input_cluster[index]
            temp_list = []
            for current_value in input_cluster:
                similarity = cosine_similarity(laser.embed_sentences(start_value, lang='en'),
                                               laser.embed_sentences(current_value, lang='en'))[0][0]
                if similarity > 0.70:
                    temp_list.append(similarity)
            # print(temp_list)
            if len(temp_list) < 4:
                condition_to_discard = condition_to_discard+1
                # print("condition to discard---->",condition_to_discard)
                element_to_pop_index.append(index)
                print("element to pop------>",colored(start_value,"red"))
        else:
            print("Not a valid cluster")
            return False , None
    element_to_pop_index.sort(reverse=True)
    print(element_to_pop_index)
    print("valid cluster")
    return True , element_to_pop_index

# from .utils import GoogleTranslate
# def language_detection(text) -> str:
#     with GoogleTranslate(text) as out:
#         return out["language"]

# def language_detection(text):
#     language_set = ['en', 'fr', 'es','nl','it','pl','ro','pt']
#     langid.set_languages(['en', 'fr', 'es','nl','it','pl','ro','pt'])
#     fasttext_output = language_model.predict_pro(text)[0]
#     # print(f'fasttext---->{fasttext_output}')
#     if fasttext_output[0] in language_set:
#         if fasttext_output[1] > 0.50:
#             return fasttext_output[0]
#     langid_output = classify(text)[0]
#     # print(f'langid---->{langid_output}')
#     if langid_output in language_set:
#         if langid_output == fasttext_output[0]:
#             return langid_output
#     langdetect_output = lang_det.detect_langs(text)[0]
#     # print(f'langdetect---->{langdetect_output}')
#     langdetect_lang , lang_detect_prob = str(langdetect_output).split(':')
#     if langdetect_lang in language_set:
#         if float(lang_detect_prob) > 0.70:
#             return langdetect_lang
#     return classify(text)[0]

from .utils import GoogleTranslate
from .excel_processing import language_model
def language_detection(text):
    language_set = ['en', 'fr', 'es', 'nl', 'it', 'pl', 'ro', 'pt']
    langid.set_languages(['en', 'fr', 'es', 'nl', 'it', 'pl', 'ro', 'pt'])
    text = re.sub(r'[^\w\s]', '', text).strip()
    text = text.replace('\n',' ')
    if text.strip():
        try:
            lang = language_model.predict_lang(text)
            if lang in language_set:
                return lang
            else:
                return classify(text)[0]
        except:
            return classify(text)[0]
        # with GoogleTranslate(text) as output:
        #     lang = output["language"]
        #     if lang in language_set:
        #         return lang
    return classify(text)[0]

from sentence_transformers import util
from .utils import cosine_similarity as cos_sim
def validation_upgrade(input_cluster:list):
    condition_to_discard = 0
    element_to_pop_index = []
    input_cluster = [re.sub(r"\D\$[01]","",str(value)) for dict in input_cluster for key , value in dict.items()]
    input_cluster = [re.sub(r"^\D\s(.*)", lambda pat: pat.group(1), str(value)).strip() for value in input_cluster]
    for index in range(len(input_cluster)):
        if condition_to_discard < np.ceil(len(input_cluster)/2):
            start_value = input_cluster[index]
            similarity_scores = cos_sim(laser.embed_sentences(start_value, lang='en'),
                                               laser.embed_sentences(input_cluster, lang='en'))
            similarity_scores = list(np.array(similarity_scores)[0])
            print(start_value,"-------->",similarity_scores)
            index_to_select = [index for index,score in enumerate(similarity_scores) if score > 0.70]
            if len(index_to_select) < np.ceil(len(input_cluster)/2):
                condition_to_discard = condition_to_discard+1
                element_to_pop_index.append(index)
                print("element to pop------>",colored(start_value,"red"))
        else:
            print("Not a valid cluster")
            return False , None
    element_to_pop_index.sort(reverse=True)
    print(element_to_pop_index)
    print("valid cluster")
    return True , element_to_pop_index


def find_optimum_clusters(X,random_state):
    cluster = {}
    new_x_train = X
    count = round(len(new_x_train) / 7)
    for no_of_cluster in reversed(range(4,count)):
        db = GaussianMixture(n_components=no_of_cluster,random_state=random_state,covariance_type='spherical')
        # db = KMeans(n_clusters=count, init='k-means++', n_init=count + 2, max_iter=300)
        db.fit(new_x_train)
        labels = db.fit_predict(new_x_train)
        score = silhouette_score(new_x_train, labels)
        cluster[score] = no_of_cluster
        print("cluster_number---->",no_of_cluster,"---------->score------->",score)
        if score > 0.13:
            break
    return cluster

def validation_upgrade_v2(input_cluster:list):
    condition_to_discard = 0
    element_to_pop_index = []
    input_cluster = [re.sub(r"\D\$[01]","",str(value)) for dict in input_cluster for key , value in dict.items()]
    input_cluster = [re.sub(r"^\D\s(.*)", lambda pat: pat.group(1), str(value)).strip() for value in input_cluster]
    input_cluster_embedded = laser.embed_sentences(input_cluster,lang="en")
    similarity_tensor = cos_sim(input_cluster_embedded,input_cluster_embedded)
    for index in range(len(input_cluster)):
        if condition_to_discard < np.ceil(len(input_cluster)/2):
            start_value = input_cluster[index]
            similarity_scores = similarity_tensor[index]
            index_to_select = [score for score in similarity_scores if score > 0.70]
            # if len(index_to_select) < np.ceil(len(input_cluster)/2):
            if len(index_to_select) < 4:
                condition_to_discard = condition_to_discard+1
                element_to_pop_index.append(index)
                print("element to pop------>",colored(start_value,"red"))
        else:
            print("Not a valid cluster")
            return False , None
    element_to_pop_index.sort(reverse=True)
    print(element_to_pop_index)
    print("valid cluster")
    return True , element_to_pop_index