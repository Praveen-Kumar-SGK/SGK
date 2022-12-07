import io
import pdfplumber
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
from sklearn.metrics.pairwise import cosine_similarity
import pdfminer
from bs4 import BeautifulSoup
from textblob import TextBlob


from .excel_processing import *

# header_dict_value = {header: laser.embed_sentences(content,lang='en').mean(0).reshape(1,1024) for header, content in header_dict.items()}

class ferrero_extraction(base):
    def __init__(self):
        super().__init__()
        self.input_pdf_holder = None
        self.nutrition_table_title = ['Nutrition Information', 'nutrition declaration','Part D1 (LTR) - Nutrition Information','nutrition information typical values']
        self.output_io = io.StringIO()
        self.input_file = io.BytesIO()

    def get_pdf_file(self,file):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                self.input_file.write(f.read())
                self.input_file.seek(0)
                print('file found')
                # extract_text_to_fp(f,output_io,
                #                    laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                #                    output_type='html', codec=None)
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                self.input_file.write(f.read())
                self.input_file.seek(0)
                print('file found')
                # extract_text_to_fp(f,output_io,
                #                    laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                #                    output_type='html', codec=None)

        finally:
            smbclient.reset_connection_cache()
        return self.input_file

    def is_nutrition_table(self,text):  # 4
        if str(text).strip():
            similarity = cosine_similarity(laser.embed_sentences(text, lang='en'),
                                           laser.embed_sentences(self.nutrition_table_title, lang='en').mean(0).reshape(1,1024))[0][0]
        else:
            return False
        if similarity > 0.80:
            return True
        else:
            pass

    def header_similarity(self,text):
        embed_text = laser.embed_sentences([text], lang='en')
        similarity = lambda t: {key: cosine_similarity(value, t)[0][0] for key, value in header_dict_value.items()}
        score_dict = similarity(embed_text)
        max_cate = max(score_dict, key=score_dict.get)
        if score_dict and score_dict[max(score_dict, key=score_dict.get)] > 0.80:
            return max_cate
        else:
            return None

    def pdf_to_tables(self,input_pdf, page_no):  # pdfplumber 2
        if input_pdf.startswith('\\'):
            if not self.input_pdf_holder:
                if self.input_file.getvalue():
                    pdf = pdfplumber.open(self.input_file)
                    self.input_pdf_holder = pdf
                else:
                    pdf = pdfplumber.open(self.get_pdf_file(input_pdf))
            else:
                print('inside self.pdf')
                pdf = self.input_pdf_holder
        else:
            pdf = pdfplumber.open(input_pdf)
        page = pdf.pages[page_no - 1]
        tables = page.extract_tables()
        for table_no in range(len(tables)):
            # print(tables)
            # print('------'*10)
            yield tables[table_no]

    def attribute_checking(self,input_pdf, text):
        text_out = []
        if input_pdf.startswith('\\'):
            if not self.output_io.getvalue():
                extract_text_to_fp(self.input_file, self.output_io,laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                                       output_type='html', codec=None)
            else:
                pass
        else:
            if not self.output_io.getvalue():
                with open(input_pdf,'rb') as input:
                    extract_text_to_fp(input, self.output_io,
                                       laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                                       output_type='html', codec=None)
            else:
                pass
        html = BeautifulSoup(self.output_io.getvalue(), 'html.parser')
        results = html.find_all(
            lambda tag: tag.name == "div" and ' '.join(text.replace('\n', '').split()[:3]) in tag.text.replace('\n',''))
        # results = html.find_all(lambda tag:tag.name == "div" and text.lower() in tag.text.lower().replace('/n',''))  #if data processes via
        if results:
            if 'bold' in str(results[-1]).lower():
                for span in results[-1]:
                    if 'bold' in span['style'].lower():
                        text_out.append(f'<b>{span.text}</b>')
                    if 'bold' not in span['style'].lower():
                        text_out.append(span.text)
                # print(' '.join(text_out))
                return ' '.join(text_out)
            else:
                return None

    def table_non_table_extraction(self, input_pdf, page_no):  # start -1
        final = {}
        # for index, table in enumerate(get_tables(input_pdf, page_no=page_no)):
        for index, table in enumerate(self.pdf_to_tables(input_pdf, page_no=int(page_no))):
            nutrition_check_point = 0
            df = pd.DataFrame(table)
            rows, columns = df.shape
            if self.is_nutrition_table(re.sub(r'\<(.*?)\>', '', str(df[0][0]).replace('\n',' '))):
                # print(f'nutrition-------->{str(df[0][0])}')
                nutrition_check_point = 1
            if nutrition_check_point == 1:
                nutrition_data = {}
                nutrition_data_original = {}
                for column in range(columns)[:1]:
                    for row in range(rows):
                        if df[column][row]:
                            # key = nutrition_header_similarity(df[column][row])
                            nutrition_header = df[column][row]
                            nutrition_header_cleaned = nutrition_header.split('/')[0].strip()
                            key = base('ferrero_header',ferrero_header_model).prediction(nutrition_header_cleaned)['output']
                            if key in ['nutrition_table_reference']:
                                lang = classify(nutrition_header)[0]
                                final['nutrition_table_contents'] = [{lang:df[column][row]}]
                            elif key in ['header']:
                                for col_index in range(columns)[1:]:
                                    if df[col_index][row]:
                                        if df[col_index][row].strip() == 'Unit of Measure':
                                            for col_head in range(columns)[1:]:
                                                if df[col_head][row]:
                                                    print('headers---->', df[col_head][row].strip())
                                                    # if df[col_head][row].strip() not in ['N', 'GC', 'P', 'Y'] and df[col_head][row + 1]:
                                                    if df[col_head][row].strip():
                                                        if df[col_head][row].strip() == 'Unit of Measure':
                                                            if 'header' in nutrition_data:
                                                                nutrition_data['header'].append('Unit')
                                                            else:
                                                                nutrition_data['header'] = ['Unit']
                                                        elif '%' in df[col_head][row].strip():
                                                            if 'header' in nutrition_data:
                                                                nutrition_data['header'].append('PDV')
                                                            else:
                                                                nutrition_data['header'] = ['PDV']
                                                        else:
                                                            if 'header' in nutrition_data:
                                                                nutrition_data['header'].append('Value')
                                                            else:
                                                                nutrition_data['header'] = ['Value']
                            elif key not in ['None','nutrition_table_reference','header']:
                                print('nutrition_header_cleaned --->',nutrition_header_cleaned)
                                for col_index in range(columns)[1:]:
                                    if key in nutrition_data:
                                        if df[col_index][row] and df[col_index][row] not in ['N', 'GC', 'P', 'Y']:
                                            nutrition_data[key].append(df[col_index][row])
                                        elif df[col_index][row] == "":
                                            nutrition_data[key].append(df[col_index][row])
                                    else:
                                        if df[col_index][row] and df[col_index][row] not in ['N', 'GC', 'P', 'Y']:
                                            nutrition_data[key] = [df[col_index][row]]
                                        elif df[col_index][row] == "":
                                            nutrition_data[key] = [df[col_index][row]]
                                            # --------------------------------------------
                                    if nutrition_header_cleaned in nutrition_data_original:    # for exception  ---- nutrition_data_original
                                        if df[col_index][row] and df[col_index][row] not in ['N', 'GC', 'P', 'Y']:
                                            nutrition_data_original[nutrition_header_cleaned].append(df[col_index][row])
                                        elif df[col_index][row] == "":
                                            nutrition_data_original[nutrition_header_cleaned].append(df[col_index][row])
                                    else:
                                        if df[col_index][row] and df[col_index][row] not in ['N', 'GC', 'P', 'Y']:
                                            nutrition_data_original[nutrition_header_cleaned] = [df[col_index][row]]
                                        elif df[col_index][row] == "":
                                            nutrition_data_original[nutrition_header_cleaned] = [df[col_index][row]]
                                            # --------------------------------------------
                            else:
                                pass
                        else:
                            for col_index in range(columns)[1:]:
                                if df[col_index][row]:
                                    print('table title---->',df[col_index][row])
                                    if df[col_index][row].strip() == 'Unit of Measure':
                                        for col_head in range(columns)[1:]:
                                            if df[col_head][row]:
                                                print('headers---->', df[col_head][row].strip())
                                                # if df[col_head][row].strip() not in ['N', 'GC', 'P', 'Y'] and df[col_head][row+1]:
                                                if df[col_head][row].strip():
                                                    if df[col_head][row].strip() == 'Unit of Measure':
                                                        if 'header' in nutrition_data:
                                                            nutrition_data['header'].append('Unit')
                                                        else:
                                                            nutrition_data['header'] = ['Unit']
                                                    elif '%' in df[col_head][row].strip():
                                                        if 'header' in nutrition_data:
                                                            nutrition_data['header'].append('PDV')
                                                        else:
                                                            nutrition_data['header'] = ['PDV']
                                                    else:
                                                        if 'header' in nutrition_data:
                                                            nutrition_data['header'].append('Value')
                                                        else:
                                                            nutrition_data['header'] = ['Value']

                                        continue
                                    elif df[col_index][row].strip() == 'Nutritional Table Title:':
                                        if df[col_index+1][row]:
                                            lang = classify(df[col_index+1][row])[0]
                                            final['nutrition_table_title'] = [{lang:df[col_index+1][row]}]
                                            continue
                                    # elif df[col_index][row].strip() and df[col_index][row].strip() == 'Servings Per Package:':
                                    elif df[col_index][row].strip() == 'Servings Per Package:':
                                        print('inside serving per package-->',df[col_index + 1][row])
                                        if df[col_index+1][row]:
                                            lang = classify(df[col_index+1][row])[0]
                                            final['serving per package'] = [{lang:df[col_index+1][row]}]
                                        elif df[col_index+2][row]:
                                            lang = classify(df[col_index+2][row])[0]
                                            final['serving size'] = [{lang:df[col_index+2][row]}]
                                        continue
                                    # elif df[col_index][row].strip() and df[col_index][row].strip() == "Serving Size:":
                                    elif df[col_index][row].strip() == 'Serving Size:':
                                        print('inside serving size-->', df[col_index + 1][row])
                                        if df[col_index+1][row]:
                                            lang = classify(df[col_index+1][row])[0]
                                            final['serving size'] = [{lang:df[col_index+1][row]}]
                                        elif df[col_index+2][row]:
                                            lang = classify(df[col_index+2][row])[0]
                                            final['serving size'] = [{lang:df[col_index+2][row]}]
                                        continue
                                    else:
                                        pass
                final_nutrition = {}
                headings = None
                if nutrition_data['header']:
                    headings = nutrition_data['header']
                    print('headings--->',headings)
                    try:
                        nutrition_data.pop('header')
                    except:
                        pass
                print('nutrition_data---->', nutrition_data_original)
                try:
                    for nutritient, nutri_value in nutrition_data.items():
                        if nutritient != 'None':
                            for index, value in enumerate(nutri_value):
                                if value:
                                    if nutritient in final_nutrition:
                                        final_nutrition[nutritient].append({headings[index]: {'en': value}})
                                    else:
                                        final_nutrition[nutritient] = [{headings[index]: {'en': value}}]
                    final['Nutrition'] = final_nutrition
                except:
                    for nutritient, nutri_value in nutrition_data_original.items():
                        if nutritient != 'None':
                            for index, value in enumerate(nutri_value):
                                if value:
                                    if nutritient in final_nutrition:
                                        final_nutrition[nutritient].append({headings[index]: {'en': value}})
                                    else:
                                        final_nutrition[nutritient] = [{headings[index]: {'en': value}}]
                    final['Nutrition'] = final_nutrition
            else:
                for column in range(columns)[:1]:
                    for row in range(rows):
                        if df[column][row]:
                            text = re.sub(r'\((.*?)\)|\[.*?\]|\<(.*?)\>', '', df[column][row].replace('\n', '')).strip()
                            cate_out = base('ferrero_header',ferrero_header_model).prediction(text)
                            cate = cate_out['output']
                            cate_probability = cate_out['probability']
                            if cate not in ['None','header','distributor','manufacturer'] and cate_probability > 0.90:
                                for col_index in range(columns)[1:]:
                                    if df[col_index][row] and df[col_index][row] not in ['N', 'GC', 'P', 'Y']:
                                        cleaned_text = re.sub(r'\<(.*?)\>', '', str(df[col_index][row]))
                                        try:
                                            lang = TextBlob(cleaned_text).detect_language()
                                        except:
                                            lang = classify(cleaned_text)[0]
                                        text_with_attr = self.attribute_checking(input_pdf, cleaned_text)
                                        if text_with_attr:
                                            text_final = text_with_attr
                                        else:
                                            text_final = df[col_index][row]
                                        if cate in ['storage instruction', 'ingredients', 'marketing claim']:
                                            pred_out = base('general', model_location).prediction(cleaned_text)
                                            pred = pred_out['output']
                                            probability = pred_out['probability']
                                            if pred != cate:
                                                if probability > 0.80:
                                                    if pred in final:
                                                        final[cate].append({lang: text_final})
                                                    else:
                                                        final[cate] = [{lang: text_final}]
                                                else:
                                                    pass
                                        if cate in final:
                                            final[cate].append({lang: text_final})
                                        else:
                                            final[cate] = [{lang: text_final}]
                            else:
                                pass
        return final

    def main(self,files,pages):
        out_file = {}
        for file in [files]:
            out_pages = {}
            for page in pages.split(','):
                response = self.table_non_table_extraction(file,int(page))
                out_pages[page] = response
            # out_file[file] = out_pages
        try:
            self.input_file.close()
            self.output_io.close()
        except:
            pass
        return out_pages
