from django.shortcuts import render
from . import views
from django.urls import path, include , re_path
from rest_framework.authtoken.views import obtain_auth_token
from django.views.generic.base import RedirectView
from django.contrib import admin
from django.views.generic import TemplateView
from django.conf.urls import include, url
from django.views.static import serve


urlpatterns = [
    # re_path(r"home\/$", views.home, name='home'),
    re_path(r"msd\/$", views.msd, name='msd'),
    re_path(r"az\/$", views.astrazeneca, name='az'),
    re_path(r"ai\/$", views.ai_hub.as_view(), name='ai'),
    re_path(r"gm\/$", views.general_mills_hd, name='general_mills'),
    re_path(r"carrefour_excel\/$", views.carrefour_excel, name='carrefour_excel'),
    re_path(r"unilever_excel\/$", views.unilever_excel, name='unilever_excel'),
    re_path(r"unilever\/$", views.unilever, name='unilever_hybrid'),
    re_path(r"ferrero\/$", views.ferrero, name='ferrero'),
    re_path(r"coca_cola\/$", views.coca_cola, name='coco_cola'),
    re_path(r"excel_extraction\/$", views.excel_extraction, name='excel_extraction'),
    re_path(r"kellogs_extraction\/$", views.kelloggs_extraction, name='kellogs_extraction'),
    re_path(r"dg\/$", views.dollar_general, name='dollar_general'),
    re_path(r"nestle\/$", views.nestle, name='nestle'),
    re_path(r"albertson\/$", views.albertson, name='alertson'),
    re_path(r"mondelez_word\/$", views.mondelez_word, name='mondelez_word'),
    re_path(r"mondelez_pdf\/$", views.mondelez_pdf, name='mondelez_pdf'),
    re_path(r"griesson\/$", views.griesson, name='griesson'),
    re_path(r"nestle_sydney\/$", views.nestle_sydney, name='nestle_sydney'),
    re_path(r"magnum\/$", views.magnum, name='magnum'),
    re_path(r"gwf\/$", views.gwf, name='gwf'),
    re_path(r"pepsico\/$", views.pepsico, name='pepsico'),
    re_path(r"carrefour_cep\/$", views.carrefour, name='carrefour_cep'),
    re_path(r"docx_tornado_extractor\/$", views.docx_tag_content_extractor_for_tornado, name='docx_extractor_for_tornado'),
    re_path(r"getTyphoonLang\/$", views.tornado_mongo_search, name='tornado_mongo_search'),
    # re_path(r"classifier\/$", views.classifier, name='classifier'),
    # path("extractor/", views.extractor, name='extractor'),
    # re_path(r"doc_extractor\/$",views.doc_extractor,name='doc_extractor'),
    re_path(r"lang_detect\/$",views.language_detection,name='lang_detect'),
    re_path(r"google_api\/translate/$",views.translate,name='google_api'),
    re_path(r"api_token\/$",obtain_auth_token,name='auth_token'),
    # re_path(r"dataset_update\/$",views.dataset_to_mangodb,name='dataset_update'),
    re_path(r"jnj_cep\/$", views.j_and_j, name='jnj_cep'),
    re_path(r"henkel_cep\/$", views.henkal_cep, name='henkal_cep'),
    re_path(r"ferrero_cep\/$", views.ferrero_cep, name='ferrero_cep'),
    re_path(r"beiersdorf\/$", views.beiersdorf_cep, name='beiersdorf_cep'),
    re_path(r"kimberly_cep\/$", views.kimberly_cep, name='kimberly_cep'),
    re_path(r"cocacola_cep\/$", views.cocacola_cep, name='cocacola_cep'),
    re_path(r"pepsi_cep\/$", views.pepsi_cep, name='pepsi_cep'),
    re_path(r"home_and_laundry_cep\/$", views.home_and_laundry_cep, name='home_and_laundry_cep'),
    re_path(r"jnj_listerine_cep\/$", views.jnj_listerine_cep_view, name='jnj_listerine_cep'),
    re_path(r"mondelez_cep\/$", views.mondelez_cep_view, name='mondelez_cep'),
    re_path(r"ai\/capture_annotation\/$", views.annotation_capture, name='annotation_capture'),
]



