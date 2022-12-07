import pandas as pd
import numpy as np
from functools import reduce
from xlsxwriter.utility import xl_col_to_name
from langid import classify
from sklearn.neural_network import MLPClassifier
import time
from laserembeddings import Laser
import openpyxl
from .excel_processing import *
import io

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)

cate_classifier = ['ingredients', 'allergen statement', 'allergen may contain statement', 'handling statement',
                   'preparation instruction', 'prepared statement', 'storage type']

input_dataset = r"/Users/sakthivel/Documents/SGK/Excel Dataset Samples/New Format/Excel DataSet.xlsx"


output_file = io.BytesIO()

def get_file(file):
    if file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                output_file.write(f.read())
                output_file.seek(0)
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                output_file.write(f.read())
                output_file.seek(0)
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return 'SMB'
    else:
        return 'LOCAL'

def excel_extraction_new(filepath, sheetname):
    out = get_file(filepath)
    if out == 'SMB':
        wb_obj = openpyxl.load_workbook(output_file)
    else:
        file = document_location+filepath
        wb_obj = openpyxl.load_workbook(file)
    try:
        output_file.truncate(0)
    except:
        pass
    try:
        ws1 = wb_obj[sheetname]
    except:
        return {'status':0,'comment':'page does not exist'}
    df1 = pd.DataFrame(ws1.values)
    df1 = df1.fillna('n/a')
    df1 = df1.apply(lambda x: x.astype(str))
    list2 = df1.values.tolist()
    list2 = [
        [x.replace('N/A', 'n/a').replace('N/a', 'n/a').replace('n/A', 'n/a').replace('NA', 'n/a').replace('\xa0', ' ')
         for x in i] for i in list2]

    empty = []
    # for i in range(0,len(list1)):
    for j in range(0, len(list2)):
        #         if [list1[i][j]] !='n/a':
        list10 = [list2[j], j + 1]
        empty.append(list10)

    nl = []
    for i in range(0, len(empty)):
        ls = (' ').join(empty[i][0])
        nl.append(ls)

    df = pd.read_excel(excel_main_dataset,engine='openpyxl')
    x_train_laser = laser.embed_sentences(df['text'], lang='en')
    classifier = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750, random_state=0,
                               shuffle=True)
    classifier.fit(x_train_laser, df['category'])
    #         joblib.dump(classifier,excel_model_location)

    list1 = []
    for i in range(0, len(nl)):
        prediction = classifier.predict(laser.embed_sentences(nl[i], lang='en'))
        probability = classifier.predict_proba(laser.embed_sentences(nl[i], lang='en'))
        probability.sort()
        prob = probability[0][-1]
        if (prob > 0.65) or ((prob / 2) > probability[0][-2]):
            prediction1 = (nl[i], prediction[0])
        else:
            prediction1 = (nl[i], 'none')

        list1.append(prediction1)

    empty1 = []
    # for i in range(0,len(list1)):
    for j in range(0, len(list1)):
        #         if [list1[i][j]] !='n/a':
        list10 = list1[j], j + 1
        empty1.append(list10)

    nut = []
    for i in range(0, len(empty1)):
        #     for k in range (0,len(list1[i])):
        if empty1[i][0][1] == 'nutrition':
            nut.append(empty1[i])

    nl2 = []
    samp_new1 = {}
    for i in range(0, len(empty)):
        for k in range(0, len(nut)):
            if nut[k][1] == empty[i][1]:
                nl2.append(empty[i])
    if nl2:
        nl5 = nl2[0][0]
        l1 = [np.nan if x == 'n/a' else x for x in nl5]
        nl6 = pd.Series(l1)
        nl6 = nl6.first_valid_index()

        keywords = []
        for y in range(0, len(nl2)):
            #     for z in range(0,len(nl2[0][0])):
            #         if nl2[y][0][0] !='n/a':
            keywords.append(nl2[y][0][nl6])

        head = []
        for k in range(0, len(list2)):
            for j in range(0, len(list2[k])):
                if list2[k][j].lower().replace(' ', '') == '%dv':
                    head = list2[k]

        # header = []
        # for i in range(0, len(empty1)):
        #     #     for k in range (0,len(list1[i])):
        #     if empty1[i][0][1] == 'header':
        #         header.append(empty1[i])
        #
        # header2 = []
        # for i in range(0, len(empty)):
        #     for k in range(0, len(header)):
        #         if header[k][1] == empty[i][1]:
        #             header2.append(empty[i])

        # matches2 = reduce(lambda x, y: x + y, header2)
        # matches2 = [list_element for list_element in header2 if list_element]

        samp_new = {}
        for i in range(0, len(nl2)):
            for index in keywords:
                if index in nl2[i][0]:
                    some1 = nl2[i][0].index(index)
                    some1 = some1 + 1
                    for j in range(some1, len(nl2[i][0])):
                        names = {index + '_' + head[j] + '_' + str(j): [xl_col_to_name(j) + str(nl2[i][1]) + '_en',
                                                                               nl2[i][0][j]]}

                        samp_new.update(names)

        l = []
        for key, values in samp_new.items():
            #     if any(key in s):
            lis = [key, values]
            l.append(lis)
        mat = [s for s in l if any(xs in s[0] for xs in '%')]

        for i in range(0, len(mat)):
            if (((len(mat[i][1][1]) == 3 and mat[i][1][1] != 'n/a') or len(mat[i][1][1]) == 4) and mat[i][1][1] != '100'):
                k = float(mat[i][1][1])
                k = int(k * 100)
                nl10 = {mat[i][0]: [mat[i][1][0], str(k)]}
            else:
                nl10 = {mat[i][0]: [mat[i][1][0], mat[i][1][1]]}
            samp_new.update(nl10)

        samp_new1 = {}
        for key, values in samp_new.items():
            if values[1] != 'n/a':
                dt = {key: [{values[0]: values[1]}]}
                samp_new1.update(dt)
    else:
        samp_new1 = None

    gen = []
    for i in range(0, len(empty1)):
        #     for k in range (0,len(list1[i])):
        #         if empty1[i][0][1] !='nutrition' and empty1[i][0][1] !='none':
        if empty1[i][0][1] not in ['nutrition', 'none', 'header']:
            gen.append(empty1[i])

    gen2 = []
    new = None
    for i in range(0, len(empty)):
        for k in range(0, len(gen)):
            if gen[k][1] == empty[i][1]:
                gen2.append(empty[i])

    if gen2:
        nl7 = gen2[0][0]
        l1 = [np.nan if x == 'n/a' else x for x in nl7]
        nl8 = pd.Series(l1)
        nl8 = nl8.first_valid_index()

        for k in range(0, len(gen2)):
            if gen[k][0][1] != 'serving':
                gen2[k][0][nl8] = gen[k][0][1]

        keywords1 = []
        for y in range(0, len(gen2)):
            #     for z in range(0,len(nl2[0][0])):
            #         if gen2[y][0][0] !='n/a':
            keywords1.append(gen2[y][0][nl8])

        nd1 = {}
        for i in range(0, len(empty)):
            #     if len(matches2)==len(matches[i]):
            for y in keywords1:
                if y in empty[i][0]:
                    some = empty[i][0].index(y)
                    some = some + 1
                    #                 some = empty[i][0][some+1:]
                    #                 nl1.append(some)
                    el = []
                    for k in range(some, len(empty[i][0])):
                        #                     names1= y,[xl_col_to_name(k)+str(empty[i][1]),empty[i][0][k]]
                        if empty[i][0][k] != 'n/a':
                            names = {xl_col_to_name(k) + str(empty[i][1]): empty[i][0][k]}
                            el.append(names)
                            names1 = {y: el}
                            nd1.update(names1)

        final = {}
        for key, value in nd1.items():
            if key in cate_classifier:
                for content in value:
                    for cell_value, item in content.items():
                        lang = classify(item)[0]
                        classified_output = classifier.predict(laser.embed_sentences([item], lang='en'))
                        probability1 = classifier.predict_proba(laser.embed_sentences(nl[i], lang='en'))
                        probability1.sort()
                        prob1 = probability1[0][-1]
                        item = str(item).replace('<', '&lt;').replace('>', '&gt;')
                        if (prob1 > 0.65) or ((prob1 / 2) > probability1[0][-2]):
                            classified_output = classified_output[0]
                        else:
                            classified_output = 'none'
                        if classified_output not in ['none', 'others']:
                            if classified_output in final:
                                final[classified_output].append({f'{cell_value}_{lang}': item})
                            else:
                                final[classified_output] = [{f'{cell_value}_{lang}': item}]
                        elif classified_output == 'others':

                            if key in final:
                                final[key].append({f'{cell_value}_{lang}': item})
                            else:
                                final[key] = [{f'{cell_value}_{lang}': item}]
                        else:
                            pass

            else:
                for content in value:
                    for cell_value, item in content.items():
                        lang = classify(item)[0]
                        if key in final:
                            final[key].append({f'{cell_value}_{lang}': item})
                        else:
                            final[key] = [{f'{cell_value}_{lang}': item}]
        # new = {**{'Nutrition':samp_new1}, **final}
        new = final
    else:
        new = None

    final11 = {}
    if samp_new1 and new:
        attributes = []
        for row in ws1:
            for cell in row:
                if cell.font.bold:
                    attributes.append(cell.value)

        #         attributes = [x.lower() for x in attributes]
        attributes = [x.replace('\xa0', ' ') for x in attributes]

        for key, value in new.items():
            for content in value:
                for cell_value, item in content.items():
                    if item in attributes:
                        if key in final11:
                            final11[key].append({f'{cell_value}': '<b>' + item + '</b>'})
                        else:
                            final11[key] = [{f'{cell_value}': '<b>' + item + '</b>'}]
                    else:
                        if key in final11:
                            final11[key].append({f'{cell_value}': item})
                        else:
                            final11[key] = [{f'{cell_value}': item}]
        final11['Nutrition'] = samp_new1
    else:
        final11 = {'status':0,'comment':'this page is not valid'}

    return final11


