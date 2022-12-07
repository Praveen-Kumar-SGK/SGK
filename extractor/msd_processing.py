import mammoth
from bs4 import BeautifulSoup
from textblob import TextBlob
from .excel_processing import *

custom_replace_words = {"ΛΞΗ":"ΛΗΞΗ"}

class msd_extraction(base):
    def __init__(self):
        super().__init__()
        self.file_name = None
        # self.regex_heading_msd = r"^\d+\.\d?[\-\s][^%]|\<li\>"   # old
        self.regex_heading_msd = r"^\d+\.\d?[\-\s][^%ml][A-Z]?|\<li\>"
        # self.regex_heading_msd = r"^\d{1,2}\.?\d?[\-\s][^%ml]|\<li\>"
        self.validation_categories = {
                                      'warning':['warning'],
                                      'storage_instructions':['storage_instructions'],
                                      'manufacturer':['address','manufacturer'],
                                      'marketing_company': ['address','marketing_company'],
                                      'expiry_date':['expiry_date'],
                                      'form_content':['form_content'],
                                      'method_route':['method_route'],
                                      'others':['others'],
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

    def text_from_html(self,file_name):             # only for MSD
        print('entering text to _html')
        html = self.docx_to_html(file_name)
        soup = BeautifulSoup(html, 'html.parser')
        '''paragraphs = soup.find_all(['p', 'li'])
        for para in paragraphs:
            if '<em>' not in str(para):
                yield para'''
        print(soup)
        # print("check_table------>",'<table>' in html)
        # print("check_em------>",'<em>' in html)
        # print("check_length------>",all([len(_row.find_all('td')) != 1 for _row in soup.find_all('tr')]))
        # print("check_particulars------>","particulars" not in html.lower())
        # print(any([len(BeautifulSoup(str(_row)).find_all('td')) != 1 for _row in soup.find_all('tr')]))
        # if ('<table>' in html) and ('<em>' in html) and all([len(BeautifulSoup(str(_row)).find_all('td')) != 1 for _row in soup.find_all('tr')]):                         # for table structure
        if ('<table>' in html) and ('<em>' in html) and all([len(_row.find_all('td')) != 1 for _row in soup.find_all('tr')]) and "particulars" not in html.lower():                         # for table structure
            print('inside table structure')
            rows = soup.find_all('tr')
            for row in rows:
                for column in row.find_all('td'):
                    # print('column----->',column)
                    # yield column.findall('p')
                    yield column
        else:                                       # for heading - value structure
            print('inside normal structure')
            paragraphs = soup.find_all(['p', 'li', 'h1'])
            for para in paragraphs:
                # print('para------>',para)
                yield para

    def heading_value_extraction(self,file_name):                       # only for MSD
        tmp = []
        final = {}
        key = ''
        generator = self.text_from_html(file_name)
        paragraphs = [component for component in generator]
        for i, content in enumerate(paragraphs):
            text = str(content)
            if '' in tmp:
                tmp.remove('')
            if (re.findall(self.regex_heading_msd, content.text.strip()) or '<li>' in text):
            # if re.findall(self.regex_heading_msd, text):
                print(f'heading------->{text}')
                try:
                    if key and (key not in final):
                        if tmp:
                            # final[key] = ['$$'.join(tmp)]
                            yield key , ['$$'.join(tmp)]
                    elif key in final:
                        if tmp:
                            # final[key].append('$$'.join(tmp))
                            yield key ,['$$'.join(tmp)]
                    key = re.sub(r'<.*?>', '', text)
                    # print(key)
                    tmp.clear()
                except:
                    pass
            else:
                if i == len(paragraphs) - 1:
                    text = text.strip()
                    tmp = [t for t in tmp if t]
                    if text and not re.findall(r"Panel\s\d", text):
                        text = text.replace('<strong>', '<b>').replace('</strong>', '</b>')
                        text = re.sub(r"<(\/?br\/?)>","",text)
                        text = re.sub(r"<(\/?[^/bems]).*?>", '', text)
                        tmp.append(text)
                    if key not in final:
                        if tmp:
                            # final[key] = ['$$'.join(tmp)]
                            yield key, ['$$'.join(tmp)]
                    elif key in final:
                        if tmp:
                            # final[key].append('$$'.join(tmp))
                            yield key, ['$$'.join(tmp)]
                    else:
                        print('temp__-------append-------->', text)
                        pass
                else:
                    text = text.strip()
                    tmp = [t for t in tmp if t]
                    if text and not re.findall(r"Panel\s\d", text):  # filter out heading like 'big panel 1'
                        text = text.replace('<strong>', '<b>').replace('</strong>', '</b>')
                        text = re.sub(r"<(\/?br\/?)>","\n",text)
                        text = re.sub(r"<(\/?[^/bems]).*?>", '', text)
                        tmp.append(text)

    def heading_value_extraction2(self,file_name):
        tmp = []
        heading_concat = []
        key = ''
        generator = self.text_from_html(file_name)
        paragraphs = [component for component in generator]
        for i, content in enumerate(paragraphs):
            text = str(content).strip()
            if '' in tmp:
                tmp.remove('')
            if ("strong" in text) and heading_concat:
                # print("heading_to_append2------->", text)
                heading_concat.append(content)
                if i + 1 < len(paragraphs) and "strong" in str(paragraphs[i + 1]) and '<li>' not in str(paragraphs[i + 1]) and not re.search(r"^\d\.$",re.sub(r"<.*?>", "", content.text.strip())):
                    continue
                else:
                    html_text = " ".join([text.text for text in heading_concat])
                    html_text = '<li>' + html_text + '</li>'
                    html_tag = BeautifulSoup(html_text, "html.parser")
                    content = html_tag
                    text = str(content).strip()
            elif (re.search(r"^\d\.$",re.sub(r"<.*?>", "", content.text.strip())) and not heading_concat) or "<li>" in text:
            # elif re.findall(r"^\d+\.\d?[\-\s][^%ml]|\<li\>",str(content)):
            #     print("inside elif------->",text)
                heading_concat.clear()
                heading_concat.append(content)
                if i+1 < len(paragraphs) and "strong" in str(paragraphs[i+1]) and '<li>' not in str(paragraphs[i + 1]) and not re.search(r"^\d\.$",re.sub(r"<.*?>", "", content.text.strip())):
                    continue
                else:
                    pass
            heading_concat.clear()
            # elif heading_concat and "strong" in str(content).lower() and not re.search(r"\d\.",str(content)):
            #     heading_concat.append(content)
            #     continue
            # elif heading_concat and "strong" not in str(content).lower():
            #     html_text = " ".join([text.text for text in heading_concat])
            #     print("======"*10)
            #     print("content to heading--------->",html_text)
            #     # print("content to yield--------->",content)
            #     print("======"*10)
            #     html_text = '<li>'+html_text+'</li>'
            #     text = html_text
            #     # html_tag = BeautifulSoup(html_text,"html.parser")
            #     # key = html_tag.text
            #     # heading_concat.clear()
            print("sentence apply for heading ---->",content)
            if re.findall(self.regex_heading_msd, content.text.strip()) or '<li>' in text:
                print("sentence selected for heading ---->", content.text.strip())
                print("-------"*10)
                if key and tmp:
                    # print("========"*10)
                    # print(f'heading------>{key}')
                    # print(f'value--sending------>{text}')
                    # print(f'value------>{[" ".join(tmp)]}')
                    # print("========"*10)
                    yield key , ["$$".join(tmp)]
                key = re.sub(r"\([^)]*(font size).*\)", "", str(content.text.strip()))   # cleaning for rare case scenario 1 file reported
                # key = content.text.strip()
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
                                para = para.replace('<h1>', '<b>').replace('</h1>', '</b>')
                                #para = re.sub(r"<(\/?br\/?|\/?em\/?)>", "", para)
                                para = re.sub(r"<(\/?[^/bems]).*?>", '', para)
                                para = re.sub(r"\([^)]*(font size).*\)", "", para)
                                para = para.replace(chr(0xa0)," ")
                                #para = para.replace(chr(0xae)," ")
                                tmp.append(para)
                        except:
                            pass
                    if key and tmp:
                        # print("========" * 10)
                        # print(f'heading2------>{text}')
                        # print(f'value2------>{[" ".join(tmp)]}')
                        # print("========" * 10)
                        yield key, ['$$'.join(tmp)]
                        tmp.clear()
                        heading_concat.clear()
                else:
                    if text and not re.findall(r"Panel\s\d", text):  # filter out heading like 'big panel 1'
                        try:
                            content = BeautifulSoup(str(content),'html.parser')
                            for para in content.find_all(['p','h1']):
                                para = str(para)
                                # print('para----xxxxxxx',para)
                                para = para.replace('<strong>', '<b>').replace('</strong>', '</b>')
                                para = para.replace('<h1>', '<b>').replace('</h1>', '</b>')
                                #para = re.sub(r"<(\/?br\/?|\/?em\/?)>", "", para)
                                para = re.sub(r"<(\/?[^/bems]).*?>", '', para)
                                para = re.sub(r"\([^)]*(font size).*\)", "", para).strip()
                                #para = para.replace(chr(0xae), " ")
                                para = para.replace(chr(0xa0), " ")
                                # print("adding to tmp------>",para)
                                tmp.append(para)
                        except:
                            pass

    def validation(self,final):
        print("************"*10)
        print("Validation starts")
        print("************" * 10)
        for category , cate_value in self.validation_categories.items():
            if category in final:
                for index,value in enumerate(final[category]):
                    for lang_key, val in value.items():
                        # output = base('msd_content',msd_content_model_location).prediction(val,method='labse')
                        output = base('msd_content',msd_content_model_location).prediction(val)
                        pred = output['output']
                        probability = output['probability']
                        print("++++++++++++++"*10)
                        print(val,'--------->',pred,'----------->',probability)
                        print("++++++++++++++" * 10)
                        if pred in cate_value:
                            pass
                        else:
                            # try:
                            #     undetected_msd_log(file_name=self.file_name,text=val,header_category=category,content_category=pred,language_code=lang_key).save()
                            # except:
                            #     pass
                            if pred == 'None':
                                pass
                            elif pred != 'None' and probability > 0.70:
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

    # def main2(self,file_name):                      # group by language
    #     final = {}
    #     all_lang = set()
    #     check = 0
    #     self.file_name = file_name
    #     for key, value in self.heading_value_extraction(file_name):
    #         prediction = base('msd', msd_model_location).prediction(key)['output']
    #         if prediction in msd_categories_lang_exception:
    #             val = value[0].replace('$$',' ')
    #             # lang = lang_detect(val)[0]
    #             lang = lang_detect(str(val).lower())
    #             all_lang.add(lang)
    #             if prediction in final:
    #                 final[prediction].append({lang: val})
    #             else:
    #                 final[prediction] = [{lang: val}]
    #         elif prediction in ['unique_identifier', 'reg_number']:
    #             if prediction in final:
    #                 final[prediction].extend(value)
    #             else:
    #                 final[prediction] = value
    #         else:
    #             for val in value:
    #                 if '$$' in val:
    #                     print('inside dollar split ##########------>',val)
    #                     prev_lang = None
    #                     for index , text in enumerate(val.split('$$')):
    #                         text = text.replace('$$',' ')
    #                         lang = lang_detect(str(text).lower())
    #                         all_lang.add(lang)
    #                         if prediction in final:
    #                              # if lang in any(lang_detail == lang for lang_content in final[prediction] for lang_detail in lang_content.keys()):
    #                             for lang_content in final[prediction]:
    #                                 for lang_detail in lang_content.keys():
    #                                     if lang_detail == lang:
    #                                         lang_content[lang] = ' '.join((lang_content[lang],text))
    #                                         check = 1
    #                                         break
    #                                     else:
    #                                         pass
    #                             if check == 0:
    #                                 final[prediction].append({lang: text})
    #                             else:
    #                                 check = 0
    #                         else:
    #                             print(text,'---->first')
    #                             final[prediction] = [{lang: text}]
    #                 else:
    #                     print('inside not dollar split ##########------>',val)
    #                     lang = lang_detect(str(value[0]).lower())
    #                     all_lang.add(lang)
    #                     if prediction in final:
    #                         final[prediction].append({lang: val})
    #                     else:
    #                         final[prediction] = [{lang: val}]
    #     # if 'unique_identifier' in final:
    #     #     print('checking unique identifiers')
    #     #     print(final['unique_identifier'])
    #     #     for key, identifier in self.regex_parsers_generator(final['unique_identifier']):
    #     #         identifier = str(identifier).strip()
    #     #         print('identifier--->',identifier)
    #     #         if identifier:
    #     #             final[key] = [identifier]
    #     #     final.pop('unique_identifier',None)
    #     if 'unique_identifier' in final:
    #         identifier_clear = []
    #         for identifier in final['unique_identifier']:
    #             identifier_clear.append(identifier.replace('$$',' '))
    #         final['unique_identifier'] = identifier_clear
    #     if 'None' in final:
    #         final.pop('None',None)
    #     final = {**{'status': 1,'language': list(all_lang),'file_name': [file_name]},**final}
    #     self.validation(final)
    #     return final

    def main(self,file_name):
        final = {}
        all_lang = set()
        for key, value in self.heading_value_extraction2(file_name):
            # prediction = base('msd', msd_model_location).prediction(key,method='labse')['output']
            prediction = base('msd', msd_model_location).prediction(key)['output']
            print(f'{key}---{value}-------->{prediction}')
            if prediction == 'None':
                try:
                    blob = TextBlob(key)
                    key = blob.translate(to='en')
                    prediction = base('msd', msd_model_location).prediction(str(key))['output']
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
                ########## custom patch
                custom_val = custom_replace_words.get(str(val),None)
                if custom_val:
                    val = custom_val
                ######### Custom patch
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
                    ######### Custom patch
                    custom_val = custom_replace_words.get(str(para), None)
                    if custom_val:
                        para = custom_val
                    ######### Custom patch
                    if prediction in final:
                        final[prediction].append({lang: para})
                    else:
                        final[prediction] = [{lang: para}]
        if 'None' in final:
            final['unmapped'] = final['None']
            final.pop('None', None)
        final = {**{'status': 1, 'language': list(all_lang), 'file_name': [file_name]}, **final}
        print(final)
        self.validation(final)
        return final

    # def main_old(self,file_name):
    #     final = {}
    #     all_lang = set()
    #     for key , value in self.heading_value_extraction2(file_name):
    #         prediction = base('msd',msd_model_location).prediction(key)['output']
    #         print(value[0])
    #         if prediction in msd_categories_lang_exception:
    #             val = value[0].replace('$$',' ')
    #             # lang = lang_detect(val)[0]
    #             lang = lang_detect(val)
    #             all_lang.add(lang)
    #             if prediction in final:
    #                 final[prediction].append({lang: val})
    #             else:
    #                 final[prediction] = [{lang: val}]
    #         elif prediction in ['unique_identifier']:
    #             if prediction in final:
    #                 final[prediction].extend(value)
    #             else:
    #                 final[prediction] = value
    #         else:
    #             for val in value:
    #                 if '$$' in val:
    #                     topic = ''
    #                     for index, text in enumerate(val.split('$$')):
    #                         text = text.replace('$$', ' ')
    #                         if len(str(text).split()) > 2:
    #                             text = ' '.join((topic, text)).strip()
    #                             topic = ''
    #                             # lang = classify(text)[0]
    #                             lang = lang_detect(text)
    #                             all_lang.add(lang)
    #                             if prediction in final:
    #                                 final[prediction].append({lang: text})
    #                             else:
    #                                 final[prediction] = [{lang: text}]
    #                         else:
    #                             topic = ' '.join((topic, text)).strip()
    #                             if index == len(val.split('$$')) - 1:
    #                                 # lang = lang_detect(topic)[0]
    #                                 lang = lang_detect(topic)
    #                                 all_lang.add(lang)
    #                                 if prediction in final:
    #                                     final[prediction].append({lang: topic})
    #                                 else:
    #                                     final[prediction] = [{lang: topic}]
    #                                 topic = ''
    #                             else:
    #                                 pass
    #                 else:
    #                     # lang = classify(value[0])[0]
    #                     lang = lang_detect(value[0])
    #                     all_lang.add(lang)
    #                     if prediction in final:
    #                         final[prediction].append({lang: val})
    #                     else:
    #                         final[prediction] = [{lang: val}]
    #     # if 'unique_identifier' in final:
    #     #     print('checking unique identifiers')
    #     #     print(final['unique_identifier'])
    #     #     for key, identifier in self.regex_parsers_generator(final['unique_identifier']):
    #     #         identifier = str(identifier).strip()
    #     #         print('identifier--->',identifier)
    #     #         if identifier:
    #     #             final[key] = [identifier]
    #     #     final.pop('unique_identifier',None)
    #     if 'unique_identifier' in final:
    #         identifier_clear = []
    #         for identifier in final['unique_identifier']:
    #             identifier_clear.append(identifier.replace('$$',' '))
    #         final['unique_identifier'] = identifier_clear
    #     if 'None' in final:
    #         final.pop('None',None)
    #     final = {**{'status': 1,'language': list(all_lang),'file_name': [file_name]},**final}
    #     self.validation(final)
    #     return final


# pattern = r"^\d+\.\d?[\-\s][^%ml][A-Z]?|\<li\>"
#
# sentence = "1.	LÄKEMEDLETS NAMN"
#
# re.search(pattern,sentence)