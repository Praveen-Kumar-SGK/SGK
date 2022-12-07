# -------------------------------------------- Pladis -----------------------------------------------#

# Packages used
import io
import tabula
import pdfplumber
from fuzzywuzzy import fuzz
from bs4 import BeautifulSoup
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
import tempfile

from .excel_processing import *

# --------------------------------------------------------------------------------
# Laser Embedding
# path_to_bpe_codes = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/93langs.fcodes'
# path_to_bpe_vocab = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/93langs.fvocab'
# path_to_encoder = r'/opt/anaconda3/lib/python3.8/site-packages/laserembeddings/data/bilstm.93langs.2018-12-26.pt'
# laser = Laser(path_to_bpe_codes, path_to_bpe_vocab, path_to_encoder)

# --------------------------------------------------------------------------------
# Loading MLP Classifier for classification keys
# classifier = joblib.load(r'/Users/praveen/Documents/Study/Projects/Pladis/Pladis.sav')
classifier = joblib.load(pladis_model)

# --------------------------------------------------------------------------------
# Data Extraction

def data_extraction(path, sheet_number):
    data = pdfplumber.open(path).pages[sheet_number].extract_text()
    # Removing extra spaces using regex and splitting linewise
    data_cleaned = re.sub(' +', ' ', data).strip().split('\n')
    data_cleaned = [i for i in data_cleaned if i.strip()]
    for i in range(len(data_cleaned)):
        # Allergen statement misalignment
        if 'May Contain' in data_cleaned[i]:
            data_cleaned[i] = 'May Contain Statement:' + data_cleaned[i].replace('May Contain ', '').replace(
                'Statement:', '')
        elif data_cleaned[i].startswith('Statement:'):
            data_cleaned[i] = data_cleaned[i].replace('Statement:', '')
        # Nutritional Claim
        elif data_cleaned[i].startswith('Energy per'):
            data_cleaned[i] = 'FOP Nutrition Icons:' + data_cleaned[i]
    return data_cleaned


# --------------------------------------------------------------------------------
# Merging the multiple values in new lines

def merging_values(data):
    remove1 = []
    remove2 = []
    temp_id = 0
    end = 0
    for i in range(len(data)):
        # Stopping the data at nutrition table
        if data[i].strip() == 'Nutrition Information':
            end = i
            # End of the data needed and capturing the indices to be removed
            remove2 = [j for j in range(end, len(data))]
            break
        elif ':' in data[i]:
            temp_id = i
        else:
            # Adding multiple values to the keys which came last
            data[temp_id] = data[temp_id].strip() + '\n' + data[i].strip()
            # Now removing the multiple value after it got merged
            remove1.append(i)
    # Removing all the unwanted data
    Remove = remove1 + remove2
    for i in Remove:
        if ':' in data[i]:
            Remove.remove(i)
    for i in sorted(Remove, reverse=True):
        del data[i]
    return data


# --------------------------------------------------------------------------------
# To remove unwanted FOP Icon table

def fop_cleaning(data):
    st_id = 0
    ed_id = 0
    for i in range(len(data)):
        if 'FOP' in data[i] and '\n' in data[i]:
            temp = data[i].split('\n')
            for j in range(len(temp)):
                if 'Energy' in temp[j]:  # Starting from  energy value
                    st_id = j
                elif 'of' in temp[j]:
                    ed_id = j  # Last element
            unwanted = ('\n'.join(temp[st_id:ed_id])).strip()
            data[i] = data[i].replace(unwanted, '').strip()
            break
    return data


# --------------------------------------------------------------------------------
# Special Case files
# 70161 Meredith & Drew Oaty Flapjack (single) pc 21 01 2022.pdf
# 99137 Jacob's Mini Cheddars - Cheese Pizza Flavour Sharing Pack 45g, 90g pc 28 01 2022.pdf

def special_case(data):
    for i in range(len(data)):
        temp = data[i].split(':', 1)[0]
        temp = re.sub(r"[\([{})\]]", "", temp).strip()
        if temp in ['EN single', 'Case', 'Sharing pack']:
            data[i] = data[i - 1].split(':', 1)[0] + ':' + data[i]

    return data


# --------------------------------------------------------------------------------
def mixed_values(keys, values):
    for i in range(len(keys)):
        if keys[i] == 'INGREDIENTS_DECLARATION':
            temp = list(values[i][0].values())[0].split('\n')
            if temp[-1].startswith('For allergens'):
                values[i] = ([{classify(''.join(temp[:-1]))[0]: ''.join(temp[:-1])}])
                allergen_val = [{classify(temp[-1])[0]: temp[-1]}]
                # print(igre,aller)
                for j in range(len(keys)):
                    if keys[j] == 'ALLERGEN_STATEMENT':
                        mark_val2 = (list(values[j][0].values())[0])
                        aller_id = j
                    elif keys[j] == 'MARKETING_CLAIM':
                        mark_val1 = (list(values[j][0].values())[0])
                        mark_id = j

                values[aller_id] = allergen_val
                mark_val = mark_val1 + '\n' + mark_val2
                values[mark_id] = [{classify(mark_val)[0]: mark_val}]
    return values


