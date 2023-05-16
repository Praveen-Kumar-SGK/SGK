# Django Libraries
from django.shortcuts import render, redirect, reverse
from django.http import HttpResponse, JsonResponse, HttpResponseBadRequest, Http404
from django.views.decorators.csrf import csrf_exempt
from django.views import View

# Rest framework import
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.decorators import api_view,permission_classes,authentication_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.authentication import SessionAuthentication, BasicAuthentication , TokenAuthentication
import json
import langid
import langdetect as lang_det
from langdetect import DetectorFactory
from collections import Counter

from .utils import GoogleTranslate

DetectorFactory.seed = 1

# import other class
# from .excel_processing import *
from .msd_processing import *
from .astrazeneca_processing import az_extraction
# from .ferrero_final import main as ferr_main
# from .ferrero_processing import *
from .ferrero_processing_chinese_fix import *
from .unilever_processing import main as main_unilever
from .unilever_processing import unilever_excel_main #for single url functionality
from .unilever_docx_processing import unilever_docx_main
from .unilever_pdf import unilever_pdf_main , unilever_main  #unilever main function for single url
# from .ferrero_new import *
# from .ferrero_final import output_io
# from .excel_extraction1 import *
from .quacker_pdf import quaker_main

from .Albertson_trial1 import albertson_main

from .mondelez_pdf_processing import mondelez_pdf as mp

# from .mondelez_word_updated import mondelez_word as mw
from .mondelez_word_processing import main as mw

from .excel_extraction import excel_extraction_new , gfs_main #gfs main for single url

from .DG_processing import *

# from .carrefour_excel import excel_extract_carrefour
#from .carrefour_excel_new import main as excel_extract_carrefour
#from .carrefour_excel_new import carrefour_main    # carrefour main for single url
from .carrefour_excel_new_v2 import carrefour_extraction

from .carrefour import carrefour_cep_proccessing

from .Griesson_processing import griesson_processing

from .Nestle_processing import *

from .kellogs_extraction import excel_extract_kelloggs , kelloggs_main  # kellogs main fun for single url

from .General_mills_hd import main as main_gm

from .docx_tag_content_extractor_for_tornado import docx_tag_extractor_for_tornado as docx_ext_tornado

from .j_and_j_processing import j_and_j_main

from.henkal_cep import henkal_main

from .conagra import conagra_main
from .mead_johnson import mead_final_main

from .ferrero_cep import ferrero_main
from .sainsbury import sainsbury_main
from .heinz import heinz_main
from .beiersdorf_cep import beiersdorf_cep_main
from .kimberly_cep import CEP_Template
from .cocacola_cep import Cocacola_CEP_Template
from .pepsi_cep import Pepsi_CEP_Template
from .home_and_laundry_cep import Home_and_laundry_CEP_Template
from .jnj_listerine_cep import Listerine_CEP_Template
from .mondelez_cep import Mondelez_CEP_Template
from .mondelez_mea_plus_older_regions import mondelez_mea_word_main
from .ascensia_cep import Ascensia_CEP_Template
from .danone_cep import Danone_CEP_Template

# annotation capture
from .annotation_capture import capture_annotations_for_n_files

import smbclient
from environment import MODE

if MODE == 'local':
    from .local_constants import smb_username , smb_password , document_location
else:
    from .dev_constants import smb_username , smb_password, document_location

import concurrent.futures
from functools import partial
from multiprocessing.pool import Pool

def msd(request):
    final_json = {}
    # getting value from query string
    file_name_list = request.GET.getlist('file','no file')
    print('file_list',file_name_list)
    if file_name_list == 'no file':
        return render(request, 'extractor/index_msd.html')
        # return Response({'status':'0'})
    else:
        pass
    for file_index , file_name in enumerate(file_name_list):
        doc_format = os.path.splitext(file_name)[1].lower()
        if doc_format == '.docx':
            output = msd_extraction().main(file_name)
            final_json[file_index] = output
            try:
                log_book(accounts='MSD', input_file=file_name, input_body={}, output=output).save()
            except:
                pass
        else:
            final_json[file_index] = {'status':0}
    return JsonResponse(final_json)

