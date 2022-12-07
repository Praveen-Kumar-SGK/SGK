import pdfplumber
import re
import mammoth
from bs4 import BeautifulSoup
from sklearn.neural_network import MLPClassifier
from langid import classify
import pandas as pd
import joblib
from laserembeddings import Laser
from pdf2docx import parse, Converter
import time
import tempfile
from .excel_processing import *

# machine learning classifier
classifier = joblib.load(heinz_model_location)
# document_location = r"/Users/sakthivel/Documents/SGK/Heinz/"

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
        return document_location+input_file


# In[ ]:


def pdf_to_docx(file, converted_docx,page_no):
    # convert pdf to docx
    parse(file, converted_docx, pages=[page_no - 1])
#     parse(file, path, start= pages-1, end=pages)
    html = mammoth.convert_to_html(converted_docx).value
    html = html.replace('<p>','\n<p>')
    soup = BeautifulSoup(html, "html.parser")
    return soup


# In[ ]:


def table_content(soup):
    tables = []
    for table1 in soup.find_all('table'):
        _table = []
        for row in table1.find_all("tr"):
            _row = []
            for column in row.find_all("td"):
                column = str(column).replace('<strong>', '<b>').replace('</strong>', '</b>')
                column = re.sub(r'<(?!b|\/b).*?>','',str(column))
                column = re.sub(r'\<\/?br\/?\>','\n',str(column))
#             column = re.sub(r'\<.*?\>',' ',str(column))
                _row.append(str(column))
    #             print(column.text)
#                 _row.append(column.text)
            _table.append(_row)
        tables.append(_table)
    return tables


# In[ ]:


# working
def serv_nutr(table_data):
    nutrition_diction = {}
    serv_diction = {}
    for line1 in table_data:
        nut_diction = {}
        if "nutrition information" in line1[0][0].lower():
            for l1 in line1:
                ser = []
                for ser_pack in l1:
                    for pattern in ("Serving size:","Servings per package:"):
                        if pattern in ser_pack:
    #                         ser.append(ser_pack)
                            siz = ser_pack.replace('<', '&lt;').replace('>', '&gt;')
                            key_ser = "SERVING_SIZE"
                            if key_ser in serv_diction:
                                serv_diction[key_ser].append({classify(siz)[0]:siz.strip()})
                            else:
                                serv_diction[key_ser] = [{classify(siz)[0]:siz.strip()}]
#                 ser = [s for s in l1 if "Serving size:" in s]
#                 for k1, k2 in enumerate(ser):
#                     siz_ltgt = k2.replace('Serving size:','')
#                     siz = siz_ltgt.replace('<', '&lt;').replace('>', '&gt;')
#                     key_ser = "SERVING_SIZE"
#                     if key_ser in serv_diction:
#                         serv_diction[key_ser].append({classify(siz)[0]:siz})
#                     else:
#                         serv_diction[key_ser] = [{classify(siz)[0]:siz}]
    #             refd = re.sub(r"[^a-zA-zA-Z]","",l1[0])
    #             print(l1[0].lower())
                nut = l1[0].replace("-",'').replace(':','').replace(',','').lower().strip()
                x_nut = classifier.predict_proba(laser.embed_sentences(nut, lang = "en"))[0]
                x_nut.sort()
                classified = classifier.predict(laser.embed_sentences(nut,lang = "en"))[0]
                if x_nut[-1]>0.60:
                    classified_key = classified
                else:
                    classified_key = "UNMAPPED"
                for seco_val in range(2,len(l1)):
                    va1 = l1[seco_val]
                    value_nut_ltgt = str(va1).strip()
                    value_nut = value_nut_ltgt.replace('<', '&lt;').replace('>', '&gt;')
#                     if value_nut not in ("nan","None","0","[]"):
                    if value_nut != "None":
                        if "%" in value_nut:
                            header_value = "PDV"
                        else:
                            header_value = "Value"
                        if classified_key not in ("UNMAPPED"):
                            if classified_key in nut_diction:
                                nut_diction[classified_key].append({header_value:{classify(value_nut)[0]:value_nut.strip()}})
                            else:
                                nut_diction[classified_key] = [{header_value:{classify(value_nut)[0]:value_nut.strip()}}]
                        else:
                            # serv_diction.setdefault(classified_key, []).append({header_value:{classify(value_nut)[0]:value_nut.strip()}})
                            serv_diction.setdefault(classified_key, []).append({classify(value_nut)[0]:value_nut.strip()})

        if nut_diction:
            if "NUTRITION_FACTS" in nutrition_diction:
                nutrition_diction["NUTRITION_FACTS"].append(nut_diction)
            else:
                nutrition_diction["NUTRITION_FACTS"] = [nut_diction]
    return {**nutrition_diction,**serv_diction}


