from .dev_constants import *
import mammoth
from bs4 import BeautifulSoup
from langid import classify
import re
from laserembeddings import Laser
import joblib
import time
from .excel_processing import *
import warnings
import tempfile
nutri_model = mead_johnson_nutrition_model
gen_model = mead_johnson_general_model

def get_input(input_file, input_docx_location):
    if input_file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_docx_location, 'wb') as docx:
                    docx.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_docx_location, 'wb') as docx:
                    docx.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_docx_location
    else:
        return document_location + input_file

#function for model
def load_model(model_path):
    return joblib.load(model_path)


#Working code type2 --> file extracted docx to html format
def docx_file_input(file):
    with open(file,"rb") as docx_file:
        html = mammoth.convert_to_html(docx_file).value
        return html

# function for all extract information(exclude the informtion from inside the table tag)
def paragraph_extraction(html_raw):
    html_general_catagory = re.sub(r'<table>.*?<\/table>', '', html_raw)# remove table tab
    General_paragragh_content = BeautifulSoup(html_general_catagory,"html.parser")
    return General_paragragh_content

# function for extract information for work table tag
def table_extraction(html_raw):
    file_table_content = BeautifulSoup(html_raw,"html.parser")
    return file_table_content



def table_function(html_data):
    tables = []
    for table1 in html_data.find_all("table"):
        _table = []
        for row in table1.find_all("tr"):
            _row = []
            for column in row.find_all("td"):
                column = str(column).replace('<strong>', 'lt;&bgt;').replace('</strong>', 'lt;&bgt;')
                column = re.sub(r'<(?!b|\/b).*?>','',str(column))
                column = re.sub(r'\<\/?br\/?\>','\n',str(column))
#                 column = re.sub(r'\<.*?\>',' ',str(column))
                _row.append(str(column))
    #             print(column.text)
    #                 _row.append(column.text)
            _table.append(_row)
        tables.append(_table)
    return tables


#function for paragraph information into list of list
def paragraph_function(html_dat):
        para_content = []
        for img in html_dat.find_all("img"):
            img.decompose()
        for para1 in html_dat.find_all("p"):
            para_gen = re.sub(r'<.*?>', '', str(para1).replace("<strong>","lt;&bgt;").replace("</strong>", "lt;/&bgt;").strip())
            para_content.append(para_gen)
        return para_content


#main function
def main(data,file):
    html_raw = docx_file_input(file)
    if data == "para":
        paragragh_information = paragraph_extraction(html_raw)
        paragraph_list_extraction = paragraph_function(paragragh_information)
        return paragraph_list_extraction
    elif data == "table":
        table_information = table_extraction(html_raw)
        table_list_extraction = table_function(table_information)
        return table_list_extraction


def table_data_info(data, file):
    result_info = main("table",file)
    ert = {}
    for nut_con in result_info:
        nut_diction = {}
#         if len(nut_con)>=10:
        if 'nutrients' in nut_con[0][0].lower().strip() or "项目" in nut_con[0][0].lower().strip():
            for loop1 in nut_con:
                key_nutri = loop1[0].replace('lt;&bgt;','').strip()
                val_nut = loop1[1:]
                classifier = load_model(nutri_model)
                x1 = classifier.predict_proba(laser.embed_sentences(key_nutri, lang = "en"))[0]
                x1.sort()
                classified = classifier.predict(laser.embed_sentences(key_nutri, lang = "en"))[0]
                if x1[-1]>0.70:
                    classi_key = classified
                else:
                    classi_key = "UNMAPPED"
                for d1 in range(len(val_nut)):
                    val_nutri = val_nut[d1].replace("\xa0","").strip()#.replace('lt;&bgt;','')
                    val_nutri1 = val_nut[d1].replace("\xa0","").replace('lt;&bgt;','').strip()
                    if val_nutri1:
                        if "%" in val_nutri1:
                            value_header = "PDV"
                        elif val_nutri1 in ['mg','g','μg','kJ','mg α-TE','mg a-TE','mg RE','μg RE','克g','千焦','克','毫克','微克视黄醇当量','毫克a-生育酚当量','毫克\uf061-生育酚当量','微克','毫克α-生育酚当量']:
                            value_header = "Unit"
                        else:
                            value_header = "Value"
                        if classi_key in nut_diction:
                            nut_diction[classi_key].append({value_header:{classify(val_nutri)[0]:val_nutri}})
                        else:
                            nut_diction[classi_key] = [{value_header:{classify(val_nutri)[0]:val_nutri}}]
        if nut_diction:
            if "NUTRITION_FACTS" in ert:
                ert["NUTRITION_FACTS"].append(nut_diction)
            else:
                ert["NUTRITION_FACTS"] = [nut_diction]
    return ert