def astrazeneca(request):
    final_json = {}
    # getting value from query string
    file_name_list = request.GET.getlist('file','no file')
    print('file_list----->',file_name_list)
    for file_index , file_name in enumerate(file_name_list):
        doc_format = os.path.splitext(file_name)[1].lower()
        if doc_format == '.docx':
            output = az_extraction().main(file_name)
            final_json[file_index] = output
        else:
            final_json[file_index] = {'status':0}
    return JsonResponse(final_json)

def ferrero(request):
    ferrero_final = {}
    files = request.GET.getlist('file',None)
    pages = request.GET.getlist('pages',None)
    print(f'files---------->{files}')
    print(f'pages---------->{pages}')
    if len(files) == len(pages):
        for index , file in enumerate(files):
            # if file.startswith('\\'):
            #     pass
            # else:
            #     file = document_location + file

            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.pdf' and pages:
                out = ferrero_extraction().main(file,pages[index])
                # try:
                #     log_book(accounts='Ferrero', input_file=file, input_body={}, output=out).save()
                # except:
                #     pass
                ferrero_final[file] = out
            else:
                ferrero_final = {'status':0,'comment':'Please enter the file name with correct extensions'}
    else:
        ferrero_final = {'status':0,'comment':'please provide correct query strings'}
    return JsonResponse(ferrero_final)

# def ferrero(request):                     #chinese fix
#     ferrero_final = {}
#     files = request.GET.getlist('file',None)
#     pages = request.GET.getlist('pages',None)
#     print(f'files---------->{files}')
#     print(f'pages---------->{pages}')
#     if len(files) == len(pages):
#         for index , file in enumerate(files):
#             # if file.startswith('\\'):
#             #     pass
#             # else:
#             #     file = document_location + file
#
#             doc_format = os.path.splitext(file)[1].lower()
#             if doc_format == '.pdf' and pages:
#                 out = ferrero_extraction().main(file,pages[index])
#                 ferrero_final[file] = out
#     else:
#         ferrero_final = {'status':0,'comment':'please provide correct query strings'}
#     return JsonResponse(ferrero_final)

def dollar_general(request):
    files = request.GET.getlist('file',None)
    pages = request.GET.getlist('pages',None)
    final = {}
    results = []
    # dg_actors = [Dollar_General.remote() for i in range(len(files))]
    # results = [actor.main.remote(file) for actor,file in zip(dg_actors,files)]
    if len(files) == len(pages):
        for index,file in enumerate(files):
            # dg = Dollar_General.remote()
            # results.append(dg.main.remote(file,pages[index]))
            dg = Dollar_General()
            results.append(dg.main(file,pages[index]))

        # for index,result in enumerate(ray.get(results)):
        for index,result in enumerate(results):
            # try:
            #     log_book(accounts='Dollar General', input_file=files[index], input_body={}, output=result).save()
            # except:
            #     pass
            final[files[index]] = result

    else:
        final = {'status':0,'comment':'Please provide proper query strings'}
    print(final)
    return JsonResponse(final)

def nestle(request):
    files = request.GET.getlist('file',None)
    pages = request.GET.getlist('pages',None)
    final = {}
    results = []
    if len(files) == len(pages):
        for index,file in enumerate(files):
            nestle = Nestle_processing()
            results.append(nestle.main(file,pages[index]))
        for index,result in enumerate(results):
            # try:
            #     log_book(accounts='Nestle', input_file=files[index], input_body={}, output=result).save()
            # except:
            #     pass
            final[files[index]] = result
    else:
        final = {'status':0,'comment':'Please provide proper query strings'}
    # print(final)
    return JsonResponse(final)