# In[ ]:


def unmap_conte_nutri(table_data):
    nut_unmap = {}
    for line123 in table_data:
        if "<b>Country Of Origin</b>" in line123[0]:#--> MAF and Date codeing searched base country of origin
            for unmap_conte in line123:
                if "MAF Legend" in unmap_conte[0]:
                    maf_value = unmap_conte[1:]
                    for nutri_unmap in range(0, len(maf_value)):
                        unmap_nutri = maf_value[nutri_unmap][0:]
                        if "OTHER_INSTRUCTIONS" in nut_unmap:
                            nut_unmap["OTHER_INSTRUCTIONS"].append({classify(unmap_nutri)[0]:unmap_nutri.strip()})
                        else:
                            nut_unmap["OTHER_INSTRUCTIONS"]=[{classify(unmap_nutri)[0]:unmap_nutri.strip()}]
                elif "Date Coding &amp; Lot ID Coding" in unmap_conte[0]:
                    Date_code = unmap_conte[1:]
                    for nutri_unmap12 in range(0, len(Date_code)):
                        unmap_nutri12 = Date_code[nutri_unmap12][0:]
                        if "OTHER_INSTRUCTIONS" in nut_unmap:
                            nut_unmap["OTHER_INSTRUCTIONS"].append({classify(unmap_nutri12)[0]:unmap_nutri12.strip()})
                        else:
                            nut_unmap["OTHER_INSTRUCTIONS"]=[{classify(unmap_nutri12)[0]:unmap_nutri12.strip()}]
        else:
            if "<b>Other On-Pack Statements</b>" in line123[0]:
                for unmap_conte34 in line123:
                    for nutri_unmap34 in range(1, len(unmap_conte34)):
                        unmap_nutri34 = unmap_conte34[nutri_unmap34][0:]
                        if "OTHER_INSTRUCTIONS" in nut_unmap:
                            nut_unmap["OTHER_INSTRUCTIONS"].append({classify(unmap_nutri34)[0]:unmap_nutri34.strip()})
                        else:
                            nut_unmap["OTHER_INSTRUCTIONS"]=[{classify(unmap_nutri34)[0]:unmap_nutri34.strip()}]
    return nut_unmap


# In[ ]:


def gen_cat_data(table_data):
    gen_category = {}
    is_ingredient_availble = False
    for index,gen_cat in enumerate(table_data):
        for gen_cat1 in gen_cat:#---> Work for brandname,product_name, net_Qty
            gen = gen_cat1[0].replace(':','').replace('/','').replace('<b>','').replace('</b>','').lower().strip()
            if gen in ["sub brand","product fgi","date created","nut data date","status","brand","product name","pack size","coo labelling","company name &amp; address","quality statement &amp; \nconsumer enquiries \ncontact details"]:
                assign_key = {'sub brand':"GENERIC_NAME",'product fgi':"UNMAPPED",'status':"UNMAPPED",'nut data date':"UNMAPPED",'date created':"UNMAPPED",'brand':"BRAND_NAME",'product name':"FUNCTIONAL_NAME",'pack size':"NET_CONTENT",'coo labelling':"LOCATION_OF_ORIGIN",'company name &amp; address':"CONTACT_INFORMATION",'quality statement &amp; \nconsumer enquiries \ncontact details':"LOCAL_CONTACT_INFORMATION"}
                gen_val_ltgt = str(gen_cat1[1:][0]).strip()
                gen_val = gen_val_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                if gen_val not in ("nan",None,"0","[]","N/A",""):
                    if assign_key[gen] in gen_category:
                        gen_category[assign_key[gen]].append({classify(gen_val)[0]:gen_val.strip()})
                    else:
                        gen_category[assign_key[gen]] = [{classify(gen_val)[0]:gen_val.strip()}]
    #             ds = re.sub(r'(?:|\W)social media(?:$|\W)',"",gen)#----> working for only website
            elif "website" in gen:
                web_value_ltgt = gen_cat1[1]
                web_value = web_value_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                if web_value not in ("nan",None,"0","[]","N/A",""):
                    if "WEBSITE" in gen_category:
                        gen_category["WEBSITE"].append({classify(web_value)[0]:web_value.strip()})
                    else:
                        gen_category["WEBSITE"] = [{classify(web_value)[0]:web_value.strip()}]
            elif "allergens" in gen:
                for a1 in range(1,len(gen_cat1)):
                    allergen_va = gen_cat1[a1]
                    val_aller_ltgt = str(allergen_va[0:]).strip()
                    val_aller = val_aller_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                    if val_aller not in ("nan",None,"0","[]","N/A",""):
                        if "ALLERGEN_STATEMENT" in gen_category:
                            gen_category["ALLERGEN_STATEMENT"].append({classify(val_aller)[0]:val_aller.strip()})
                        else:
                            gen_category["ALLERGEN_STATEMENT"] = [{classify(val_aller)[0]:val_aller.strip()}]
            elif "claims" in gen:
                if "claims:" in gen_cat1[0]:
                    for c1 in range(1,len(gen_cat1)):
                        claim_va = gen_cat1[c1]
                        claim_value_ltgt = str(claim_va[0:])
                        claim_value = claim_value_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                        if "MARKETING_CLAIM" in gen_category:
                            gen_category["MARKETING_CLAIM"].append({classify(claim_value)[0]:claim_value.strip()})
                        else:
                            gen_category["MARKETING_CLAIM"] = [{classify(claim_value)[0]:claim_value.strip()}]
            elif is_ingredient_availble:
                val_in = table_data[index]
                val_ingre_ltgt = val_in[0][1]
                val_ingre = val_ingre_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                is_ingredient_availble = False
                if "INGREDIENTS_DECLARATION" in gen_category:
                    gen_category["INGREDIENTS_DECLARATION"].append({classify(val_ingre)[0]:val_ingre.strip()})
                else:
                    gen_category["INGREDIENTS_DECLARATION"] = [{classify(val_ingre)[0]:val_ingre.strip()}]
            elif "statement of ingredients" in table_data[index][0][0].replace('<b>','').replace('</b>','').lower().strip():
                is_ingredient_availble = True
#             else:
#                 for k1 in range(1,len(gen_cat1[0:])):
#                     unmap_val_head = gen_cat1[1:][0]
#     #                 if unmap_val_head not in ("Ingredients"):
#     #                     print(gen_cat1)
#                     if "UNMAPPED" in gen_category:
#                         gen_category["UNMAPPED"].append({classify(unmap_val_head)[0]:unmap_val_head})
#                     else:
#                         gen_category["UNMAPPED"]=[{classify(unmap_val_head)[0]:unmap_val_head}]
    return gen_category


# In[ ]:


def gen_content_data(table_data):
    gen_cont_claim = {}
    for cla_1 in table_data:
        if "supportable claims" in cla_1[0][0].lower().strip():
            for cla_2 in cla_1:
                key_val_claim = cla_2[0].lower().strip()
    #             print(key_val_claim)
                if "product" in key_val_claim:
                    for dr1 in range(1,len(cla_2)):
                        val_claim1_ltgt = cla_2[dr1]
                        val_claim1 = val_claim1_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                        if val_claim1 not in ("nan","None","0","[]",""):
                            if "CONTENT_CLAIM" in gen_cont_claim:
                                gen_cont_claim["CONTENT_CLAIM"].append({classify(val_claim1)[0]:val_claim1.strip()})
                            else:
                                gen_cont_claim["CONTENT_CLAIM"] = [{classify(val_claim1)[0]:val_claim1.strip()}]
                elif "claims:" in key_val_claim:
                    for dr2 in range(1,len(cla_2)):
                        val_claim2_ltgt = cla_2[dr2]
                        val_claim2 = val_claim2_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                        if val_claim2 not in ("nan","None","0","[]",""):
                            if "CONTENT_CLAIM" in gen_cont_claim:
                                gen_cont_claim["CONTENT_CLAIM"].append({classify(val_claim2)[0]:val_claim2.strip()})
                            else:
                                gen_cont_claim["CONTENT_CLAIM"] = [{classify(val_claim2)[0]:val_claim2.strip()}]
        elif "allergens present:" in cla_1[0][0].lower().strip():
            for cla_3 in cla_1:
                key_val_claim2 = cla_3[0].lower().strip()
        #             print(key_val_claim)
                if "product" in key_val_claim2:
                    for dr12 in range(1,len(cla_3)):
                        val_claim12_ltgt = cla_3[dr12]
                        val_claim12 = val_claim12_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                        if val_claim12 not in ("nan","None","0","[]",""):
                            if "CONTENT_CLAIM" in gen_cont_claim:
                                gen_cont_claim["CONTENT_CLAIM"].append({classify(val_claim12)[0]:val_claim12.strip()})
                            else:
                                gen_cont_claim["CONTENT_CLAIM"] = [{classify(val_claim12)[0]:val_claim12.strip()}]
                elif "claims:" in key_val_claim2:
                    for dr22 in range(1,len(cla_3)):
                        val_claim22_ltgt = cla_3[dr22]
                        val_claim22 = val_claim22_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                        if val_claim22 not in ("nan","None","0","[]",""):
                            if "CONTENT_CLAIM" in gen_cont_claim:
                                gen_cont_claim["CONTENT_CLAIM"].append({classify(val_claim22)[0]:val_claim22.strip()})
                            else:
                                gen_cont_claim["CONTENT_CLAIM"] = [{classify(val_claim22)[0]:val_claim22.strip()}]
        elif "nutrient & " in cla_1[0][0].lower().strip():
            for cla_3 in cla_1:
                for dr3 in range(1,len(cla_3)):
                    val_claim3_ltgt = cla_3[dr3]
                    val_claim3 = val_claim3_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                    if val_claim3 not in ("nan","None","0","[]",""):
                        if "CONTENT_CLAIM" in gen_cont_claim:
                            gen_cont_claim["CONTENT_CLAIM"].append({classify(val_claim3)[0]:val_claim3.strip()})
                        else:
                            gen_cont_claim["CONTENT_CLAIM"] = [{classify(val_claim3)[0]:val_claim3.strip()}]
        elif "product \nclaims:" in cla_1[0][0].lower().strip():
            for cla_4 in cla_1:
                for dr5 in range(1,len(cla_4)):
                    val_claim5_ltgt = cla_4[dr5]
                    val_claim5 = val_claim5_ltgt.replace('<', '&lt;').replace('>', '&gt;')
                    if val_claim5 not in ("nan","None","0","[]",""):
                        if "CONTENT_CLAIM" in gen_cont_claim:
                            gen_cont_claim["CONTENT_CLAIM"].append({classify(val_claim5)[0]:val_claim5.strip()})
                        else:
                            gen_cont_claim["CONTENT_CLAIM"] = [{classify(val_claim5)[0]:val_claim5.strip()}]

    return gen_cont_claim


# In[ ]:


def cook_in(table_data):
    storage_instruction_complete = {}
    for gen_cook in table_data:
        gen_c = gen_cook[0][0].replace(':','').replace('/','').replace('<b>','').replace('</b>','').lower().strip()
        if "cooking serving storage &amp; handling" in gen_c:# -->type1(cooking instruction and storage info merged)
            for k23 in gen_cook:
                cooking_instruction_value = k23[0:]
                if len(cooking_instruction_value)>1:
                    value_two_length = cooking_instruction_value[1:]
                    for kty in range(0,len(value_two_length)):
                        value_two_length1_in = value_two_length[kty]
                        value_two_length1 = value_two_length1_in.replace('<b>Instructions</b>','').replace('<b>Cooking Serving Storage &amp; Handling</b>', '').replace('<', '&lt;').replace('>', '&gt;')
                        if value_two_length1 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(value_two_length1).strip():
                            if "STORAGE_INSTRUCTIONS" in storage_instruction_complete:
                                storage_instruction_complete["STORAGE_INSTRUCTIONS"].append({classify(value_two_length1)[0]:value_two_length1.strip()})
                            else:
                                storage_instruction_complete["STORAGE_INSTRUCTIONS"]=[{classify(value_two_length1)[0]:value_two_length1.strip()}]
                elif len(cooking_instruction_value)>0:
                    value_one_length = cooking_instruction_value[0:]
                    for one_len in range(0,len(value_one_length)):
                        value_one_length1_in = value_one_length[one_len]
                        value_one_length1 = value_one_length1_in.replace('<b>Instructions</b>','').replace('<b>Cooking Serving Storage &amp; Handling</b>', '').replace('<', '&lt;').replace('>', '&gt;')
                        if value_one_length1 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(value_one_length1).strip():
                            if "STORAGE_INSTRUCTIONS" in storage_instruction_complete:
                                storage_instruction_complete["STORAGE_INSTRUCTIONS"].append({classify(value_one_length1)[0]:value_one_length1.strip()})
                            else:
                                storage_instruction_complete["STORAGE_INSTRUCTIONS"]=[{classify(value_one_length1)[0]:value_one_length1.strip()}]
        elif "storage instructions" in gen_c:# -->type1(cooking instruction and storage info merged)
            for stor_type2 in gen_cook:
                cooking_instruction_type = stor_type2[1:]
                for type2_loop in range(0,len(cooking_instruction_type)):
                    value_type2_loop_in = cooking_instruction_type[type2_loop]
                    value_type2_loop = value_type2_loop_in.replace('<b>Instructions</b>','').replace('<b>Cooking Serving Storage &amp; Handling</b>', '').replace('<', '&lt;').replace('>', '&gt;')
                    if value_type2_loop not in ("nan",None,"0","[]","N/A","","{}"," ") and str(value_type2_loop).strip():
                        if "STORAGE_INSTRUCTIONS" in storage_instruction_complete:
                            storage_instruction_complete["STORAGE_INSTRUCTIONS"].append({classify(value_type2_loop)[0]:value_type2_loop.strip()})
                        else:
                            storage_instruction_complete["STORAGE_INSTRUCTIONS"]=[{classify(value_type2_loop)[0]:value_type2_loop.strip()}]
    return storage_instruction_complete


# In[ ]:


def paragraph_content(soup):
    #working only marketing claim para(tag)
    mar_claim = []
    mar = []
    for mar_table in soup.find_all("table"):
        mar_table.decompose()
    for para in soup.find_all("p"):
        mar.append(para.text)
    mar_claim.append(mar)
    return mar_claim


# In[ ]:


