import mammoth
from bs4 import BeautifulSoup
import warnings
import tempfile


from .excel_processing import *

# conagra_model_location = r'/Users/sakthivel/Documents/SGK/Conagra/Conagra_model.sav'
classifier = joblib.load(conagra_model_location)

# document_location = r"/Users/sakthivel/Documents/SGK/Conagra/"

nutri_keys = ['Fat', 'Saturated Fat', 'Carbohydrate', 'Fibre', 'Sugar', 'Protein',
              'Cholesterol', 'Sodium', 'Potassium', 'Iron', 'Trans Fat', 'Calcium',
              'Vitamin A', 'Vitamin C']

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


# Cleaning and Classification
def cleaning_classifiction(key_id, classifier):
    temp = key_id.replace("&lt;b&gt;", '').replace("&lt;/b&gt;", '').replace("&lt;/b&gt;", '').replace('&lt;',
                                                                                                       '').replace(
        '&gt;', '').strip()
    # temp=re.sub('[\W_]+',' ',temp)
    prob = classifier.predict_proba(laser.embed_sentences(temp.strip(), lang='en'))[0]
    prob.sort()
    classified = str(classifier.predict(laser.embed_sentences(temp, lang='en'))[0])
    return temp, prob, classified

def general_info(path):
    html=mammoth.convert_to_html(path).value
    soup=BeautifulSoup(html,'html.parser')
    sep_text=str(soup).split('<table>')
    a='<table>'+sep_text[1]       
    for i in soup.find_all('table'):
        a=a.replace(str(i),'')
    
    a=a.replace('<ul>','<p>').replace('</ul>','</p>').replace('<ol>','<p>')\
        .replace('</ol>','</p>').replace('<li>','"break_line"').replace('</li>','')
    a=re.sub(r'<(?:a\b[^>]*>|/a>)','',a)
    general_soup=BeautifulSoup(a,'html.parser')
    aq1= str(general_soup).split('<p><strong>')
    
    keys=[]
    values=[]
    for i in aq1:
        temp=i.split('</strong>',1)
        try:
            if BeautifulSoup(str(temp[1]).replace('<p>',' '),'html.parser').text.strip():
                if BeautifulSoup(str(temp[0]),'html.parser').text.strip():
                    temp2=BeautifulSoup(str(temp[0]),'html.parser').text.strip().replace(':','')
                    keys.append(temp2)
                    values.append(BeautifulSoup(str(temp[1]).replace('<strong>',"&lt;b&gt;")\
                                                .replace('</strong>',"&lt;/b&gt;").replace('<p>','\n')\
                                                    .replace('</p>',''),'html.parser').text.strip())
                        
                elif temp[0].strip()=='' and temp[1].strip():
                    keys.append(temp2)
                    values.append(BeautifulSoup(temp[1].replace('<p>','\n').replace('</p>',''),'html.parser').text.strip())
                    
            elif ':' in i and i.endswith('</strong></p>'):                
                if i.split(":")[1].strip()!='</strong></p>':
                    keys.append(i.split(":")[0])
                    values.append("&lt;b&gt;"+BeautifulSoup(i.split(":")[1].replace('</strong></p>','')\
                                                            .replace('<p>','\n').replace('</p>',''),'html.parser')\
                                  .text.strip()+"&lt;/b&gt;")
                else:
                    # print('\n',i)
                    pass
        except:
            pass
            # print('\n',i)
    return keys,values,soup,sep_text[0]


def standard_keys_values(keys, values):
    values1 = []
    keys1 = []
    for i in range(len(values)):
        temp, prob, classified = cleaning_classifiction(keys[i], classifier)
        # print('\n',temp, prob[-1], classified)
        if '"break_line"' in values[i].replace('"break_line"', '', 1):
            temp = values[i].replace('"break_line"', '', 1).split('"break_line"')
            for j in temp:
                values1.append([{classify(j)[0]: j}])
                if prob[-1] > 0.85:
                    keys1.append(classified)
                else:
                    keys1.append('UNMAPPED')

        else:
            vt = re.sub(' +', ' ', values[i].replace('"break_line"', '').replace(':', '').strip())
            values1.append([{classify(vt)[0]: vt}])
            if prob[-1] > 0.85:
                keys1.append(classified)

            else:
                keys1.append('UNMAPPED')

    return keys1, values1


# In[46]:


def net_text(sep_text):
    acv = [BeautifulSoup(i, 'html.parser').text.strip() for i in
           sep_text.replace('</p>', '\n').replace('<p>', '').split('\n') if i.strip()]
    keys = []
    values = []
    for i in acv:
        if ':' in i:
            t = i.split(":")
            temp, prob, classified = cleaning_classifiction(t[0], classifier)
            values.append([{classify(t[1])[0]: t[1].strip()}])
            if prob[-1] > 0.65:
                # print({classified:{classify(t[1])[0]:t[1].strip()}})
                keys.append(classified)

            else:
                # print({'UNMAPPED':{classify(t[1])[0]:t[1].strip()}})
                keys.append('UNMAPPED')
        else:
            keys.append('UNMAPPED')
            values.append([{classify(i)[0]: i.strip()}])

    return keys, values

