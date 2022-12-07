from bs4 import BeautifulSoup
import pdfplumber
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import io
import tempfile
from .excel_processing import *

# document_location = r"/Users/sakthivel/Documents/SGK/Pepsico/"

mlp_model = joblib.load(document_location+"pepsico_general_model.pkl")

classifier = joblib.load(document_location+"ferrero_header_model.pkl")

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


def General_Extraction(pdf_file, page_no):
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[int(page_no) - 1]
        #     for page in pdf.pages:

        extract_data = page.extract_text().split('\n')
        #     print(column_list_1)

        shelf_life_extract = []
        ingredient_extract = []
        marketing_claim_extract = []
        full_data_extract = []
        if 'ingredient legend' in ''.join(extract_data).lower():
            start = False
            for j in range(len(extract_data)):

                if "ingredient legend" in extract_data[j].lower().strip():
                    start = True
                if "nutrition information" in extract_data[j].lower().strip():
                    start = False
                if start:
                    if extract_data[j] == None:
                        continue
                    ingredient_extract.append(extract_data[j].strip())
                else:
                    full_data_extract.append(extract_data[j])

        elif 'manufacturing date' in ''.join(extract_data).lower() or 'main product claims' in ''.join(
                extract_data).lower():

            start = False
            start_1 = False
            for m in range(len(extract_data)):

                if "manufacturing date" in extract_data[m].lower().strip():
                    start = True
                if "product standard code" in extract_data[m].lower().strip():
                    start = False
                if "main product claims" in extract_data[m].lower().strip():
                    start_1 = True
                if "other information" in extract_data[m].lower().strip():
                    start_1 = False
                if start:
                    if extract_data[m] == None:
                        continue
                    shelf_life_extract.append(extract_data[m].strip())

                elif start_1:
                    if extract_data[m] == None:
                        continue
                    marketing_claim_extract.append(extract_data[m].strip())
                else:
                    full_data_extract.append(extract_data[m])
        else:
            full_data_extract.extend(extract_data)

        #         print("shelf",shelf_life_extract)

        #         print("marketing",marketing_claim_extract)
        #         print("\n\n")
        #         print(ingredient_extract)
        #         print("\n")
        #         print('full_data_extract',full_data_extract)

        return shelf_life_extract, marketing_claim_extract, ingredient_extract, full_data_extract


def functional_brand_name(full_data_extract):
    inner_dictionary_1 = {}
    balance_data_extract = []
    for i in range(0, len(full_data_extract)):
        edit_brand = str(full_data_extract[i]).replace("Formula/Ref. No：", "").strip().split("：")
        if "product name" in edit_brand[0].lower().strip():
            if "FUNCTIONAL_NAME" in inner_dictionary_1:
                inner_dictionary_1["FUNCTIONAL_NAME"].append({classify(edit_brand[1])[0]: str(edit_brand[1]).strip()})
            else:
                inner_dictionary_1["FUNCTIONAL_NAME"] = [{classify(edit_brand[1])[0]: str(edit_brand[1]).strip()}]


        elif "brand" in edit_brand[0].lower().strip():
            #             edit_brand[1]=edit_brand[1].replace("Formula/Ref. No：","").strip()
            if "BRAND_NAME" in inner_dictionary_1:

                inner_dictionary_1["BRAND_NAME"].append({classify(edit_brand[1])[0]: str(edit_brand[1]).strip()})
            else:
                inner_dictionary_1["BRAND_NAME"] = [{classify(edit_brand[1])[0]: str(edit_brand[1]).strip()}]
        else:
            balance_data_extract.append(full_data_extract[i])
    # print(inner_dictionary_1)
    return inner_dictionary_1, balance_data_extract


def general_dictionary_forming(shelf_claim_list):
    inner_dictionary_2 = {}
    ingre = []
    for i in range(1, len(shelf_claim_list)):
        shelf_claim_list[i] = shelf_claim_list[i].replace('\uf052', '').strip()

        if shelf_claim_list[i]:
            Xtest_laser = laser.embed_sentences(shelf_claim_list[i], lang='en')
            model_op = mlp_model.predict(Xtest_laser)
            classified_output = model_op[0]
            item_prob = mlp_model.predict_proba(Xtest_laser)
            item_prob[0].sort()
            prob = item_prob[0][-1]
            #         if prob>=0.95:
            #             print({shelf_claim_list[i]:str(prob)+"  "+classified_output})
            if classified_output in ("ACTIVE_INGREDIENTS_DECLARATION") and prob >= 0.92:
                ingre.append(shelf_claim_list[i].strip())
            elif classified_output in (
            "NUTRITIONAL_CLAIM", "SHELF_LIFE_STATEMENT", "ALLERGEN_STATEMENT", "LOT_NUMBER") and prob >= 0.95:
                if classified_output in inner_dictionary_2:
                    inner_dictionary_2[classified_output].append(
                        {classify(shelf_claim_list[i])[0]: str(shelf_claim_list[i]).strip()})
                else:
                    inner_dictionary_2[classified_output] = [
                        {classify(shelf_claim_list[i])[0]: str(shelf_claim_list[i]).strip()}]

            else:
                if prob > 0.75:
                    classified_output = "UNMAPPED"
                    if classified_output in inner_dictionary_2:
                        inner_dictionary_2[classified_output].append(
                            {classify(shelf_claim_list[i])[0]: str(shelf_claim_list[i]).strip()})
                    else:
                        inner_dictionary_2[classified_output] = [
                            {classify(shelf_claim_list[i])[0]: str(shelf_claim_list[i]).strip()}]

                        # print(ingre)
    joining_ingre = "".join(ingre).strip()
    if joining_ingre.strip():
        if "ACTIVE_INGREDIENTS_DECLARATION" in inner_dictionary_2:
            inner_dictionary_2["ACTIVE_INGREDIENTS_DECLARATION"].append(
                {classify(joining_ingre)[0]: str(joining_ingre).strip()})
        else:
            inner_dictionary_2["ACTIVE_INGREDIENTS_DECLARATION"] = [
                {classify(joining_ingre)[0]: str(joining_ingre).strip()}]

        #     print(inner_dictionary_2)
    return inner_dictionary_2