def mark_para(mar_claim):
    cty_orgn = {}
    stor_inst = {}
    unmap = {}
    for org1 in mar_claim:
        for value_new1 in org1:
            if "*" and "adult" in value_new1:
                org2 = value_new1
                if value_new1 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "DECLARATION_CONTEXT_FOOTNOTE" in cty_orgn:
                        cty_orgn["DECLARATION_CONTEXT_FOOTNOTE"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["DECLARATION_CONTEXT_FOOTNOTE"]=[{classify(org2)[0]:org2.strip()}]
            elif "No Preservatives" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "CONTENT_CLAIM" in cty_orgn:
                        cty_orgn["CONTENT_CLAIM"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["CONTENT_CLAIM"]=[{classify(org2)[0]:org2.strip()}]
            elif "NZ" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "CONTENT_CLAIM" in cty_orgn:
                        cty_orgn["CONTENT_CLAIM"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["CONTENT_CLAIM"]=[{classify(org2)[0]:org2.strip()}]
            elif "frozenIndividually" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "CONTENT_CLAIM" in cty_orgn:
                        cty_orgn["CONTENT_CLAIM"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["CONTENT_CLAIM"]=[{classify(org2)[0]:org2.strip()}]
            elif "Good source of Folate" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "CONTENT_CLAIM" in cty_orgn:
                        cty_orgn["CONTENT_CLAIM"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["CONTENT_CLAIM"]=[{classify(org2)[0]:org2.strip()}]
            elif "Australia" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "LOCATION_OF_ORIGIN" in cty_orgn:
                        cty_orgn["LOCATION_OF_ORIGIN"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["LOCATION_OF_ORIGIN"]=[{classify(org2)[0]:org2.strip()}]
            elif "New Zealand" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "LOCATION_OF_ORIGIN" in cty_orgn:
                        cty_orgn["LOCATION_OF_ORIGIN"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["LOCATION_OF_ORIGIN"]=[{classify(org2)[0]:org2.strip()}]
            elif "Netherlands" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "LOCATION_OF_ORIGIN" in cty_orgn:
                        cty_orgn["LOCATION_OF_ORIGIN"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["LOCATION_OF_ORIGIN"]=[{classify(org2)[0]:org2.strip()}]
            elif "United Kingdom" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "LOCATION_OF_ORIGIN" in cty_orgn:
                        cty_orgn["LOCATION_OF_ORIGIN"].append({classify(org2)[0]:org2.strip()})
                    else:
                        cty_orgn["LOCATION_OF_ORIGIN"]=[{classify(org2)[0]:org2.strip()}]
            elif "uneaten" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "STORAGE_INSTRUCTIONS" in stor_inst:
                        stor_inst["STORAGE_INSTRUCTIONS"].append({classify(org2)[0]:org2.strip()})
                    else:
                        stor_inst["STORAGE_INSTRUCTIONS"]=[{classify(org2)[0]:org2.strip()}]
            elif "MICROWAVE" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "STORAGE_INSTRUCTIONS" in stor_inst:
                        stor_inst["STORAGE_INSTRUCTIONS"].append({classify(org2)[0]:org2.strip()})
                    else:
                        stor_inst["STORAGE_INSTRUCTIONS"]=[{classify(org2)[0]:org2.strip()}]
            elif "CHILDREN" in value_new1:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "STORAGE_INSTRUCTIONS" in stor_inst:
                        stor_inst["STORAGE_INSTRUCTIONS"].append({classify(org2)[0]:org2.strip()})
                    else:
                        stor_inst["STORAGE_INSTRUCTIONS"]=[{classify(org2)[0]:org2.strip()}]
            else:
                org2 = value_new1
                if org2 not in ("nan",None,"0","[]","N/A","","{}"," ") and str(org2).strip():
                    if "UNMAPPED" in unmap:
                        unmap["UNMAPPED"].append({classify(org2)[0]:org2.strip()})
                    else:
                        unmap["UNMAPPED"]=[{classify(org2)[0]:org2.strip()}]
    return {**stor_inst,**cty_orgn,**unmap}


# In[ ]:


def main_tab(file, converted_docx, pages):
    with pdfplumber.open(file) as pdf:
        if int(pages) <= len(pdf.pages):
            pd_doc = pdf_to_docx(file, converted_docx, pages)
            convertd = table_content(pd_doc)
            serv_nut = serv_nutr(convertd)
            unmap_inform = unmap_conte_nutri(convertd)
            gen_inform = gen_cat_data(convertd)
            content_claim = gen_content_data(convertd)
#             ingre_infor = gen_in(convertd)
            cook_infor = cook_in(convertd)
            #     print(type(gen_inform),type(serv_nut))
            general_main_dict = {}
            for diction in [serv_nut,unmap_inform,gen_inform,content_claim,cook_infor]:
                for keyy, valuee in diction.items():
                    if keyy in general_main_dict:
                        general_main_dict[keyy].extend(valuee)
                    else:
                        general_main_dict[keyy] = valuee
#             general_main_dict = {**serv_nut,**unmap_inform, **gen_inform, **content_claim,**cook_infor}
            cla = paragraph_content(pd_doc)
            unmap_cla = mark_para(cla)
            general_main_dict_final = {}
            for diction_final in [general_main_dict,unmap_cla]:
                for keyy_final, valuee_final in diction_final.items():
                    if keyy_final in general_main_dict_final:
                        general_main_dict_final[keyy_final].extend(valuee_final)
                    else:
                        general_main_dict_final[keyy_final] = valuee_final
#             final_data = general_main_dict_final}
            return general_main_dict_final
        else:
            return {}


# In[ ]:


def heinz_main(pdf_file,pages):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    converted_docx = f'{temp_directory.name}/converted.docx'
    pdf_file = get_input(pdf_file, input_pdf_location)
    t1 = time.time()
    final_dict = {}
    for page in pages.split(","):
        print(page)
        page_response = main_tab(pdf_file, converted_docx, int(page))
        final_dict[page] = page_response

    t2 = time.time()
    print(f'Complted in {t2 - t1} secs')
    return final_dict