def albertson(request):
    final = {}
    files = request.GET.getlist('file',None)
    pages = request.GET.getlist('pages',None)
    print(files,pages)
    if len(files) == len(pages):
        for index , file in enumerate(files):
            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.pdf':
                # albertson = Albertson_processing()
                result = albertson_main(file,pages[index])
                final[file] = result
            else:
                final[file] = {'status': 0, 'comment': 'please check the file format'}
    return JsonResponse(final)

def mondelez_word(request):
    final = {}
    files = request.GET.getlist('file',None)
    print(files)
    for index , file in enumerate(files):
        doc_format = os.path.splitext(file)[1].lower()
        if doc_format == '.docx':
            result = mw(file)
            final[file] = result
        else:
            final[file] = {'status':0,'comment':'please check the file format'}
    return JsonResponse(final)

def mondelez_pdf(request):
    final = {}
    files = request.GET.getlist('file',None)
    pages = request.GET.getlist('pages',None)
    print(files,pages)
    if len(files) == len(pages):
        for index , file in enumerate(files):
            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.pdf':
                result = mp().main(input_pdf = file,pages = pages[index])
                final[file] = result
            else:
                final[file] = {'status': 0, 'comment': 'please check the file format'}
    print(final)
    return JsonResponse(final)

def general_mills_hd(request):
    final = {}
    files = request.GET.getlist('file',None)
    print(files)
    for index , file in enumerate(files):
        doc_format = os.path.splitext(file)[1].lower()
        if doc_format == '.docx':
            result = main_gm(file)
            final[file] = result
        else:
            final[file] = {'status':'0','comment':'please check the file format'}
    return JsonResponse(final)

def carrefour_excel(request):
    output_files = {}
    files = request.GET.getlist('file',None)
    sheet_names = request.GET.getlist('sheet',None)
    print(f'file-------->{files}')
    print(f'sheet_name-------->{sheet_names}')
    for index , file in enumerate(files):
        output_sheets = {}
        for sheet in sheet_names[index].split(','):
            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.xlsx' and sheet:
                output = carrefour_extraction(file,sheet)
            else:
                output = {'status':0,'comment':'please check the input file format'}
            output_sheets[sheet] = output
        # try:
        #     log_book(accounts='GFS Excel', input_file=file, input_body={}, output=output_sheets).save()
        # except:
        #     pass
        output_files[file] = output_sheets
    return JsonResponse(output_files)

def unilever_excel(request):
    output_files = {}
    files = request.GET.getlist('file', None)
    sheet_names = request.GET.getlist('sheet', None)
    print(f'file-------->{files}')
    print(f'sheet_name-------->{sheet_names}')
    for index, file in enumerate(files):
        output_sheets = {}
        for sheet in sheet_names[index].split(','):
            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.xlsx' and sheet:
                output = main_unilever(file, sheetname=sheet)
            else:
                output = {'status': 0, 'comment': 'please check the input file format'}
            output_sheets[sheet] = output
        # try:
        #     log_book(accounts='GFS Excel', input_file=file, input_body={}, output=output_sheets).save()
        # except:
        #     pass
        output_files[file] = output_sheets
    return JsonResponse(output_files)


def unilever(request):
    output_files = {}
    files = request.GET.getlist('file', None)
    sheet_names = request.GET.getlist('sheet', None)
    pages = request.GET.getlist('pages', None)
    print(f'file-------->{files}')
    print(f'sheet_name-------->{sheet_names}')
    excel_count = 0
    pdf_count = 0
    for index, file in enumerate(files):
        doc_format = os.path.splitext(file)[1].lower()
        if doc_format == '.xlsx':
            output_sheets = {}
            for sheet in sheet_names[excel_count].split(','):
                if sheet:
                    output = main_unilever(file, sheetname=sheet)
                    output_sheets[sheet] = output
            output_files[file] = output_sheets
            excel_count = excel_count + 1
        elif doc_format == '.docx':
            result = unilever_docx_main(file)
            output_files[file] = result
        elif doc_format == ".pdf":
            page_dict = {}
            for page in pages[pdf_count].split(','):
                if page:
                    result = unilever_pdf_main(file,page_no=int(page))
                    page_dict[page] = result
            output_files[file] = page_dict
            pdf_count = pdf_count + 1
        else:
            output = {'status': 0, 'comment': 'please check the input file format'}
            output_files[file] = output
    return JsonResponse(output_files)

