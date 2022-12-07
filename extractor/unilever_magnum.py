import pdfplumber
import mammoth
from pdf2docx import parse
from bs4 import BeautifulSoup
import fitz
import tempfile
import pandas as pd

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

from .excel_processing import *

mlp_model_1 = joblib.load(magnum_general_model)
mlp_model = joblib.load(magnum_nutrition_model)

def get_input(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location + input_pdf

def pdf_to_docx(file, pages, input_docx_location):
    parse(file, input_docx_location, pages=[pages - 1])
    return input_docx_location

def paragraph_content(output_file):
    html = mammoth.convert_to_html(output_file).value
    soup = BeautifulSoup(html, "html.parser")
    paragraphs = soup.find_all(['p', 'li'])
    start = False
    general_dic_para = {}
    para_list = []
    for para in paragraphs:
        par = [component for component in para]

        for i, content in enumerate(par):
            text = str(content)
            #         print(text)
            if "img src" not in text.lower():
                #             print(text)
                raw_html = text.replace('<strong>', 'start_bold ').replace('</strong>', ' end_bold').replace(
                    '</p>', '\n').strip()
                cleantext = BeautifulSoup(raw_html, "lxml").text
                cleantext = cleantext.replace('start_bold', '<b>').replace('end_bold', '</b>')
                cleantext = cleantext.replace('<', '&lt;').replace('>', '&gt;')
                #             print(cleantext)

                if 'legal denominator' in cleantext.lower():
                    start = True
                if 'additional declarations' in cleantext.lower():
                    start = False
                if start:
                    #                 print(cleantext)
                    para_list.append(cleantext)
                else:
                    break

    for para_value in para_list:
        Xtest_laser_1 = laser.embed_sentences(
            para_value.replace('&lt;', '').replace('&gt;', '').replace('/b', '').replace('b', ''), lang='en')
        model_op_1 = mlp_model_1.predict(Xtest_laser_1)
        classified_output_1 = model_op_1[0]
        item_prob_1 = mlp_model_1.predict_proba(Xtest_laser_1)
        item_prob_1[0].sort()
        prob_1 = item_prob_1[0][-1]

        if prob_1 >= 0.90:
            if classified_output_1 in general_dic_para:
                general_dic_para[classified_output_1].append({classify(para_value)[0]: str(para_value)})
            else:
                general_dic_para[classified_output_1] = [{classify(para_value)[0]: str(para_value)}]
        else:
            classified_output_1 = "UNMAPPED"
            if classified_output_1 in general_dic_para:
                general_dic_para[classified_output_1].append({classify(para_value)[0]: str(para_value)})
            else:
                general_dic_para[classified_output_1] = [{classify(para_value)[0]: str(para_value)}]

    return general_dic_para

def table_content_list(output_file):
    html = mammoth.convert_to_html(output_file).value
    soup = BeautifulSoup(html, "html.parser")
    # print("soup------->",soup)
    table_content_list_all = []
    for tables in soup.find_all('table'):
        for row in tables.find_all('tr'):
            column_list = []
            for column in row.find_all('td'):
                #             column_list.append(str(column).replace('<td>','').replace('</td>','').replace('</p>','').replace('<p>','').replace('<td colspan="2">','').strip())
                raw_html = str(column).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace(
                    '</p>', '\n').strip()
                cleantext = BeautifulSoup(raw_html, "lxml").text
                cleantext = cleantext.replace('start_bold', '<b>').replace('end_bold', '</b>')
                cleantext = cleantext.replace('<', '&lt;').replace('>', '&gt;').replace('\n', '')
                column_list.append(cleantext.strip())
            column_list = [i for i in column_list if i]
            #         print(column_list)
            table_content_list_all.append(column_list)

    table_content_list_all = [x for x in table_content_list_all if x != []]
    return table_content_list_all


def General_Content(table_list_of_list):
    start = False
    general_dic = {}
    final_dic = {}
    print("---------------->",table_list_of_list)
    for i, common_list in enumerate(table_list_of_list):
        common_list = [str(i) for i in common_list]
        check_str = ' '.join(common_list)

        if 'purpose' in check_str.lower() and 'description' in check_str.lower():
            start = True
        if start:
            try:
                #                     print(common_list)
                Xtest_laser_1 = laser.embed_sentences(str(common_list[1]), lang='en')
                model_op_1 = mlp_model_1.predict(Xtest_laser_1)
                classified_output_1 = model_op_1[0]
                item_prob_1 = mlp_model_1.predict_proba(Xtest_laser_1)
                item_prob_1[0].sort()

                prob_1 = item_prob_1[0][-1]
                if prob_1 >= 0.95:
                    if classified_output_1 in general_dic:
                        general_dic[classified_output_1].append({classify(common_list[1])[0]: str(common_list[1])})
                    else:
                        general_dic[classified_output_1] = [{classify(common_list[1])[0]: str(common_list[1])}]
                else:

                    classified_output_1 = "UNMAPPED"
                    if classified_output_1 in general_dic:
                        general_dic[classified_output_1].append({classify(common_list[1])[0]: str(common_list[1])})
                    else:
                        general_dic[classified_output_1] = [{classify(common_list[1])[0]: str(common_list[1])}]

            except:
                continue

    for i in range(0, len(table_list_of_list)):
        if len(table_list_of_list[i]) >= 2:
            #         print(table_content_list_all[i][1])
            if 'product name' in table_list_of_list[i][1].lower():
                #             print(table_content_list_all[i+1][1])
                if table_list_of_list[i + 1][1].strip() != '':
                    #                 print(table_content_list_all[i+1][1])
                    lang = classify(table_list_of_list[i + 1][1])[0]
                    if 'PRODUCT_NAME' in general_dic:
                        general_dic["PRODUCT_NAME"].append({lang: table_list_of_list[i + 1][1]})
                    else:
                        general_dic["PRODUCT_NAME"] = [{lang: table_list_of_list[i + 1][1]}]
    #     print(general_dic)
    return general_dic

# ********************************* NUTRI-FRMAT -1 ****************************************************
def pdf_format_1(input_file, page_no):
    with pdfplumber.open(input_file) as pdf:
        #         page = pdf.pages[0]
        try:

            page = pdf.pages[int(page_no) - 1]
            text = page.extract_text().split('\n')
            outer_list = [i.strip() for i in text if i != '']
        except:
            print("Page Num doesn't exist")
    return outer_list

'''def pdf_format_2(input_file, page_no):
    doc = fitz.Document(input_file)
    try:
        page = doc[int(page_no) - 1]
        contents = page.get_text("blocks")

        for content in contents:
            if 'DECLARACIÓN NUTRIMENTAL' in content[4] and ';' in content[4]:
                whole_content = content[4].split(';')
                outer_list = []
                for each_content in whole_content:
                    each_content_1 = re.sub(r'^.*?\[', '', each_content)
                    each_content_2 = each_content_1.replace(']', '\n').replace('DECLARACIÓN NUTRIMENTAL', '')
                    each_content_3 = each_content_2.strip().split('\n')
                    outer_list.extend(each_content_3)
        outer_list = [i.strip() for i in outer_list if i != '']
        return outer_list
    except:
        print("page Num doesn't exist")'''

def pdf_format_2(input_file,page_no):
    doc = fitz.Document(input_file)
#     page = doc[0]
    try:
        page = doc[int(page_no) - 1]
        contents = page.get_text("blocks")
        outer_list = []
        for content in contents:
            if 'DECLARACIÓN NUTRIMENTAL' in content[4] and ';' in content[4]:
                whole_content =content[4].split(';')
                outer_list = []
                for each_content in whole_content:
                    each_content_1 =re.sub(r'^.*?\[', '', each_content)
#                     print(each_content_1,"EACH ")
                    each_content_1 = each_content_1.replace('DECLARACIÓN NUTRIMENTAL','')
                    if ']' in each_content_1:
                        each_content_2 = each_content_1.replace(']','\n')
                        each_content_3 = each_content_2.strip().split('\n')
#                         print(each_content_3,"EACH 3")
                        outer_list.extend(each_content_3)
                    else:
                        outer_list.extend([each_content_1])
#                         print(each_content_1,"ELSE")
#         print('&&&&&&&&&&&&&&&&&&&&&&&&')
#         print(outer_list)
        outer_list = [i.strip() for i in outer_list if i!='']
#         print(outer_list,"%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
        return outer_list
    except:
        print("page Num doesn't exist")

# outer_list
# ****************************** Common code for both format of nutrition *******************************************************
def common_process_for_both_pdf(outer_list):
    # *******************Appending(nutrition,energy,serving)in seperate list of list******************************************************************
    energy_lst = []
    nutrition_lst = []
    serving = []
    for each_string in outer_list:
        fst = re.findall(r'[A-Za-z\u00C0-\u00D6\u00D8-\u00f6\u00f8-\u00ff\s]+', each_string)[0].strip()
        # print(fst)
        Xtest_laser = laser.embed_sentences(fst, lang='en')
        model_op = mlp_model.predict(Xtest_laser)
        classified_output = model_op[0]

        item_prob = mlp_model.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob = item_prob[0][-1]
        #         print({fst+'_'+str(prob):classified_output})
        if prob > 0.90:
            if classified_output == 'Energy':
                #                 print(inner_lst)
                energy_lst.append(each_string)
            else:
                nutrition_lst.append(each_string)
        else:
            Xtest_laser_1 = laser.embed_sentences(fst, lang='en')
            model_op_1 = mlp_model_1.predict(Xtest_laser_1)
            classified_output_1 = model_op_1[0]
            #
            item_prob_1 = mlp_model_1.predict_proba(Xtest_laser_1)
            item_prob_1[0].sort()
            prob_1 = item_prob_1[0][-1]
            #             print({fst+'_'+str(prob_1):classified_output_1})
            if prob_1 > 0.90:
                if classified_output_1 in ['SERVING_SIZE', 'SERVING_PER_CONTAINER']:
                    serving.append(each_string)
    return energy_lst, nutrition_lst, serving
    # print(serving,"SERVING")
    # print(nutrition_lst,"NUTRI")
    # print(energy_lst,"ENERGY")


# ******************************** forming dictionary ****************************************************
def Appending_dic(list_of_list):
    nutri_dic = {}
    for l in range(0, len(list_of_list)):
        for m in range(1, len(list_of_list[l])):
            if list_of_list[l][m] != '':
                if list_of_list[l][0].strip() in nutri_dic:
                    if '%' not in list_of_list[l][m]:
                        nutri_dic[list_of_list[l][0].strip()].append({'Value': {
                            'en': list_of_list[l][m].strip()}})
                    else:
                        nutri_dic[list_of_list[l][0].strip()].append({'PDV': {
                            'en': list_of_list[l][m].strip()}})
                else:
                    if '%' not in list_of_list[l][m]:
                        nutri_dic[list_of_list[l][0].strip()] = [{'Value': {
                            'en': list_of_list[l][m].strip()}}]
                    else:
                        nutri_dic[list_of_list[l][0].strip()] = [{'PDV': {
                            'en': list_of_list[l][m].strip()}}]
    return nutri_dic


# ********************** after dictionary creating making prediction *************************************************
def final_prediction(dic_values):
    dic = {}
    for keys, value in dic_values.items():

        #         print(value)
        Xtest_laser = laser.embed_sentences(keys, lang='en')
        model_op = mlp_model.predict(Xtest_laser)
        classified_output = model_op[0]

        item_prob = mlp_model.predict_proba(Xtest_laser)
        item_prob[0].sort()
        prob = item_prob[0][-1]
        #         print({classified_output+str(prob):keys})
        print("helloooooooooo------>",value)
        if prob > 0.90:
            if classified_output != 'UNMAPPED':
                if classified_output in dic:
                    dic[classified_output].extend(value)
                else:
                    dic[classified_output] = value
            else:
                if keys in dic:
                    dic[keys].extend(value)
                else:
                    dic[keys] = value
        else:
            if keys in dic:
                dic[keys].extend(value)
            else:
                dic[keys] = value
    print("bad guy--------->",dic)
    return dic

# ********************************* NUTRITION WITHOUT ENERGY ***************************************************
def NUTRITION(nutrition_lst):
    Nut_lst_3 = []
    for j in range(0, len(nutrition_lst)):
        val_1 = []
        string_1 = re.findall(r'[A-Za-z\u00C0-\u00D6\u00D8-\u00f6\u00f8-\u00ff\s]+', nutrition_lst[j])[0].strip()
        val_1.append(string_1)
        print("value----->",string_1)
        snd = [i[0].strip() for i in re.findall(r'(<?\s?(\d?\d)+(\,\d+)?\s?(mg|kj|g|%|mcg))', nutrition_lst[j])]
        val_1.extend(snd)
        print("snd----->", snd)
        Nut_lst_3.append(val_1)
    print("nut---------->",Nut_lst_3)
    return Nut_lst_3

def Energy(energy_lst):
    Energy_lst_3 = []
    header = []
    for j in range(0, len(energy_lst)):
        val_2 = []
        string_2 = re.findall(r'[A-Za-z\u00C0-\u00D6\u00D8-\u00f6\u00f8-\u00ff\s]+', energy_lst[j])[0].strip()
        # val_2.append(string_2)
        header.append(string_2)
        snd_1 = [i.strip() for i in re.findall(r'[0-9]+\s+[a-zA-Z]+\s+\([^)]*\)', energy_lst[j])]
        val_2.extend(snd_1)
        Energy_lst_3.extend(val_2)
    Energy_lst_3.append(header[0])
    return [Energy_lst_3[::-1]]

# **************************** SERVING SIZE AND CONTAINER **********************************************
def Serving_size_and_container(serving):
    Serving_lst_3 = []
    for j in range(0, len(serving)):
        val_3 = []
        string_3 = re.findall(r'[A-Za-z\u00C0-\u00D6\u00D8-\u00f6\u00f8-\u00ff\s]+', serving[j])[0].strip()
        val_3.append(string_3)
        snd_3 = [i[0].strip() for i in re.findall(r'(<?\s?(\d?\d)(\,\d+)?\s?(mg|kj|g|%|mcg)|(\d+))', serving[j])]
        val_3.extend(snd_3)
        #     print(val_3)
        Serving_lst_3.append(val_3)
    serving_values = Appending_dic(Serving_lst_3)
    # serving_values
    serv_dic = {}
    for ser_keys, ser_value in serving_values.items():
        print(ser_value)
        Xtest_laser_1 = laser.embed_sentences(ser_keys, lang='en')
        model_op_1 = mlp_model_1.predict(Xtest_laser_1)
        classified_output_1 = model_op_1[0]
        #
        item_prob_1 = mlp_model_1.predict_proba(Xtest_laser_1)
        item_prob_1[0].sort()
        prob_1 = item_prob_1[0][-1]
        #         print({classified_output+str(prob):keys})
        if prob_1 > 0.90:
            if classified_output_1 != 'None':
                if classified_output_1 in serv_dic:
                    serv_dic[classified_output_1].append(ser_value[0]["Value"])
                else:
                    serv_dic[classified_output_1] = [ser_value[0]["Value"]]
            else:
                if ser_keys in serv_dic:
                    # serv_dic[ser_keys].append(ser_value[0])
                    serv_dic[ser_keys].append(ser_value[0]["Value"])
                else:
                    # serv_dic[ser_keys] = ser_value
                    serv_dic[ser_keys] = [ser_value[0]["Value"]]
    return serv_dic

def delete_existing_doc_file(input_docx_location):
    import os
    if os.path.exists(input_docx_location):
        os.remove(input_docx_location)

def general_all_function_call(pdf_file, page_no, input_docx_location):
    delete_existing_doc_file(input_docx_location)
    docx_file = pdf_to_docx(pdf_file, page_no, input_docx_location)
    paragraph_dic = paragraph_content(docx_file)
    table_list_of_list = table_content_list(docx_file)
    General_dictionary = General_Content(table_list_of_list)
    final_dic_general = {**paragraph_dic, **General_dictionary}
    return final_dic_general

def Nutri_function_call(specific_file_format_func_call, input_file, page_no):
    outer_list = specific_file_format_func_call(input_file, page_no)
    energy_lst, nutrition_lst, serving = common_process_for_both_pdf(outer_list)
    Nutrition_clean_list = NUTRITION(nutrition_lst)
    nutri_values = Appending_dic(Nutrition_clean_list)
    Nutri_dic_1 = final_prediction(nutri_values)
    Energy_clean_list = Energy(energy_lst)
    energy_values = Appending_dic(Energy_clean_list)
    Energy_dic_1 = final_prediction(energy_values)
    Nutri_dic = {}
    Nutrition = {**Nutri_dic_1, **Energy_dic_1}
    if 'NUTRITION_FACTS' in Nutri_dic:
        Nutri_dic['NUTRITION_FACTS'].append(Nutrition)
    else:
        Nutri_dic['NUTRITION_FACTS'] = [Nutrition]
    serving_final_output = Serving_size_and_container(serving)
    # serving_final_output
    # *******************************************************************************
    inner_dic = {**serving_final_output, **Nutri_dic}
    # print(inner_dic)
    ######################################################################################
    return inner_dic

def process_pdf_file(input_file, page_no,converted_docx):
    final_dict = {}
    with pdfplumber.open(input_file) as pdf:
        if page_no-1 in range(len(pdf.pages)):
            page = pdf.pages[page_no-1]
            text = page.extract_text()
            text_table = page.extract_table()
            missing_content = missing_content_extraction(text_table)
            print("--------------->",final_dict)
            print("tables---->",text_table)
            input_docx_location = converted_docx
            # if 'general information' in text.lower():
            if 'cu pird report' in text.lower() or 'r&d artwork brief' in text.lower():
                General_dictionary = general_all_function_call(input_file, page_no, input_docx_location)
                if missing_content:
                    General_dictionary = {**General_dictionary,**missing_content}
                return General_dictionary
            else:
                if len(text_table) <= 10:
                    full_dict = Nutri_function_call(pdf_format_2, input_file, page_no)
                    return full_dict
                else:
                    full_dict = Nutri_function_call(pdf_format_1, input_file, page_no)
                    return full_dict
        else:
            return {}

def missing_content_extraction(text_table):
    df = pd.DataFrame(text_table)
    rows , columns = df.shape
    if rows >=1 and columns >=1:
        if str(df[0][0]).lower() in ('purpose'):
            content = General_Content(text_table)
            return content

def Holanda_y_Magnum_main(file_input, page_nos):
    page_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    converted_docx = f'{temp_directory.name}/converted.docx'
    input_file = get_input(file_input,input_pdf_location)
    for page_no in page_nos.split(','):
        d = process_pdf_file(input_file, int(page_no),converted_docx)
        page_dict[page_no] = d
        # if file_name not in full_dict:
        #     full_dict[file_name] = page_dict
    return page_dict


# no needed ...just to run in console
# Start = time.time()
# page_nos = '1,2,3,4'
# file_input = input_3
# full_dict = Holanda_y_Magnum_main(file_input, page_nos)
# print(full_dict)
# Stop = time.time()
# print("\nTime Taken to execute : ", Stop - Start)