# --------------------------------------------------------------------------------
# Cleaning and Classification
def cleaning_classifiction(key_id):
    temp = key_id.replace("&lt;b&gt;", '').replace("&lt;/b&gt;", '').replace("&lt;/b&gt;", '').replace('&lt;',
                                                                                                       '').replace(
        '&gt;', '').strip()
    temp = re.sub('[\W_]+', ' ', temp)
    prob = classifier.predict_proba(laser.embed_sentences(temp.strip(), lang='en'))[0]
    prob.sort()
    classified = str(classifier.predict(laser.embed_sentences(temp, lang='en'))[0])
    return temp, prob, classified


# --------------------------------------------------------------------------------
def keys_values(data):
    keys = []
    values = []
    for i in data:
        if ':' in i and 'FOP Nutrition Icons' in i:
            if '\n' in i.split(':', 1)[1].strip():
                fv = ([i.strip() for i in i.split(':', 1)[1].strip().split('\n') if i.strip()])
                for j in fv:
                    values.append([{classify(j)[0]: j.replace('<', '&lt;').replace('>', '&gt;')}])
                    keys.append('NUTRITIONAL_CLAIM')  # i.split(':',1)[0].strip())
            else:
                values.append([{classify(i.split(':', 1)[1].strip())[0]: i.split(':', 1)[1].strip().replace('<',
                                                                                                            '&lt;').replace(
                    '>', '&gt;')}])
                keys.append('NUTRITIONAL_CLAIM')  # i.split(':',1)[0].strip())
        elif ':' in i and i.split(':', 1)[1].strip() != '':
            values.append([{classify(i.split(':', 1)[1].strip())[0]: i.split(':', 1)[1].strip().replace('<',
                                                                                                        '&lt;').replace(
                '>', '&gt;')}])
            temp, prob, classified = cleaning_classifiction(i.split(':', 1)[0].strip())
            if prob[-1] > 0.65:
                keys.append(classified)
            else:
                keys.append('UNMAPPED')
    return keys, values


# --------------------------------------------------------------------------------
# Table Data Function
def tabular_data(path, sheet_number):
    b = tabula.read_pdf(path, pages=sheet_number, lattice=True)
    keys = []
    values = []
    nut_list1 = []
    nut_list2 = []
    nut_list3 = []
    for i in b:
        table = (i.dropna(how='all', axis=1)).T.reset_index().T
        if table.shape[0] > 1 and table.shape[1] > 1:
            # Nutrition Table in Page 1
            if str(table.iloc[0, 0]) == 'Nutrition Information':
                nut_list1 = (i.dropna(how='all', axis=1)).iloc[1:, ].values.tolist()
            # Nutrition Table in Page 2
            elif str(table.iloc[0, 0]) == 'Average Values':
                nut_list2 = (i.dropna(how='all', axis=1)).values.tolist()
            # FOP Table
            elif str(table.iloc[0, 0]) == 'Energy':
                nut_list3 = (i.dropna(how='all', axis=1)).T.reset_index().values.tolist()
            # Special Case 70161 Meredith & Drew Oaty Flapjack (single) pc 21 01 2022.pdf
            elif str(table.iloc[0, 0]).startswith('Number of flapjacks'):
                pass  # print('Special Case')
            elif table.iloc[1, 0] == table.iloc[2, 0]:
                aq = table.drop_duplicates()
                if aq.iloc[1, 0] == aq.iloc[2, 0]:
                    temp = (aq.iloc[2:, :].T.values.tolist())
                for i in temp:
                    sub_val = []
                    for j in range(len(i)):
                        if j == 0:
                            temp, prob, classified = cleaning_classifiction(i[j])
                            if prob[-1] > 0.65:
                                keys.append(classified)
                            else:
                                keys.append('UNMAPPED')
                        else:
                            sub_val.append(
                                {classify(str(i[j]))[0]: str(i[j]).replace('<', '&lt;').replace('>', '&gt;')})
                        if len(sub_val) == len(i) - 1:
                            values.append(sub_val)
            else:
                temp = table.T.values.tolist()
                for i in temp:
                    sub_val = []
                    for j in range(len(i)):
                        if j == 0:
                            temp, prob, classified = cleaning_classifiction(i[j])
                            if prob[-1] > 0.65:
                                keys.append(classified)
                            else:
                                keys.append("UNMAPPED")
                        else:
                            sub_val.append(
                                {classify(str(i[j]))[0]: str(i[j]).replace('<', '&lt;').replace('>', '&gt;')})
                        if len(sub_val) == len(i) - 1:
                            values.append(sub_val)
    nut_list = nut_list1 + nut_list2 + nut_list3
    return nut_list, keys, values