def excel_extraction(request):
    output_files = {}
    files = request.GET.getlist('file',None)
    sheet_names = request.GET.getlist('sheet',None)
    print(f'file-------->{files}')
    print(f'sheet_name-------->{sheet_names}')
    for index , file in enumerate(files):
        output_sheets = {}
        for sheet in sheet_names[index].split(','):
            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.xlsx' and sheet:
                output = excel_extraction_new(file,sheetname=sheet)
            else:
                output = {'status':0}
            output_sheets[sheet] = output
        # try:
        #     log_book(accounts='GFS Excel', input_file=file, input_body={}, output=output_sheets).save()
        # except:
        #     pass
        output_files[file] = output_sheets
    return JsonResponse(output_files)

def kelloggs_extraction(request):
    output_files = {}
    files = request.GET.getlist('file',None)
    sheet_names = request.GET.getlist('sheet',None)
    print(f'file-------->{files}')
    print(f'sheet_name-------->{sheet_names}')
    for index , file in enumerate(files):
        output_sheets = {}
        for sheet in sheet_names[index].split(','):
            doc_format = os.path.splitext(file)[1].lower()
            if doc_format == '.xlsx' and sheet:
                # print('sakthi')
                output = excel_extract_kelloggs(file,sheetname=sheet)
                # output = Kelloggs(file,sheetname=sheet).excel_extract_kelloggs()
            else:
                output = {'status':0}
            output_sheets[sheet] = output
        # try:
        #     log_book(accounts='Kellogs Excel', input_file=file, input_body={}, output=output_sheets).save()
        # except:
        #     pass
        output_files[file] = output_sheets
    return JsonResponse(output_files)

@csrf_exempt
def griesson(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    try:
        result = griesson_processing(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Carrefour", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Carrefour", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

from .carrefour_cep_clustering import carrefour_cep_main
@csrf_exempt
def carrefour(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    # result = carrefour_cep_proccessing(body) #old
    try:
        brand_name = body.get("brand_name", None)
        result = carrefour_cep_main(body["data"], brand_name)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Carrefour", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Carrefour", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

@csrf_exempt
def j_and_j(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = j_and_j_main({"data":body})
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "JnJ", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"JnJ", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

    
@csrf_exempt
def henkal_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = henkal_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Henkal", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Henkal", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)
    
@csrf_exempt
def ferrero_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    try:
        result = ferrero_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Ferrero", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Ferrero", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

@csrf_exempt
def beiersdorf_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
    	result = beiersdorf_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Beiersdorf", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Beiersdorf", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)
    
@csrf_exempt
def kimberly_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
    	result = CEP_Template().kimberly_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Kimberly", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Kimberly", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

@csrf_exempt
def cocacola_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Cocacola_CEP_Template().cocacola_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Cocacola", "file": str(body)},
               output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"Cocacola", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)


@csrf_exempt
def pepsi_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Pepsi_CEP_Template().pepsi_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Pepsi", "file": str(body)},
               output=str(E), error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account": "Pepsi", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

@csrf_exempt
def home_and_laundry_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Home_and_laundry_CEP_Template().home_and_laundry_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "Home_and_Laundry", "file": str(body)},
               output=str(E), error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account": "Home_and_Laundry", "file": str(body)}, output=str(result)).save()
        return JsonResponse(result)

@csrf_exempt
def jnj_listerine_cep_view(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Listerine_CEP_Template().listerine_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "jnj_listerine", "file": str(body)},
            output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"jnj_listerine", "file": str(body)}, output=str(result)).save()
    return JsonResponse(result)