def mixed_ingre(gkeys, gvalues):
    keys1 = []
    values1 = []
    for i in range(len(gvalues)):
        val = list(gvalues[i][0].values())[0]
        if '<b>Contains' in val:
            # gvalues[i]=([{classify(val.split('<b>Contains')[0])[0]:val.split('<b>Contains')[0].strip()}])
            keys1.append(gkeys[i])
            values1.append([{classify(val.split('<b>Contains')[0])[0]: val.split('<b>Contains')[0].strip().replace(
                '<b>', "&lt;b&gt;").replace('</b>', "&lt;/b&gt;")}])
            keys1.append('ALLERGEN_STATEMENT')
            values1.append(
                [{classify(val.split('<b>Contains')[1])[0]: val.split('<b>Contains')[1].replace('</b>', '').strip()}])
        else:
            keys1.append(gkeys[i])
            values1.append([{classify(list(gvalues[i][0].values())[0])[0]: list(gvalues[i][0].values())[
                0].strip().replace('<b>', "&lt;b&gt;").replace('</b>', "&lt;/b&gt;")}])
    return keys1, values1


# Function to create dict with same key with multiple values in list
def multi_key_value(keys, values):
    file = {}
    for i in range(len(keys)):
        file.setdefault(keys[i], []).extend(values[i])
    return file

def nutri_extraction(soup):
    tab = []
    for table in soup.find_all('table'):
        rows = []
        for row in table.find_all('tr'):
            cells = []
            for cell in row.find_all('p'):
                if cell.text.strip():
                    cells.append(cell.text.strip())
            if cells:
                rows.append(cells)
        if rows:
            tab.append(rows)

    unit_nutri = []
    other_nutri = []
    if not bool(re.search(r'\d', tab[0][6][0])):
        unit_nutri = tab[0]
    else:
        other_nutri = tab[0]

    return unit_nutri, other_nutri

def unit_nutrition_table(unit_nutri):
    nkeys = []
    nvalues = []
    keys = []
    values = []

    for i in unit_nutri:
        temp, prob, classified = cleaning_classifiction(i[0].split('/')[0], classifier)
        if prob[-1] > 0.65 and classified in nutri_keys:
            nkeys.append(classified)
            sub_val = []
            for j in range(len(i)):

                if j > 0:
                    if i[j].strip() in ['g', 'mg', '%']:
                        sub_val.append({'Unit': {classify(i[j])[0]: i[j].strip()}})
                    else:
                        sub_val.append({'Value': {classify(i[j])[0]: i[j].strip()}})
                # else:
                #     sub_val.append({'copy_notes': {classify(i[j])[0]: i[j].strip()}})

            nvalues.append(sub_val)

        elif 'Calories' in i[0]:
            if '/' in i[0]:
                nkeys.append(i[0].split('/')[0].strip())
                # nvalues.append([{"copy_notes": {classify(i[0])[0]: i[0]}}, {"Value": {classify(i[1])[0]: i[1]}}])
                nvalues.append([{"Value": {classify(i[1])[0]: i[1]}}])


            else:
                nkeys.append(i[0].split()[0].strip())
                # nvalues.append([{"copy_notes": {classify(i[0].split()[0].strip())[0]: i[0].split()[0].strip()}},
                #                 {"Value": {classify(i[0].split()[1])[0]: i[0].split()[1]}}])
                nvalues.append([{"Value": {classify(i[0].split()[1])[0]: i[0].split()[1]}}])


        elif 'per' in i[0].lower() or 'pour' in i[0].lower():
            keys.append('SERVING_SIZE')
            values.append([{classify(i[0])[0]: i[0]}])

        elif i[0].startswith('*'):
            for h in i:
                keys.append('NUTRITION_TABLE_CONTENT')
                values.append([{classify(h)[0]: h}])

    nt = multi_key_value(nkeys, nvalues)
    return nt, keys, values


def conagra_main(path):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_docx_location = f'{temp_directory.name}/input_docx.docx'
    docx_file = get_input(path, input_docx_location)
    keys, values, soup, sep_text = general_info(docx_file)
    gen_keys, gen_values = standard_keys_values(keys, values)
    keys1, values1 = mixed_ingre(gen_keys, gen_values)
    unit_nutri, other_nutri = nutri_extraction(soup)
    nt, keys2, values2 = {}, [], []
    if unit_nutri:
        nt, keys2, values2 = unit_nutrition_table(unit_nutri)
    keys3, values3 = net_text(sep_text)
    fkeys = keys1 + keys2 + keys3
    fvalues = values1 + values2 + values3
    aw = multi_key_value(fkeys, fvalues)
    if nt:
        aw['NUTRITION_FACTS'] = [nt]
    return aw