def Serving_size_dict(final_content):
    serv_dict = {}
    for b1 in final_content:
        if "每份食用量：" in b1:
            key_serv = "SERVING_SIZE"
            value_use_re = re.split('[-：]', b1)
            value_serv = value_use_re[1].strip()
            if key_serv in serv_dict:
                serv_dict[key_serv].append({classify(value_serv)[0]: value_serv})
            else:
                serv_dict[key_serv] = [{classify(value_serv)[0]: value_serv}]
    return serv_dict



def content_to_nutrition_table(df):
    nutrition_headers = []
    is_nutrition_table = False
    rows, columns = df.shape
    table = []
    for row in range(rows):
        row_values = " ".join(list(df.loc[row])).split()
        if "项目" in row_values:
            nutrition_headers.append(row_values)
            # print("NUtrition_headers---->",self.nutrition_headers)
            is_nutrition_table = True
        elif is_nutrition_table:
            table_content = " ".join(list(df.loc[row])).split("\n")
            for nutrition_row in table_content:
                table.append(nutrition_row.split())
    return pd.DataFrame(table)

def Extraction_Nutri(pdf_file, page_no):
    file_open = []
    fop_file = []
    with pdfplumber.open(pdf_file) as pdf:
        page = pdf.pages[int(page_no) - 1]
        pg_text = page.extract_tables()
        for k1 in pg_text:
            #             print(k1, len(k1))
            #             print("*****" *4)
            if len(k1) == 2:
                k1_dat = pd.DataFrame(k1)
                k1_dat1 = (content_to_nutrition_table(k1_dat)).values.tolist()
                file_open.append(k1_dat1)
            if len(k1) == 4:
                df = pd.DataFrame(k1)
                ky = df.T
                conlist = ky.values.tolist()
                fop_file.append(conlist)
    return file_open, fop_file



def nutri_to_json_file_open(file_open):
    nut_extract = {}
    for li in file_open:
        nut_extr = {}
        for lis1 in li:
            key = lis1[0]
            nutri_tab = classifier.predict_proba(laser.embed_sentences(key, lang="en"))[0]
            nutri_tab.sort()
            classified_tab = classifier.predict(laser.embed_sentences(key, lang="en"))[0]
            if nutri_tab[-1] > 0.65:
                classified_key = classified_tab
            else:
                classified_key = "UNMAPPED"
            for lis2 in range(1, len(lis1)):
                value = str(lis1[lis2])
                if value != "None":
                    if "％" in value:
                        value_header = "PDV"
                    else:
                        value_header = "Value"
                    if classified_key in nut_extr:
                        nut_extr[classified_key].append({value_header: {classify(value)[0]: value}})
                    else:
                        nut_extr[classified_key] = [{value_header: {classify(value)[0]: value}}]
        if nut_extr:
            if "NUTRITION_FACTS" in nut_extract:
                nut_extract["NUTRITION_FACTS"].append(nut_extr)
            else:
                nut_extract["NUTRITION_FACTS"] = [nut_extr]
    return nut_extract


def nutri_to_json_file_fop(fop_file):
    fop_dict = {}
    for d1 in fop_file:
        if len(d1) > 2 and "净含量" in d1[0]:
            for d2 in d1:
                for d3 in d2:
                    key_fop = "OTHER_INSTRUCTIONS"
                    value_fop = str(d3)
                    if value_fop != 'None':
                        if key_fop in fop_dict:
                            fop_dict[key_fop].append({classify(value_fop)[0]: value_fop})
                        else:
                            fop_dict[key_fop] = [{classify(value_fop)[0]: value_fop}]
    return fop_dict


def Nutri_function_call(pdf_file, page_no):
    file_open, fop_file = Extraction_Nutri(pdf_file, page_no)
    Nutri_table = nutri_to_json_file_open(file_open)
    return Nutri_table



def general_function_call(pdf_file, page_no):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    pdf_file = get_input(pdf_file, input_pdf_location)
    with pdfplumber.open(pdf_file) as pdf:
        if int(page_no) <= len(pdf.pages):
            shelf_life_extract, marketing_claim_extract, ingredient_extract, full_data_extract = General_Extraction(pdf_file,
                                                                                                                    page_no)
            inner_dictionary_1, balance_data_extract = functional_brand_name(full_data_extract)
            #     print(full_data_extract)
            general_1 = general_dictionary_forming(shelf_life_extract)
            general_2 = general_dictionary_forming(marketing_claim_extract)
            general_3 = general_dictionary_forming(ingredient_extract)
            general_4 = general_dictionary_forming(balance_data_extract)
            serv_dict = Serving_size_dict(full_data_extract)
            file_open, fop_file = Extraction_Nutri(pdf_file, page_no)
            fop_dict = nutri_to_json_file_fop(fop_file)
            general_main_dict = {**inner_dictionary_1, **general_1, **general_2, **general_3, **general_4, **serv_dict,
                                 **fop_dict}
            Nutri_table = Nutri_function_call(pdf_file, page_no)
            final_dict = {**general_main_dict, **Nutri_table}
            return final_dict
        else:
            return {}

def pepsico_pdf_main(pdf_file, page_nos):
    page_dict = {}
    for page_no in page_nos.split(','):
        final_response = general_function_call(pdf_file, int(page_no))
        page_dict[page_no] = final_response
    return page_dict