@csrf_exempt
def mondelez_cep_view(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Mondelez_CEP_Template().mondelez_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "mondelez", "file": str(body)},
            output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"mondelez", "file": str(body)}, output=str(result)).save()
    return JsonResponse(result)

@csrf_exempt
def ascensia_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Ascensia_CEP_Template().cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "ascensia", "file": str(body)},
            output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"ascensia", "file": str(body)}, output=str(result)).save()
    return JsonResponse(result)

@csrf_exempt
def danone_cep(request):
    json_response = request.body.decode('utf-8')
    body = json.loads(json_response)
    print(body)
    try:
        result = Danone_CEP_Template().danone_cep_main(body)
    except Exception as E:
        logger(account_type="CEP", input_body={"account": "danone", "file": str(body)},
            output=str(E),error=str(E)).save()
        return JsonResponse({})
    else:
        logger(account_type="CEP", input_body={"account":"danone", "file": str(body)}, output=str(result)).save()
    return JsonResponse(result)

@csrf_exempt
def language_detection(request):
    langs = set()
    if request.method == 'GET':
        text_list = request.GET.getlist('text',None)
    else:
        text_list = request.POST.getlist('text',None)
    print(text_list)
    for text in text_list:
        cleaned_text = text.lower().strip()
        cleaned_text = re.sub(r"\d",'',cleaned_text)
        text_array = cleaned_text.split('/')
        for text in text_array:
            text = re.sub(r'[^\w\s]', '', text).strip()
            text = text.replace('\n',' ')
            text = text.replace("<","").replace(">","")
            if text:
                with GoogleTranslate(text) as output:
                    langs.add(output['language'])
    return HttpResponse(",".join(list(langs)))

def docx_tag_content_extractor_for_tornado(request):
    files = request.GET.getlist('file',None)
    tags = request.GET.getlist('tag',None)
    print(f'filessss------>{files}')
    print(f'tagsss------>{tags}')
    result = None
    for index,file_name in enumerate(files):
        doc_format = os.path.splitext(file_name)[1].lower()
        if 'html' in doc_format.lower():
            doc_type = 'html'
        elif 'xml' in doc_format.lower():
            doc_type = 'xml'
        else:
            raise NotImplementedError('This module is available for html and xml formats')
        result = docx_ext_tornado(input_file=file_name,tags=tags[index],input_type=doc_type).extract()
        print(f'result length------>{len(result)}')
    return JsonResponse({'output': result})

# def dataset_to_mangodb(request):
#     from pymongo import MongoClient
#     client = MongoClient('172.28.42.150',27017)
#     db = client['dataset']
#     collection = db['general']
#     # data = [ferrero_header(category=i['category'], text=i['text'], language_code=i['language_code'],
#     #                     language=i['language'],
#     #                     category_actual=i['category_actual'],
#     #                     type=i['type']) for i in collection.find({})]
#     data = [general_dataset(category=i['category'], text=i['text'] , brand=i['brand'], domain=i['Domain']) for i in collection.find({})]
#     if data:
#         general_dataset.objects.bulk_create(data)
#         return HttpResponse('success')
#     else:
#         return HttpResponse('Failure')

from .coco_cola_pdf_processing import coco_cola
from .carrefour_excel_new_v2 import carrefour_main
from .goodman_fielder_excel_processing import main as gf
from .aldi_excel_processing import main as aldi
from .campbell_arnotts import arnott_main
from .pladis_pdf_processing import main as pladis_main
# from .woolsworth_pdf_processing import woolsworth_main ## This is only for sample response
from .kp import main as kp_main
# from .aldi_pdf import aldi_pdf_main ## This is only for sample response
from .woolsworth import woolsworth_main
from .aldi_pdf_new import aldi_page_routing
from .cocacola_docx import coke_main
from .pepsico_pdf import pepsico_pdf_main
from .beiersdorf import beiersdorf_main
from .fontem import fontem_main
from .bng_foods_pdf_image_processing import BG_FOODS as bng_foods
from .hormel_pdf_processing import Hormel_Processing as hp
from .albertson_amer_pdf_processing import albertson_amer_main
from .purina_excel import purina_main

