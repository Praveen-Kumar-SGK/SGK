# Constants
path_to_bpe_codes = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Laser/93langs.fcodes"
path_to_bpe_vocab = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Laser/93langs.fvocab"
path_to_encoder = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Laser/bilstm.93langs.2018-12-26.pt"
document_location = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/"

#language model
whatlangid_model = r'/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/fasttext_model/lid.176.ftz'

#General
input_excel = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/dataset.xlsx"
model_location = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/model.pkl"

#MSD Project
msd_input_excel = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/MSD_dataset.xlsx"
msd_model_location = r"/Users/VIJAYKANAGARAJ/PycharmProjects/Schawk_document_xml/Dataset/model_msd.pkl"

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

regex_heading_msd = r"\d\.[\t\s]|\<li\>"

# avail language option for categories
msd_categories_lang = ['form_content','method_route','warning',
                       'storage_instructions','precautions',
                       'usage_instruction','braille_info',
                       'product_info','label_dosage','box_info','classification',
                       'method_route',
                       ]

msd_categories_lang_exception = ['excipients','active_substance','name','marketing_company','manufacturer']

# For excel processing
excel_data_exclusion = ['None','design instruction','others']