def other_data_info(data,file):
    result_info = main("table",file)
    other_dict = {}
    for otr_con in result_info:
        if len(otr_con)<=10:
            for other_instr in otr_con:
                if len(other_instr)>1:
                    for lev_1 in range(len(other_instr)):
                        value_1 = other_instr[lev_1].strip()
                        if value_1:
                            if "OTHER_INSTRUCTIONS" in other_dict:
                                other_dict["OTHER_INSTRUCTIONS"].append({classify(value_1)[0]:value_1})
                            else:
                                other_dict["OTHER_INSTRUCTIONS"] = [{classify(value_1)[0]:value_1}]
                else:
                    for unmap in other_instr:
                        other_dict.setdefault("UNMAPPED", []).append({classify(unmap)[0]:unmap})
    return other_dict


def para_data_info(data,file):
    result_info = main("para",file)
    net_con = {}
    gen_web = {}
    con_org = {}
    contac_dic = {}
    gen_cate_dic = {}
    for gen_cont in result_info:
        if "净含量" in gen_cont or "net weight" in gen_cont.lower():
            net_val = re.split(r'[:：]\s*', gen_cont) #---> two type of colon in net content element
            net_val = net_val[1:][0].strip()
            net_con.setdefault("NET_CONTENT_STATEMENT", []).append({classify(net_val)[0]:net_val.strip()})
        elif "www." in gen_cont.lower():
            gen_web.setdefault("WEBSITE", []).append({classify(gen_cont)[0]:gen_cont.strip()})
        elif "country of origin" in gen_cont.lower():
            con_org.setdefault("LOCATION_OF_ORIGIN", []).append({classify(gen_cont)[0]:gen_cont.strip()})
        elif "热线" in gen_cont or "hotline number" in gen_cont.lower().strip():
            contac_dic.setdefault("CONTACT_INFORMATION", []).append({classify(gen_cont)[0]:gen_cont.strip()})
        else:
            clean_text = gen_cont.replace("lt;&bgt;","").replace("lt;/&bgt;","").replace("\xa0","").strip()
            classifier_gen = load_model(gen_model)
            gen1 = classifier_gen.predict_proba(laser.embed_sentences(clean_text, lang = "en"))[0]
            gen1.sort()
            classified_general = classifier_gen.predict(laser.embed_sentences(clean_text, lang = "en"))[0]
            if gen1[-1]>0.80:
                classi_gen = classified_general
            else:
                classi_gen = "UNMAPPED"
            if classi_gen in gen_cate_dic:
                gen_cate_dic[classi_gen].append({classify(gen_cont)[0]:gen_cont.replace("\xa0",'').strip()})
            else:
                gen_cate_dic[classi_gen] = [{classify(gen_cont)[0]:gen_cont.replace("\xa0",'').strip()}]
    return{**gen_cate_dic,**net_con,**gen_web,**con_org,**contac_dic}


def mead_final_main(path):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_docx_location = f'{temp_directory.name}/input_docx.docx'
    file = get_input(path, input_docx_location)
    table_data_content = table_data_info("table", file)
    other_data_content = other_data_info("table",file)
    para_data_content = para_data_info("para",file)
    final_output = {}
    for diction in [table_data_content,other_data_content,para_data_content]:
        for key, valuee in diction.items():
            if key in final_output:
                final_output[key].extend(valuee)
            else:
                final_output[key] = valuee
#     final_output = table_data_content,para_data_content,other_data_content
    return final_output