class ai_hub(View):
    files,pages,sheets,account,location = None, None, None, None, None
    def get(self,request):
        final_output = {}
        self.files = request.GET.getlist('file', None)
        self.sheets = request.GET.getlist('sheet', None)
        self.pages = request.GET.getlist('pages', None)
        self.account = request.GET.get('account', None)
        self.location = request.GET.get('location', None)
        excel_count,pdf_count = 0,0
        print(self.files)
        for index , file in enumerate(self.files):
            output_response = {}
            doc_format = os.path.splitext(file)[1].lower()
            try:
                if doc_format == ".pdf":
                    output_response = self.pdf_processing(file,self.pages[pdf_count])
                    pdf_count = pdf_count + 1
                if doc_format == ".docx":
                    output_response = self.docx_processing(file)
                if doc_format in (".xlsx",".xlsm",".xls"):
                    output_response = self.excel_processing(file,self.sheets[excel_count])
                    excel_count = excel_count + 1
            except Exception as E:
                print("Error file name---->",file)
                Error = str(E)
                try:
                    logger(account_type="TORNADO", input_body=str(dict(request.GET)), output=str({"error":Error}),error=Error).save()
                except:
                    print("cant able to log error response")
                raise Exception(E)
            else:
                if not output_response:
                    try:
                        logger(account_type="TORNADO", input_body=str(dict(request.GET)),
                               output=str({"error": f"Input file {file} might be encrypted"}),
                               error=f"Input file {file} might be encrypted").save()
                    except:
                        print("cant able to log error response")
                    raise PermissionError(f"Input file {file} might be encrypted")
                final_output[file] = output_response

        try:
            logger(account_type="TORNADO", input_body=str(dict(request.GET)), output=str(final_output)).save()
        except:
            logger(account_type="TORNADO", input_body={"account": self.account, "file": self.files},
                   output=str(final_output),
                   error="file corrupted or naming issue").save()
            print("can't able to log . check db running or not")
        return JsonResponse(final_output)

    def pdf_processing(self,file,pages):
        pdf_accounts = {'mondelez':mp().main,'albertson':albertson_main,'nestle': Nestle_processing().routing, 'unilever': unilever_main,
                        'ferrero': ferrero_extraction().main,'magnum':Holanda_y_Magnum_main,'dg':Dollar_General().main,'gwf':gwf_main,
                        'coke':coco_cola().main,'campbellsarnotts':arnott_main,"pladis":pladis_main,"woolworths":woolsworth_main,
                        'aldiequator':aldi_page_routing,'pepsico':pepsico_pdf_main,'bng':bng_foods().main,"hormel":hp().main,
                        'sainsbury':sainsbury_main,'heinz':heinz_main,"albertsonamer":albertson_amer_main,"quaker":quaker_main}
        try:
            function = pdf_accounts[self.account.lower()]
        except:
            raise NotImplementedError(F"This {self.account} account is not yet implemented in single url functionality")
        return function(file,pages)

    def docx_processing(self,file):
        docx_accounts = {"mondelez":mondelez_mea_word_main,"generalmills":main_gm,"unilever":unilever_docx_main,"kp":kp_main,'coke':coke_main,
        				'conagra':conagra_main, 'mead_johnson':mead_final_main}
        try:
            function = docx_accounts[self.account.lower()]
        except:
            raise NotImplementedError(F"This {self.account} account is not yet implemented in single url functionality")
        return function(file)

    def excel_processing(self,file,sheets):
        excel_accounts = {'kelloggs':kelloggs_main,'gfs':gfs_main,'unilever':unilever_excel_main,
                          'carrefour':carrefour_main,'pepsico':pepsico_main,'aldi':aldi ,'goodmanfielder':gf,
                          'beiersdorf':beiersdorf_main,"fontem" :fontem_main, 'purina':purina_main}
        try:
            function = excel_accounts[self.account.lower()]
        except:
            raise NotImplementedError(F"This {self.account} account is not yet implemented in single url functionality")
        return function(file,sheets)

