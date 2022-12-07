import PyPDF2 as pypdf2
import pikepdf
import io
import time
from random import randint , choice
import subprocess
import tempfile
import os
# import ray
from pdfminer.layout import LAParams
from pdfminer.high_level import extract_text_to_fp
from bs4 import BeautifulSoup
import chardet
import pdfplumber
from collections import namedtuple

from .excel_processing import *

op_file = io.StringIO()
pike_input = io.BytesIO()

# temp_dir = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/temp"

DG_header_dict = {'compare to statement':['primary compare to statement'],'NBE product selling feature callouts we can use':['primary NBE product selling feature callouts we can use'],
        'ingredients':['primary ingredients','secondary ingredients'],
        'nutrition facts_1':['primary nutrition facts'],'nutrition facts_2':['secondary nutrition facts'],
        'storage instruction':['primary storage instructions','secondary storage instructions'],'product name':['suggested product name'],
        'net weight':['net wt'],'upc':['upc'],'notes':['primary notes','primary DG notes','primary additional notes','secondary notes','secondary DG notes','secondary additional notes'],
        'legal disclaimer':['primary legal disclaimer','primary DG legal disclaimer','secondary legal disclaimer','secondary DG legal disclaimer'],
        'product selling feature callouts':['primary product selling feature callouts','secondary NBE product selling feature callouts','secondary product selling feature callouts'],
        'usage instructions':['primary consumer directions/useage instructions','secondary consumer directions/useage instructions'],
        'country of origin':['primary country of origin','secondary country of origin'],
        'allergen statement':['primary allergen statement','secondary allergen statement'],
        'warning statement': ['primary warning/caution statements','secondary warning/caution statements'],
        'legal copy requirements':['primary legal copy requirements','secondary legal copy requirements'],
        }


validation_categories = {'warning statement':['warning statement'],
                        'storage instruction':['storage_instructions'],
                        'ingredients':['ingredients'],
                        'allergen statement':['allergen statement'],
                        }

# ray.init(num_cpus=4,ignore_reinit_error=True)

