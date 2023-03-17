#Constants
# google_api_creds = r"/home/vijay/doc_extractor/model_dataset/google_api/translate-api-324204-30c08f7758c1.json"
google_api_creds = r"/home/vijay/doc_extractor/model_dataset/google_api/translate-api-new.json"

# laser_base_directory = r"/home/vijay/pretrained_models/"
path_to_bpe_codes = r"/home/vijay/pretrained_models/Laser/93langs.fcodes"
path_to_bpe_vocab = r"/home/vijay/pretrained_models/Laser/93langs.fvocab"
path_to_encoder = r"/home/vijay/pretrained_models/Laser/bilstm.93langs.2018-12-26.pt"
document_location = r"/home/vijay/doc_extractor/model_dataset/"

#LaBSE Model
labse_location = r""

#language model
whatlangid_model = r'/home/vijay/pretrained_models/whatlangid/lid.176.ftz'

# General
input_excel = r"/home/vijay/doc_extractor/model_dataset/dataset.xlsx"
model_location = r"/home/vijay/doc_extractor/model_dataset/model.pkl"

#MSD Project
msd_input_excel = r"/home/vijay/doc_extractor/model_dataset/MSD_dataset.xlsx"
msd_model_location = r"/home/vijay/doc_extractor/model_dataset/model_msd.pkl"
msd_content_model_location = r"/home/vijay/doc_extractor/model_dataset/model_msd_content.pkl"

# creds for SMB share
smb_username = 'weblogic'
smb_password = "417@sia123"

#Regex_patterns
regex_patterns = {
"GTIN_number" : r"(?<=GTIN:)(\s?[\-0-9]*)(?=)",
"serial_number" : r"(?<=SN:)(\s?[\-0-9]*)(?=)",
"lot_number" : r"(?<=Lot.:)(\s?[\-0-9]*)(?=)",
"Expiry_date" : r"(?<=Exp.:)(\s?[\-\.0-9]*)(?=)",
"PC_number" : r"(?<=PC:)(\s?[\-\.0-9]*)(?=)",
"PC" : r"(?<=PC)(\s?[\-\.0-9]*)(?=)",
"EU_number" : r"EU[\/\d]*$",
}

# regex_heading_msd = r"[\d\.]\t"
regex_heading_msd = r"\d\.[\t\s]|\<li\>"

msd_categories_lang = ['form_content','method_route','warning',
                       'storage_instructions','precautions',
                       'usage_instruction','braille_info',
                       'product_info','label_dosage','box_info','classification',
                       'method_route',
                       ]

msd_categories_lang_exception = ['excipients','active_substance','name','marketing_company','manufacturer']

# For excel processing
excel_data_exclusion = ['None','design instruction','others']

# excel_data_model

excel_model_location = r"/home/vijay/doc_extractor/model_dataset/excel_model.pkl"
excel_model_location_new = r"/home/vijay/doc_extractor/model_dataset/finalized_model.sav"
excel_input_dataset = r"/home/vijay/doc_extractor/model_dataset/Excel_DataSet.xlsx"
excel_main_dataset = r"/home/vijay/doc_extractor/model_dataset/Excel DataSet.xlsx"
kelloggs_model = r'/home/vijay/doc_extractor/model_dataset/kelloggs_model.sav'

# Ferrero Model

ferrero_header_model = r"/home/vijay/doc_extractor/model_dataset/ferrero_header_model.pkl"

# Nestle Model

nestle_model_location = r"/home/vijay/doc_extractor/model_dataset/Nestle_model.pkl"
nestle_model_dataset = r"/home/vijay/doc_extractor/model_dataset/Nestle_dataset.xlsx"

# Griesson Model

griesson_model_location = r"/home/vijay/doc_extractor/model_dataset/Griesson_model.pkl"
griesson_model_dataset = r"/home/vijay/doc_extractor/model_dataset/Griesson_dataset.xlsx"

