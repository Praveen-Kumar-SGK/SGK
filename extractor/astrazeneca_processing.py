import mammoth
from bs4 import BeautifulSoup
from textblob import TextBlob
from .excel_processing import *
import copy

class az_extraction(base):
    def __init__(self):
        super().__init__()
        self.file_name = None
        # self.regex_heading_msd = r"^\d+\.\d?[\-\s][^%]|\<li\>"   # old
        self.regex_heading_msd = r"^\d+\.\d?[\-\s][^%ml]|\<li\>"
        self.validation_categories = {
                                      'warning':['warning'],
                                      'storage_instructions':['storage_instructions'],
                                      'manufacturer':['address','manufacturer'],
                                      'marketing_company': ['address','marketing_company'],
                                      'expiry_date':['expiry_date'],
                                      'form_content':['form_content'],
                                      'method_route':['method_route'],
                                      'others':['others'],
                                      'None':['None'],
                                      # 'excipients': ['excipients'],
                                      }

    def docx_to_html(self,file,method=None):
        print('entering docx to html')
        if file.startswith('\\'):
            print('connecting to SMB share')
            try:
                with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    html = mammoth.convert_to_html(f).value
                    print('file found')
            except:
                smbclient.reset_connection_cache()
                with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    html = mammoth.convert_to_html(f).value
                    print('file found')
            finally:
                smbclient.reset_connection_cache()
        else:
            print('local')
            file = document_location + file
            html = mammoth.convert_to_html(file).value
        return html

    def html_txt_bl_extraction(self,html_content):
        raw_html = str(html_content).replace('<strong>', 'start_bold').replace('</strong>', 'end_bold').replace('</p>',
                                                                                                                '\n').strip()
        cleantext = BeautifulSoup(raw_html, "lxml").text
        cleantext = cleantext.replace('start_bold', '<b>').replace('end_bold', '</b>')
        return cleantext

    def text_from_html_revised(self,file_name):
        print("newly created home")
        html = self.docx_to_html(file_name)
        soup = BeautifulSoup(html, 'html.parser')
        # print("soup---------->",soup)
        paragraphs = soup.find_all(['p', 'li', 'a'])
        print("length of paragraphs----->",len(paragraphs))
        index_start_dict = {}
        index_stop_dict = {}
        para_id_value_list = [pa.get('id') for pa in paragraphs]
        if len(para_id_value_list) > 0:
            print("finding index based on id value")
            # print("yyyyy------>",para_id_value_list)
            for index , para_id in enumerate(para_id_value_list):
                if para_id and re.search(r"^A\..*$",para_id):
                # if para_id and re.search(r"III",para_id):
                    index_start_dict[index] = para_id
                    print("index_id_start------>",para_id)
                    continue
                if para_id and re.search(r"^B\..*$",para_id):
                    index_stop_dict[index] = para_id
                    print("index_id_stop------>", para_id)
        if not index_start_dict and not index_stop_dict:
            print("finding index based in para")
            para_value_list = [self.html_txt_bl_extraction(pa) for pa in paragraphs]
            # print("hhhhh------>",para_value_list)
            if len(para_value_list) > 0:
                for index, para in enumerate(para_value_list):
                    if para and para.strip() and re.search(r"^A\..*$", para):
                        print("index__start------>", para)
                        index_start_dict[index] = para
                        continue
                    if para and para.strip() and re.search(r"^B\..*$", para):
                        print("index_stop------>", para)
                        index_stop_dict[index] = para
        print("vaaareee vaaaa------->",index_start_dict)
        print("pooooreeee poooooo------->",index_stop_dict)
        if index_start_dict and index_stop_dict:
            if max(index_stop_dict) > max(index_start_dict):
                paragraphs = paragraphs[max(index_start_dict)+2:max(index_stop_dict)]
            else:
                print("taking minimum index")
                paragraphs = paragraphs[min(index_start_dict)+2:max(index_stop_dict)]
        else:
            raise Exception("start and stop index not found")
        print("length of paragraphs2----->", len(paragraphs))
        for para in paragraphs:
            yield para

    # def text_from_html(self,file_name):
    #     html = self.docx_to_html(file_name)
    #     soup = BeautifulSoup(html, 'html.parser')
    #     print("soup---------->",soup)
    #     indx_start = 0
    #     indx_end = 0
    #     start , end = None, None
    #     paragraphs = soup.find_all(['p', 'li', 'a'])
    #     para_dummy = [self.html_txt_bl_extraction(pa) for pa in paragraphs]
    #     para_dummy_id = [pa.get('id') for pa in paragraphs]
    #     para_dummy_id_final = [pa.get('id') for pa in paragraphs if pa.get('id') and re.search(r"^A\..*$",str(pa.get("id")))]
    #     print("vaaaaa machan----->",para_dummy)
    #     print("poooooo machan----->",para_dummy_id)
    #     print("poooooo machan final----->",para_dummy_id_final)
    #     for para in paragraphs:
    #         indx_start += 1
    #         indx_end += 1
    #         cleantext = self.html_txt_bl_extraction(para)  # Select everything after and before labelling and package leaflet
    #         if range(len(cleantext) > 0):
    #             # if re.findall("^A\.\s+LABELLING$", cleantext):
    #             if re.findall("^A\..*$", cleantext):
    #                 print('start--->',cleantext)
    #                 start = indx_start
    #             # if re.findall("^B\.\s+PACKAGE\s+LEAFLET$", cleantext):
    #             if re.findall("^B\..*$", cleantext):
    #                 print('end--->', cleantext)
    #                 end = indx_end
    #                 break
    #
    #     indx_fin = 0
    #     skipped_list = []
    #     skipped_next_list = []
    #     skipped_values = []
    #     for para_fin in paragraphs:
    #         indx_fin += 1
    #         particulars_index = self.html_txt_bl_extraction(para_fin)  # Getting minimum particulars index and followed by 1
    #         if (len(particulars_index) > 0):
    #             print(start,end)
    #             if (indx_fin > start and indx_fin < end):
    #                 if re.findall('PARTICULARS TO APPEAR', particulars_index):
    #                     skipped_list.append(indx_fin)
    #                     skipped_next_list.append(indx_fin + 1)
    #                     skipped_values.append([j for i in zip(skipped_list, skipped_next_list) for j in i])
    #
    #     skipped_values = [j for i in zip(skipped_list, skipped_next_list) for j in i]
    #     indx_fin = 0
    #     toskip = []
    #     for para_fin in paragraphs:
    #         indx_fin += 1
    #         particulars_text = self.html_txt_bl_extraction(
    #             para_fin)  # Getting minimum particulars string from previous index
    #         if (indx_fin in [i for i in skipped_values]):
    #             toskip.append(particulars_text)
    #
    #     skipped_string = "".join(toskip)  # Converting the match to a string
    #
    #     indx_fin = 0
    #     for para_fin in paragraphs:
    #         indx_fin += 1
    #         filtered_text = self.html_txt_bl_extraction(
    #             para_fin)  # Getting refined data by exluding minmum particulars paragraph and follo up index / product name
    #         if (len(filtered_text) > 0):
    #             if (indx_fin > start and indx_fin < end):
    #                 if (filtered_text in skipped_string):
    #                     continue
    #                 yield para_fin

    def text_from_html2(self,file_name):             # only for MSD
        print('entering text to _html')
        html = self.docx_to_html(file_name)
        soup = BeautifulSoup(html, 'html.parser')# for heading - value structure
        paragraphs = soup.find_all(['p', 'li'])
        for para in paragraphs:
            print('para------>',para)
            yield para

    # def heading_value_extraction(self,file_name):                       # only for MSD
    #     tmp = []
    #     final = {}
    #     key = ''
    #     try:
    #         # generator = self.text_from_html(file_name)
    #         generator = self.text_from_html_revised(file_name)
    #         print("first one is active")
    #     except:
    #         generator = self.text_from_html2(file_name)
    #         print("second one is active")
    #     paragraphs = [component for component in generator]
    #     for i, content in enumerate(paragraphs):
    #         text = str(content)
    #         if '' in tmp:
    #             tmp.remove('')
    #         if re.findall(self.regex_heading_msd, content.text.strip()) or '<li>' in text:
    #         # if re.findall(self.regex_heading_msd, text):
    #             print(f'heading------->{text}')
    #             try:
    #                 if key and (key not in final):
    #                     if tmp:
    #                         # final[key] = ['$$'.join(tmp)]
    #                         yield key , ['$$'.join(tmp)]
    #                 elif key in final:
    #                     if tmp:
    #                         # final[key].append('$$'.join(tmp))
    #                         yield key ,['$$'.join(tmp)]
    #                 key = re.sub(r'<.*?>', '', text)
    #                 # print(key)
    #                 tmp.clear()
    #             except:
    #                 pass
    #         else:
    #             if i == len(paragraphs) - 1:
    #                 text = text.strip()
    #                 tmp = [t for t in tmp if t]
    #                 if text and not re.findall(r"Panel\s\d", text):
    #                     text = text.replace('<strong>', '<b>').replace('</strong>', '</b>')
    #                     text = re.sub(r"<(\/?[^/bems]).*?>", '', text)
    #                     tmp.append(text)
    #                 if key not in final:
    #                     if tmp:
    #                         # final[key] = ['$$'.join(tmp)]
    #                         yield key, ['$$'.join(tmp)]
    #                 elif key in final:
    #                     if tmp:
    #                         # final[key].append('$$'.join(tmp))
    #                         yield key, ['$$'.join(tmp)]
    #                 else:
    #                     print('temp__-------append-------->', text)
    #                     pass
    #             else:
    #                 text = text.strip()
    #                 tmp = [t for t in tmp if t]
    #                 if text and not re.findall(r"Panel\s\d", text):  # filter out heading like 'big panel 1'
    #                     text = text.replace('<strong>', '<b>').replace('</strong>', '</b>')
    #                     text = re.sub(r"<(\/?[^/bems]).*?>", '', text)
    #                     tmp.append(text)

    def heading_value_extraction2(self,file_name):
        heading_concat = []
        tmp = []
        key = ''
        # try:
        #     generator = self.text_from_html(file_name)
        # except:
        #     generator = self.text_from_html2(file_name)
        try:
            # paragraphs = [component for component in self.text_from_html(file_name)]
            paragraphs = [component for component in self.text_from_html_revised(file_name)]
        except:
            paragraphs = [component for component in self.text_from_html2(file_name)]
        for i, content in enumerate(paragraphs):
            text = str(content).strip()
            if '' in tmp:
                tmp.remove('')
            if re.search(r"^\d\.$",re.sub(r"<.*?>", "", content.text.strip())) and not heading_concat:
                heading_concat.append(content)
                continue
            elif heading_concat and "strong" in str(content).lower() and not re.search(r"\d\.",str(content)):
                heading_concat.append(content)
                continue
            elif heading_concat and "strong" not in str(content).lower():
                html_text = " ".join([text.text for text in heading_concat])
                print("content to show--------->",html_text)
                print("content to yield--------->",content)
                html_text = '<p>'+html_text+'</p>'
                html_tag = BeautifulSoup(html_text,"html.parser")
                yield html_tag.text , [content.text]
                heading_concat.clear()
                continue
            elif not heading_concat and "strong" in str(content).lower() and not re.search(r"\d\.",str(content)):
                continue
            print("heading_concat------->",heading_concat)
            if re.findall(self.regex_heading_msd, re.sub(r"<.*?>","",content.text.strip())) or '<li>' in text:
                print(f'heading------>{text}')
                if key and tmp:
                    yield key , ["$$".join(tmp)]
                key = content.text.strip()
                tmp.clear()
            else:
                if i == len(paragraphs) - 1:
                    if text and not re.findall(r"Panel\s\d", text):
                        try:
                            content = BeautifulSoup(str(content), 'html.parser')
                            for para in content.find_all('p'):
                                # print('para----yyyyyyyyy', para)
                                para = str(para)
                                para = para.replace('<strong>', '<b>').replace('</strong>', '</b>')
                                para = re.sub(r"<(\/?[^/bems]).*?>", '', para)
                                tmp.append(para)
                        except:
                            pass
                    if key and tmp:
                        yield key, ['$$'.join(tmp)]
                        tmp.clear()
                else:
                    if text and not re.findall(r"Panel\s\d", text):  # filter out heading like 'big panel 1'
                        try:
                            content = BeautifulSoup(str(content),'html.parser')
                            for para in content.find_all('p'):
                                para = str(para)
                                # print('para----xxxxxxx',para)
                                para = para.replace('<strong>', '<b>').replace('</strong>', '</b>')
                                para = re.sub(r"<(\/?[^/bems]).*?>", '', para)
                                tmp.append(para)
                        except:
                            pass

    def validation(self,final,validation_categories):
        for category , cate_value in validation_categories.items():
            if category in final:
                for index,value in enumerate(final[category]):
                    for lang_key, val in value.items():
                        # output = base('msd_content',msd_content_model_location).prediction(val,method='labse')
                        output = base('msd_content',msd_content_model_location).prediction(val)
                        pred = output['output']
                        probability = output['probability']
                        # print(val,'------>',pred)
                        if pred in cate_value:
                            pass
                        else:
                            try:
                                undetected_msd_log(file_name=self.file_name,text=val,header_category=category,content_category=pred,language_code=lang_key).save()
                            except:
                                pass
                            if pred == 'None':
                                pass
                            elif pred == "unmapped":
                                final[category].pop(index)
                                if "None" in final:
                                    final["None"].append({lang_key:val})
                                else:
                                    final["None"] = [{lang_key:val}]
                            elif pred not in ['None','unmapped'] and probability > 0.70:
                                final[category].pop(index)
                                if pred in final:
                                    final[pred].append({lang_key:val})
                                else:
                                    final[pred] = [{lang_key:val}]
                            else:
                                pass
                                # final[category].pop(index)
                            print('fail')
                    if not final[category]:
                        final.pop(category)

    def validation_revised(self,final,validation_categories):
        print("validation starts")
        print("final------------->",final)
        content_to_rewamp = {}
        final_copy = copy.deepcopy(final)
        for category , category_map_list in validation_categories.items():
            print("category_checking------>",category)
            if category in final and category in self.validation_categories:
                print("category_exists")
                print("total number of content in category--->",len(final[category]))
                for index , value_dict in enumerate(final[category]):
                    print("index_number----->",index)
                    content = list(value_dict.values())[0]
                    language = list(value_dict.keys())[0]
                    output = base('msd_content', msd_content_model_location).prediction(content)
                    pred = output['output']
                    probability = output['probability']
                    print(f"{content}--------------->{pred}----------->{probability}")
                    if pred not in category_map_list:
                        if pred != "None":
                            if pred == "unmapped" and probability > 0.80:
                                if "None" in content_to_rewamp:
                                    content_to_rewamp["None"].append({language:content})
                                else:
                                    content_to_rewamp["None"] = [{language:content}]
                            elif pred not in ["unmapped","None"] and probability > 0.70:
                                if pred in content_to_rewamp:
                                    content_to_rewamp[pred].append({language:content})
                                else:
                                    content_to_rewamp[pred] = [{language:content}]
                            else:
                                if category in content_to_rewamp:
                                    content_to_rewamp[category].append(value_dict)
                                else:
                                    content_to_rewamp[category] = [value_dict]
                        else:
                            if category in content_to_rewamp:
                                content_to_rewamp[category].append(value_dict)
                            else:
                                content_to_rewamp[category] = [value_dict]
                    else:
                        if category in content_to_rewamp:
                            content_to_rewamp[category].append(value_dict)
                        else:
                            content_to_rewamp[category] = [value_dict]
                final_copy.pop(category)
            elif category in final and category not in self.validation_categories:
                for index , value_dict in enumerate(final[category]):
                    print("index_number----->",index)
                    content = list(value_dict.values())[0]
                    language = list(value_dict.keys())[0]
                    output = base('msd_content', msd_content_model_location).prediction(content)
                    pred = output['output']
                    probability = output['probability']
                    if pred == "unmapped" and probability > 0.80:
                        if "None" in content_to_rewamp:
                            content_to_rewamp["None"].append({language: content})
                        else:
                            content_to_rewamp["None"] = [{language: content}]
                    else:
                        print("mapping to existing category")
                        if category in content_to_rewamp:
                            content_to_rewamp[category].append(value_dict)
                        else:
                            content_to_rewamp[category] = [value_dict]
                final_copy.pop(category)
        return {**final_copy,**content_to_rewamp}

    def main(self,file_name):
        final = {}
        all_lang = set()
        prediction = None
        tags_to_check = {}
        for key, value in self.heading_value_extraction2(file_name):
            print("======="*10)
            print(key,"------->",value)
            print("======="*10)
            # prediction = base('msd', msd_model_location).prediction(key,method='labse')['output']
            output = base('msd', msd_model_location).prediction(key)
            if output["output"] == "name":
                if prediction:
                    tags_to_check[prediction] = [prediction]
                    print("check prediction--------->", prediction)
            prediction = output['output']
            print(f'{key}---{value}-------->{prediction}')
            if prediction == 'None':
                try:
                    blob = TextBlob(key)
                    key = blob.translate(to='en')
                    prediction = base('msd', msd_model_location).prediction(str(key))["output"]
                except:
                    pass
            if prediction in msd_categories_lang_exception:
                # val = value[0].replace('$$','<br>')
                val = value[0].replace('$$','\n')
                # val = ' '.join([f"<p>{_val.replace('$$','')}</p>" for _val in value[0].split('$$')])
                # cleaned_text = val.translate(str.maketrans("","",string.punctuation))
                # cleaned_text = re.sub(r'\d','',cleaned_text).lower()
                cleaned_text = re.sub(r'\d','',val).lower()
                cleaned_text = cleaned_text.replace('\n', ' ').replace(':', '').strip()
                print(cleaned_text)
                try:
                    lang = lang_detect(cleaned_text)
                    print(f'lang_detect------>{cleaned_text} ------>{lang}')
                    # lang_blob = TextBlob(cleaned_text)
                    # lang1 = lang_blob.detect_language()
                    # print(f'textblob---->{cleaned_text} ------>{lang1}')
                except:
                    lang = classify(cleaned_text)[0]
                    print(f'classify---->{cleaned_text} ------>{lang}')
                all_lang.add(lang)
                if prediction in final:
                    final[prediction].append({lang: str(val)})
                else:
                    final[prediction] = [{lang: str(val)}]
            else:
                for para in value[0].split('$$'):
                    # cleaned_text = para.translate(str.maketrans("", "", string.punctuation))
                    # cleaned_text = re.sub(r'\d', '', cleaned_text).lower()
                    cleaned_text = re.sub(r'\d', '', para).lower()
                    cleaned_text = cleaned_text.replace('\n',' ').replace(':','').strip()
                    try:
                        lang = lang_detect(cleaned_text)
                        print(f'lang_detect------>{cleaned_text} ------>{lang}')
                        # lang_blob = TextBlob(cleaned_text)
                        # lang1 = lang_blob.detect_language()
                        # print(f'textblob---->{cleaned_text} ------>{lang1}')
                    except:
                        lang = classify(cleaned_text)[0]
                        print(f'classify---->{cleaned_text} ------>{lang}')

                    all_lang.add(lang)
                    if prediction in final:
                        final[prediction].append({lang: para})
                    else:
                        final[prediction] = [{lang: para}]
        validation_categories = {**self.validation_categories,**tags_to_check}
        # validation_categories = self.validation_categories
        print("validation_cate----->",validation_categories)
        final = self.validation_revised(final,validation_categories)
        if 'None' in final:
            final['unmapped'] = final['None']
            final.pop('None', None)
        final_cleaned_dict = {}
        for category, value_list in final.items():
            final_cleaned_dict[category] = list({frozenset(list_element.items()): list_element for list_element in value_list}.values())
        final_cleaned_dict = {**{'status': 1, 'language': list(all_lang), 'file_name': [file_name]}, **final_cleaned_dict}
        return final_cleaned_dict