# --------------------------------------------------------------------------------
# Bold Attributes
def get_contents_with_attributes(path):
    output_io = io.StringIO()
    with open(path, 'rb') as input:
        extract_text_to_fp(input, output_io,
                           laparams=LAParams(line_margin=0.21, line_overlap=0.4, all_texts=False),
                           output_type='html', codec=None)
    html = BeautifulSoup(output_io.getvalue(), 'html.parser')
    final_content = []
    for div in html.find_all("div"):
        temp_div = []
        for span in div.find_all("span"):
            if 'bold' in span['style'].lower():
                if span.text.strip():
                    temp_div.append(f'<b>{span.text.strip()}</b>')
            if 'bold' not in span['style'].lower():
                if span.text.strip():
                    temp_div.append(span.text.strip())
        if temp_div:
            final_content.append(" ".join(temp_div))
    output_io.close()
    return final_content


# --------------------------------------------------------------------------------
# Nutrition Table Function
def nutri_table(data):
    nutri_keys = []
    nutri_values = []
    for i in data:
        sub_nutri = []
        temp = str(i[0]).replace('of which', '').replace('(kJ)', '').replace('(kcal)', 'Energy').strip()
        op = str(classifier.predict([laser.embed_sentences(temp, lang='en')[0]])[0])
        pb = classifier.predict_proba([laser.embed_sentences(temp, lang='en')[0]])[0]
        pb.sort()
        clean_list = [j for j in i if str(j) != 'nan' and str(j).split()[0] != 'Per']
        if pb[-1] > 0.65:
            for val in range(0, len(clean_list)):
                if val > 0:
                    if "%" in clean_list[val]:
                        sub_nutri.append({'PDV': {
                            "en": clean_list[val].replace('\r', ' ').replace('<', '&lt;').replace('>', '&gt;').replace(
                                '  ', '\n')}})
                    else:
                        sub_nutri.append({'Value': {
                            "en": clean_list[val].replace('\r', ' ').replace('<', '&lt;').replace('>', '&gt;').replace(
                                '  ', '\n')}})
                else:
                    nutri_keys.append(op)

                if len(sub_nutri) == (len(clean_list) - 1):  # Adding to main values list only if all
                    nutri_values.append(sub_nutri)  # elements of individual row is completed
    Nutrition = {}
    for i in range(len(nutri_keys)):
        Nutrition.setdefault(nutri_keys[i], []).extend(nutri_values[i])
    return Nutrition


# --------------------------------------------------------------------------------
def bold_convertion(path, keys, values, sheet_number):
    l = get_contents_with_attributes(path)
    bold = []
    for i in range(len(keys)):
        if keys[i] == 'INGREDIENTS_DECLARATION':
            bold.append(i)

    for j in bold:
        for i in l:
            cleaned_text = re.sub('\<.*?\>', '', i)
            cleaned_text = re.sub(' +', ' ', cleaned_text)
            score = fuzz.ratio(list(values[j][0].values())[0], cleaned_text)
            if score > 90:
                org = i.replace('<b>', '&lt;b&gt;').replace('</b>', '&lt;/b&gt;')
                org = re.sub('\<.*?\>', '', org)
                values[j] = [{classify(org)[0]: org}]
    return values

def get_input(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
            return input_pdf_location
            # return self.input_pdf_location
    else:
        return document_location+input_pdf

# --------------------------------------------------------------------------------
def main(path,pages):
    # page_number = list((map(int, input("Enter Pages(leaving space): ").split())))  # Multiple pages input
    temp_dir = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf = f'{temp_dir.name}/input_pdf.pdf'
    path = get_input(path,input_pdf)
    page_number = [int(x) - 1 for x in pages.split(",")]
    page_wise = []
    for sheet_number in page_number:
        if sheet_number in range(len((pdfplumber.open(path)).pages)):
            data = data_extraction(path, sheet_number)
            data = merging_values(data)
            data = fop_cleaning(data)
            data = special_case(data)
            keys1, values1 = keys_values(data)
            nut_list1, keys2, values2 = tabular_data(path, sheet_number + 1)
            nutri = nutri_table(nut_list1)
            remove = []
            for i in range(len(keys1)):
                if keys1[i] == 'NUMBER_OF_SERVINGS_PER_PACKAGE' and 'NUMBER_OF_SERVINGS_PER_PACKAGE' in keys2:
                    remove.append(i)
            for i in sorted(remove, reverse=True):
                del keys1[i], values1[i]
            keys = keys1 + keys2
            values = values1 + values2
            values = mixed_values(keys, values)
            values = bold_convertion(path, keys, values, sheet_number)
            file = {}
            for i in range(len(keys)):
                file.setdefault(keys[i], []).extend(values[i])
            if nutri:
                file['NUTRITION_FACTS'] = [nutri]
            page_wise.append({sheet_number + 1: file})

        else:
            page_wise.append({sheet_number + 1: {}})
    all_pages = {}
    for i in page_wise:
        for k, v in i.items():
            all_pages[k] = v

    # output = {path: all_pages}
    temp_dir.cleanup()
    return all_pages