# General mills
GM_HD_model_dataset = r"/home/vijay/doc_extractor/model_dataset/GM_HD_headers_dataset.xlsx"
GM_HD_model_location = r"/home/vijay/doc_extractor/model_dataset/GM_HD_model.pkl"

#carrefour model
# carrefour_model_location = r"/home/vijay/doc_extractor/model_dataset/carrefour_excel_model.sav"
carrefour_model_location = r"/home/vijay/doc_extractor/model_dataset/carrefour_excel_model.pkl"

#carrefour cep model (Illustrator file)
# carrefour_CEP_model_location = r"/home/vijay/doc_extractor/model_dataset/carrefour_cep_model.sav"
carrefour_CEP_model_location = r"/home/vijay/doc_extractor/model_dataset/Carfour_cep_Model (1).pkl"

#mondelez word model
# mondelez_word_model_location_old = r"/home/vijay/doc_extractor/model_dataset/mondelez_word_model.sav"
mondelez_word_model_location = r"/home/vijay/doc_extractor/model_dataset/mondelez_word_gen_cate_model.pkl"
mondelez_word_nutrition_model_location = r"/home/vijay/doc_extractor/model_dataset/mondelez_word_nutri_cate_model.sav"

#mindelez pdf model
mondelez_pdf_general_model_location = r"/home/vijay/doc_extractor/model_dataset/mondelez_general_model.pkl"
mondelez_pdf_model_location = r"/home/vijay/doc_extractor/model_dataset/mondelez_model.pkl"
mondelez_dataset = r"/home/vijay/doc_extractor/model_dataset/mondelez_dataset.xlsx"
mondelez_pdf_plr_model_location = r"/home/vijay/doc_extractor/model_dataset/mondelz_plr_model.sav"
mondelez_pdf_plr_nutrition_model_location = r"/home/vijay/doc_extractor/model_dataset/mondelez_plr_master_nutrition_model.sav"

# unilever docx model
unilever_docx_model_location = r"/home/vijay/doc_extractor/model_dataset/unilever_docx_model.sav"
# unilever_docx_dataset = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/mondelez_dataset.xlsx"

# unilever pdf model location
unilever_pdf_model_location = r"/home/vijay/doc_extractor/model_dataset/Unilever_pdf_model.pkl"

# Nestle sydney model location
nestle_sydney_location = r"/home/vijay/doc_extractor/model_dataset/nestle_sydney_pdf.pkl"

# Magnum_unilever
magnum_general_model = r"/home/vijay/doc_extractor/model_dataset/General_Magnum.pkl"
magnum_nutrition_model = r"/home/vijay/doc_extractor/model_dataset/Nutrition_Magnum.pkl"

# Gwf models
# gwf_general_model = r"/home/vijay/doc_extractor/model_dataset/overall_model.pkl"
gwf_general_model = r"/home/vijay/doc_extractor/model_dataset/overall_model_mark_test.pkl"
gwf_nutrition_model = r"/home/vijay/doc_extractor/model_dataset/nutri_model.pkl"

#master_nutrition_model
master_nutrition_model_location = r"/home/vijay/doc_extractor/model_dataset/master_nutrition.pkl"
master_nutrition_dataset_location = r"/home/vijay/doc_extractor/model_dataset/Master Nutrition Dataset.xlsx"

# Ferrero_F8_models
ferrero_f8_model_location = r"/home/vijay/doc_extractor/model_dataset/ferrero_F8_general.pkl"
ferrero_f8_nutrition_model_location = r"/home/vijay/doc_extractor/model_dataset/ferrero_F8_nutrition_model.pkl"

ferrero_header_model_gm = r"/home/vijay/doc_extractor/model_dataset/ferrero_header_model_gm.pkl"      # for general mills only

# coca-cola models
coca_cola_model = r"/home/vijay/doc_extractor/model_dataset/coca_cola_model.pkl"

#Nestle_china models
nestle_china_model = r"/home/vijay/doc_extractor/model_dataset/nestle_china_model.pkl"