# @ray.remote
class Dollar_General(object):
    def __init__(self):
        self.input_pdf = None
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self.output_io = io.StringIO()
        self.input_file = io.BytesIO()
        self.flat_ps = f'{self.temp_directory.name}/flatten.ps'
        self.flat_pdf = f'{self.temp_directory.name}/flatten.pdf'

    def get_pdf_file(self,file):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                self.input_file.write(f.read())
                self.input_file.seek(0)
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                self.input_file.write(f.read())
                self.input_file.seek(0)
                print('file found')

        finally:
            smbclient.reset_connection_cache()
        return self.input_file

    def ray_to_flatten_pdf(self,input_pdf):
        output, error = subprocess.Popen(f'pdf2ps {input_pdf} {self.flat_ps} ; ps2pdf {self.flat_ps} {self.flat_pdf}',shell=True).communicate()
        if not error and not output:
            return 'success'
        else:
            return 'failed'

    # def get_form_elements_old(self,input_pdf):
    #     if input_pdf.startswith('\\'):
    #         SMB_pdf_object = self.get_pdf_file(input_pdf)
    #         pike_input_pdf = pikepdf.open(SMB_pdf_object)
    #         pike_input_pdf.save(f'{self.temp_directory.name}/input.pdf')
    #         self.input_pdf = f'{self.temp_directory.name}/input.pdf'
    #     else:
    #         self.input_pdf = document_location+input_pdf
    #     pdfobj = open(self.input_pdf, 'rb')
    #     pdf = pypdf2.PdfFileReader(pdfobj)
    #     if pdf.isEncrypted:
    #         print('encrypted pdf')
    #         print(pdf)
    #         pike_pdf = pikepdf.open(self.input_pdf)
    #         pike_pdf.save(f'{self.temp_directory.name}/pike.pdf')           #pike pdf location
    #         pdfobj_pike = open(f'{self.temp_directory.name}/pike.pdf', 'rb')
    #         pdf_pike = pypdf2.PdfFileReader(pdfobj_pike)
    #         dict_form_fields = pdf_pike.getFields()
    #     else:
    #         print('not encrypted pdf')
    #         dict_form_fields = pdf.getFields()
    #     return dict_form_fields

    def attribute_checking(self,input_pdf, text,encoding):
        text_out = []
        if input_pdf.startswith('\\'):
            if not self.output_io.getvalue():
                extract_text_to_fp(self.input_file, self.output_io,laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),
                                       output_type='html', codec=None)
            else:
                pass
        else:
            if not self.output_io.getvalue():
                with open(self.flat_pdf,'rb') as input:
                    extract_text_to_fp(input, self.output_io,laparams=LAParams(line_margin=0.18, line_overlap=0.4, all_texts=False),output_type='html', codec=None)
            else:
                pass
        html = BeautifulSoup(self.output_io.getvalue(), 'html.parser')
        results = html.find_all(lambda tag: tag.name == "div" and ' '.join(text.replace('\n', '').split()[:3]) in tag.text.replace('\n', ''))
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
        else:
            return None

    # def main_old(self,input_pdf):
    #     final_dict = {}
    #     # flatten_status = self.ray_to_flatten_pdf(input_pdf)
    #     # assert flatten_status == "success"
    #     dictionary = self.get_form_elements(input_pdf)
    #     dictionary_filtered = {key: value for key, value in dictionary.items() if 'print' not in key and value.fieldType == "/Tx"}
    #     for key , value in dictionary_filtered.items():
    #         for header , synonyms in DG_header_dict.items():
    #             content = value.value
    #             if key in synonyms and content and content != 'n/a':
    #                 encoding = None
    #                 try:
    #                     encoding = chardet.detect(content)['encoding']
    #                 except:
    #                     pass
    #                 if encoding:
    #                     # print(f'content before decoding--->{encoding}---->{content}')
    #                     try:
    #                         content = content.decode('latin')
    #                     except:
    #                         content = content.decode(encoding)
    #                     # print('decoding done')
    #                 # text_with_attr = self.attribute_checking(self.flat_pdf, content,encoding)
    #                 # if text_with_attr:
    #                 #     content = text_with_attr
    #                 # else:
    #                 #     pass
    #                 if header in final_dict:
    #                     final_dict[header].append({'en':content})
    #                 else:
    #                     final_dict[header] = [{'en':content}]
    #     self.temp_directory.cleanup()
    #     self.input_file.close()
    #     self.output_io.close()
    #     return final_dict


    def get_form_elements(self,input_pdf):
        dict_page_wise = {}
        if input_pdf.startswith('\\'):
            SMB_pdf_object = self.get_pdf_file(input_pdf)
            pike_input_pdf = pikepdf.open(SMB_pdf_object)
            pike_input_pdf.save(f'{self.temp_directory.name}/input.pdf')
            self.input_pdf = f'{self.temp_directory.name}/input.pdf'
        else:
            self.input_pdf = document_location+input_pdf
        pdfobj = open(self.input_pdf, 'rb')
        pdf = pypdf2.PdfFileReader(pdfobj)
        if pdf.isEncrypted:
            print('encrypted pdf')
            print(pdf)
            pike_pdf = pikepdf.open(self.input_pdf)
            pike_pdf.save(f'{self.temp_directory.name}/pike.pdf')           #pike pdf location
            plumb_pdf = pdfplumber.open(f'{self.temp_directory.name}/pike.pdf')
            for pdf_form_obj in plumb_pdf.annots:
                page_no = pdf_form_obj['page_number']
                title = pdf_form_obj['title']
                if not title:
                    continue
                if 'V' in pdf_form_obj['data']:
                    if pdf_form_obj['data']['V']:
                        contents = pdf_form_obj['data']['V']
                    else:
                        continue
                else:
                    continue
                if page_no in dict_page_wise:
                    dict_page_wise[page_no][title] = contents
                else:
                    dict_page_wise[page_no] = {title: contents}
        else:
            print('not encrypted pdf')
            plumb_pdf = pdfplumber.open(self.input_pdf)
            dict_page_wise = {}
            for pdf_form_obj in plumb_pdf.annots:
                page_no = pdf_form_obj['page_number']
                title = pdf_form_obj['title']
                if not title:
                    continue
                if 'V' in pdf_form_obj['data']:
                    if pdf_form_obj['data']['V']:
                        contents = pdf_form_obj['data']['V']
                    else:
                        continue
                else:
                    continue
                if page_no in dict_page_wise:
                    dict_page_wise[page_no][title] = contents
                else:
                    dict_page_wise[page_no] = {title: contents}
        return dict_page_wise

    def main(self,input_pdf,pages):
        final_page = {}
        dictionary = self.get_form_elements(input_pdf)
        for page in pages.split(','):
            final_dict = {}
            if int(page) in dictionary:
                page_dict = dictionary[int(page)]
                for key , value in page_dict.items():
                    for header , header_value in DG_header_dict.items():
                        content = value
                        if key in header_value and value:
                            encoding = None
                            try:
                                encoding = chardet.detect(content)['encoding']
                            except:
                                pass
                            if encoding:
                                try:
                                    content = value.decode(encoding)
                                except:
                                    content = value.decode('latin')
                            if 'nutrition facts' in header:
                                # print(f'nutrition_facts--->{content}')
                                nutrition_check = base('general',model_location).prediction(content)
                                if nutrition_check['output'] == 'Nutrition':
                                    _nutrition_local_dict = {}
                                    _nutrition_local_list = []
                                    _nutrition = namedtuple('nutrition',['Name','Value','PDV'])
                                    if ':' not in content:
                                        for line in str(content).split('\r'):
                                            if 'serving' not in line.lower() and line.strip():
                                                if 'includes' not in line.lower():
                                                    regex_result = re.findall(r'(\D*)(\d*\.?\d*(g|mg|mcg)?)(.*)',line)[0]
                                                    if regex_result[0].strip():
                                                        _nutrition_local_list.append(_nutrition(regex_result[0].strip(),regex_result[1].strip(),regex_result[3].strip()))
                                                else:
                                                    regex_result = re.findall(r'(Includes\s\d*?g\s*?\D*)(.*)',line)[0]
                                                    if regex_result[0].strip():
                                                        _nutrition_local_list.append(_nutrition(regex_result[0].strip(), "",regex_result[1].strip()))
                                                print(f'regex result ---->{regex_result}')
                                                # if regex_result[0].strip():
                                                #     _nutrition_local_list.append(_nutrition(regex_result[0].strip(),regex_result[1].strip(),regex_result[3].strip()))
                                            else:
                                                if line.strip():
                                                    if header in final_dict:
                                                        final_dict['serving information'].append({'en': line})
                                                    else:
                                                        final_dict['serving information'] = [{'en': line}]
                                        for nutrition_tuple in _nutrition_local_list:
                                            if nutrition_tuple.Value and nutrition_tuple.PDV:
                                                _nutrition_local_dict[nutrition_tuple.Name] = [{'Value':{'en':nutrition_tuple.Value}},{'PDV': {'en': nutrition_tuple.PDV}}]
                                            elif nutrition_tuple.Value and not nutrition_tuple.PDV:
                                                _nutrition_local_dict[nutrition_tuple.Name] = [{'Value':{'en':nutrition_tuple.Value}}]
                                            else:
                                                _nutrition_local_dict[nutrition_tuple.Name] = [{'PDV': {'en': nutrition_tuple.PDV}}]
                                    else:
                                        for line in str(content).split('\r'):
                                            if 'serving' not in line.lower() and line.strip():
                                                regex_result = re.findall(r'(\D.*)[:：](.*)',line)
                                                print(f'regex result ---->{regex_result}')
                                                if regex_result and regex_result[0][0].strip():
                                                    _nutrition_local_list.append(_nutrition(regex_result[0][0].strip(),regex_result[0][1].strip(),''))
                                                else:
                                                    continue
                                        for nutrition_tuple in _nutrition_local_list:
                                            if nutrition_tuple.Value and nutrition_tuple.PDV:
                                                _nutrition_local_dict[nutrition_tuple.Name] = [{'Value':{'en':nutrition_tuple.Value}},{'PDV': {'en': nutrition_tuple.PDV}}]
                                            elif nutrition_tuple.Value and not nutrition_tuple.PDV:
                                                _nutrition_local_dict[nutrition_tuple.Name] = [{'Value':{'en':nutrition_tuple.Value}}]
                                            else:
                                                _nutrition_local_dict[nutrition_tuple.Name] = [{'PDV': {'en': nutrition_tuple.PDV}}]
                                    final_dict[header] = _nutrition_local_dict
                                    print(_nutrition_local_dict)
                                    continue
                                elif nutrition_check['output'] == 'ingredients':
                                    header = 'NUTRITIONAL_CLAIM'
                                    if header in final_dict:
                                        final_dict[header].append({'en': content})
                                    else:
                                        final_dict[header] = [{'en': content}]
                                    continue
                                else:
                                    print('this is not a nutrition')
                                    continue
                            if header in validation_categories:
                                output = base('general',model_location).prediction(content)
                                prediction = output['output']
                                probability = output['probability']
                                # print(f'{content}---------->{prediction}')
                                if prediction not in ['None','others']:
                                    if probability > 0.80 and prediction not in validation_categories[header]:
                                        header = prediction
                                else:
                                    pass
                            if header in final_dict:
                                final_dict[header].append({'en': content})
                                # final_dict[header].append(content)
                            else:
                                final_dict[header] = [{'en':content}]
            else:
                final_dict = {}
            final_page[page] = final_dict
        self.temp_directory.cleanup()
        self.input_file.close()
        self.output_io.close()
        return final_page