from .mongo_interface import MongoSearch
@csrf_exempt
def translate(request):
    json_response = request.body.decode('utf-8')    # string format
    print("json input------------->",json_response)
    json_response = re.sub(r'(?<=\\"Text\\":\\")(.*)(?=\\",)',lambda x: re.sub(r"[\"\']","",x.group(1)),json_response)
    json_response = re.sub(r'\\(\"|\')',lambda x:x.group(1),json_response)
    body = json.loads(json_response,strict=False)                #dict format
    mongo_data = MongoSearch(body["Text"],body["To_Lang"]).translate()
    if mongo_data:
        print("Getting input from Mongo DB")
        return JsonResponse({"translated_text":mongo_data})
    with GoogleTranslate(body,to_lang=body["To_Lang"]) as output:
        print("Getting data from Google API")
        return JsonResponse(output)

from .unilever_magnum import Holanda_y_Magnum_main
def magnum(request):
    overall_dict = {}
    files = request.GET.getlist('file', None)
    pages = request.GET.getlist('pages', None)
    for index,file in enumerate(files):
        response = Holanda_y_Magnum_main(file,pages[index])
        overall_dict[file] = response
    return JsonResponse(overall_dict)

from .gwf_pdf_processing import gwf_main
def gwf(request):
    overall_dict = {}
    files = request.GET.getlist('file', None)
    pages = request.GET.getlist('pages', None)
    print(files)
    for index,file in enumerate(files):
        response = gwf_main(file,pages[index])
        overall_dict[file] = response
    return JsonResponse(overall_dict)

from .nestle_sydney import main as nestle_sydney_main
def nestle_sydney(request):
    overall_dict = {}
    files = request.GET.getlist('file', None)
    pages = request.GET.getlist('pages', None)
    for index,file in enumerate(files):
        response = nestle_sydney_main(file,pages[index])
        overall_dict[file] = response
    return JsonResponse(overall_dict)
    
from .pepsico_excel_processing import main as pepsico_main
from .pepsico_xml_processing import xml_processing
def pepsico(request):
    final_dict = {}
    files = request.GET.getlist('file', None)
    sheets = request.GET.getlist('sheet', None)
    print(files,sheets)
    excel_count = 0
    response = {}
    for index,file in enumerate(files):
        doc_format = os.path.splitext(file)[1].lower()
        if doc_format == ".xml":
            response = xml_processing(file)
        elif doc_format in (".xlsx",".xlsm"):
            response = pepsico_main(file,sheets[excel_count])
            excel_count = excel_count + 1
        final_dict[file] = response
    return JsonResponse(final_dict)
    
from .coco_cola_pdf_processing import coco_cola
def coca_cola(request):
    overall_dict = {}
    files = request.GET.getlist('file', None)
    pages = request.GET.getlist('pages', None)
    for index,file in enumerate(files):
        response = coco_cola().main(file,pages[index])
        overall_dict[file] = response
    return JsonResponse(overall_dict)
    
from .mongo_interface import TornadoMongoSearch
def tornado_mongo_search(request):
    final_dictionary = {}
    start_date = request.GET.get("fromDate",None)
    end_date = request.GET.get("toDate",None)
    work_order_number = request.GET.get("wo",None)
    search_interface = TornadoMongoSearch()
    search_interface.start_date = start_date
    search_interface.end_date = end_date
    search_interface.work_order = work_order_number
    result = search_interface.search()
    if result:
        final_dictionary["status"] = "200"
        final_dictionary["data"] = result
    else:
        final_dictionary["status"] = "500"
        final_dictionary["data"] = []
    return JsonResponse(final_dictionary)

def annotation_capture(request):
    files = request.GET.getlist('file', None)  # list
    pages = request.GET.getlist('pages', None)  # list
    return JsonResponse(capture_annotations_for_n_files(files,pages))