#Goofman Fielder model location
goodman_fielder_model = r"/home/vijay/doc_extractor/model_dataset/Goodman.sav"

# Campbell_arnotts model location
campbell_arnotts_model = r"/home/vijay/doc_extractor/model_dataset/arnotts_model.sav"
campbell_arnotts_nutrition_model = r"/home/vijay/doc_extractor/model_dataset/arnotts_master_nutri_model.pkl"

#pladis
pladis_model = r"/home/vijay/doc_extractor/model_dataset/pladis.sav"

# # kp_model_location
kp_model_location = r"/home/vijay/doc_extractor/model_dataset/KP_snacks.sav"

## woolsworth_model_location
woolswoth_gen_model = r"/home/vijay/doc_extractor/model_dataset/woolworth_General.pkl"
woolswoth_nutri_model = r"/home/vijay/doc_extractor/model_dataset/woolworth_Nutrition.pkl"
woolsworth_gen_model_from_sainsbury = r"/home/vijay/doc_extractor/model_dataset/woolsworth_gen_model.sav"

## aldi_pdf_model_location
aldi_pdf_model =  r"/home/vijay/doc_extractor/model_dataset/Aldi.sav"

## cocacola_docx_model_location
cocacola_docx_model_location =  r"/home/vijay/doc_extractor/model_dataset/Coke.sav"

## pepsico_pdf_model_location
pepsico_general_model = r"/home/vijay/doc_extractor/model_dataset/pepsico_general_model.pkl"
pepsico_nutrition_model = r"/home/vijay/doc_extractor/model_dataset/pepsico_nutrition_model.sav"

## Beirsdorf_model_location
beiersdorf_model_location = r"/home/vijay/doc_extractor/model_dataset/Beiersdorf_model.pkl"

## Fontem_model_location
fontem_model_location = r"/home/vijay/doc_extractor/model_dataset/FONTEM_PICKLE.sav"

## J_andJ_model_location
jnj_model_location = r"/home/vijay/doc_extractor/model_dataset/j_and_j_model.sav"

## Henakl_CEP_model_location
henkal_model_location = r"/home/vijay/doc_extractor/model_dataset/henkal_cep_model.sav"

##Conagra_model_location
conagra_model_location = r"/home/vijay/doc_extractor/model_dataset/Conagra_model.sav"

## ferrero_cep_model_location
ferrero_cep_model_location = r"/home/vijay/doc_extractor/model_dataset/ferrero_cep_model.sav"

## sainsbury_model_location
sainsbury_model_location = r"/home/vijay/doc_extractor/model_dataset/sainsbury_gen_model.sav"
sainsbury_nutri_model_location = r"/home/vijay/doc_extractor/model_dataset/master_nutrition_sainsbury_model.sav"

## Heinz_model_location
heinz_model_location = r"/home/vijay/doc_extractor/model_dataset/Heinz_model.sav"

## Beiersdorf_cep_model_loc
beiersdorf_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/beiersdorf_cep_model.sav"

## Kimberly_cep_model_loc
kimberly_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/kimberly_cep_model.sav"

## Cocacola_cep_model_loc
cocacola_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/cep_cola_model.sav"

## Peppsi_cep_model_loc
pepsi_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/pepsico_cep.sav"

## Home_and_Laundry_cep_model_loc
home_and_laundry_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/home_and_laundry_cep.sav"

## jnj_listerine_cep_model_loc
listerine_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/JnJ_Listerine_cep.sav"

## mondelez_cep_model_loc
mondelez_cep_model_loc = r"/home/vijay/doc_extractor/model_dataset/mondelez_cep.sav"

## mondelez_mea_plus_older_regions_model
mond_gen_model = r"/home/vijay/doc_extractor/model_dataset/mond_gen_model.sav"
mond_nutri_model = r"/home/vijay/doc_extractor/model_dataset/mond_nut_model.sav"
