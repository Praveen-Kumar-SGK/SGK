import warnings
warnings.filterwarnings('ignore')
from bs4 import BeautifulSoup
from fuzzywuzzy import fuzz
import mammoth
from pdf2docx import parse
import warnings
warnings.filterwarnings('ignore')
import pdfplumber
import tempfile

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

from .excel_processing import *

##############################################################################################################################
######################################################## Test data ########################################################

# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/158 Burgen Sunflower and Linseed 660g DATASHEET_25032021.pdf'

# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/162 TT Sunblest Multigrain 650g SW DATASHEET 310321.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/163 TT Sunblest Multigrain Toast 650g DATASHEET 310321.pdf'

# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/183 Burgen Whole Grain and Oats 700g DATASHEET_26032021.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/235 Tip Top Texas Toast 700g DATASHEET_26032021.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/924 AB Sourdough Grains and Seeds 760g DATASHEET_24032021.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/925 AB Sourdough Rye 760g DATASHEET_24032021.pdf'

# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/4000 Golden Crumpet Rounds 300g 6 Pack DATASHEET_05112020 2.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/4000 Golden Crumpet Rounds 300g 6 Pack DATASHEET_05112020.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/4051 Golden Crumpet Squares 425g 6 Pack DATASHEET_05112020.pdf'
# pdf_file = '/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/PDF_location/4633 Golden Pancakes 360g 6 Pack DATASHEET_06112020.pdf'

##############################################################################################################################
##############################################################################################################################

def get_input(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location + input_pdf

def overall_dict(file_input, page,input_docx_location):
    general_classifier_model = joblib.load(gwf_general_model)
    # nutri_classifier_model = joblib.load(gwf_nutrition_model)
    nutri_classifier_model = joblib.load(master_nutrition_model_location)

    raw_data = []
    with pdfplumber.open(file_input) as pdf:
        page = pdf.pages[int(page) - 1]
        tables = page.extract_tables()

        for table_no in range(len(tables)):
            lst_value = tables[table_no]
            for i in lst_value:
                raw_data.append(list(filter(None.__ne__, i)))

    ###### NUTRITION EXTRACTION ######

    def Nutrition_data(source_nested_list):
        Nutrition_data = []
        Nutri_omit = []
        start = False
        for i in raw_data:
            if len(i[0]) > 300:
                if i[0] in i[0]:
                    Nutri_omit.append(i[0])
                    break
        for i in raw_data:
            if len(Nutri_omit) != 0:
                if i[0] == Nutri_omit[0]:
                    continue
                if 'approval' in i[0].lower():
                    start = True
                elif 'health star rating' in i[0].replace("\t"," ").lower():
                    start = False

                if start:
                    Nutrition_data.append(i)
            else:
                if 'nutrition information' in i[0].replace("\t"," ").lower():
                    start = True
                elif 'health star rating' in i[0].replace("\t"," ").lower():
                    start = False

                if start:
                    if "optional" in i[0].lower():
                        continue
                    Nutrition_data.append(i)

        if len(Nutrition_data) != 0:
            avg_index_num = []
            for i in range(len(Nutrition_data)):
                if 'energy' in Nutrition_data[i][0].lower():
                    avg_index_num.append(int(i))

            Nutrition_data_updated = []
            for i in avg_index_num:
                Nutrition_data_updated = Nutrition_data[i:]

            keys = []
            for i in Nutrition_data_updated:
                keys.append(i[0])

            nutrition_list_values = []
            for x in Nutrition_data_updated:
                nutrition_list_values.append([" ".join(x)])

            final_raw_nutriton_values = []
            for j in range(0, len(nutrition_list_values)):
                val_1 = []
                val_1.append(keys[j])
                snd = [i[0].strip() for i in
                       re.findall(r'(<?\s?(\d+)(\.\d+)?\s?(mg|kJ|g|kj|%|RDI†|mcg))', nutrition_list_values[j][0])]
                val_1.extend(snd)
                final_raw_nutriton_values.append(val_1)
        else:
            final_raw_nutriton_values = []
            Nutrition_data_updated = []

        return final_raw_nutriton_values, Nutrition_data_updated

    Nutrition_list, Nutrition_data_raw = Nutrition_data(raw_data)

    ###### NUTRITION PREDICTION ######

    def nutrition_predicted(Nutrition_list_data, classifier_model):
        nutri_predict = {}
        nutri_dict_values = {}

        for i in Nutrition_list:
            Xtest_laser = laser.embed_sentences(i[0], lang='en')
            item_res = classifier_model.predict(Xtest_laser)
            for j in i[1:]:
                j = j.replace('<', '&lt;').replace('>', '&gt;')
                if '%' in j:
                    if item_res[0] in nutri_dict_values:
                        nutri_dict_values[item_res[0]].append({'PDV': {'en': j.strip()}})
                    else:
                        nutri_dict_values[item_res[0]] = [{'PDV': {'en': j.strip()}}]
                else:
                    if item_res[0] in nutri_dict_values:
                        nutri_dict_values[item_res[0]].append({'Value': {'en': j.strip()}})
                    else:
                        nutri_dict_values[item_res[0]] = [{'Value': {'en': j.strip()}}]

        if len(nutri_dict_values) != 0:
            nutri_predict['NUTRITION_FACTS'] = [nutri_dict_values]
        else:
            nutri_predict = {}

        return nutri_predict

    Nutrition_dict = nutrition_predicted(Nutrition_list, nutri_classifier_model)

    ###### GENERAL EXTRACTION / PREDICTION ######

    def general_classifier(general_data, classifier_model):
        General_data = []
        for x in general_data:
            if x not in [i for i in Nutrition_data_raw]:
                General_data.append(x)

        general_dict = {}
        refined_dict = {}
        for i in General_data:
            for j in i:
                Xtest_laser = laser.embed_sentences(j, lang='en')
                item_res = general_classifier_model.predict(Xtest_laser)
                item_result = item_res[0]

                item_prob = general_classifier_model.predict_proba(Xtest_laser)
                item_prob[0].sort()
                prob = item_prob[0][-1]
                if prob >= 0.85:
                    classified_output = item_result
                else:
                    classified_output = 'None'

                if classified_output not in ['None', 'BRAND_NAME', 'PACKAGING_SAP_NUMBER',
                                             'GENERIC_NAME', 'FUNCTIONAL_NAME', 'NET_CONTENT_STATEMENT',
                                             'MANUFACTURER_NAME', 'MANUFACTURER_ADDRESS', 'NUTRITION_FACTS',
                                             'PER_SERVE', 'SERVING_SIZE', 'SERVINGS_PER_PACK',
                                             'MARKETING_CLAIM_1', 'MARKETING_CLAIM_2', 'MARKETING_CLAIM_3',
                                             'MARKETING_CLAIM_4', 'MARKETING_CLAIM_5']:

                    Xtest_laser_1 = laser.embed_sentences(j, lang='en')
                    item_res_1 = general_classifier_model.predict(Xtest_laser_1)
                    item_result_1 = item_res_1[0]

                    item_prob_1 = general_classifier_model.predict_proba(Xtest_laser_1)
                    item_prob_1[0].sort()
                    prob_1 = item_prob_1[0][-1]
                    if prob_1 >= 0.95:
                        classified_output_1 = item_result_1
                    else:
                        classified_output_1 = 'None'
                    j = str(j).replace("\t"," ")
                    j = str(j).replace('<', '&lt;').replace('>', '&gt;')
                    if classified_output_1 in refined_dict:
                        refined_dict[classified_output_1].append({classify(j)[0]: j.strip()})
                    else:
                        refined_dict[classified_output_1] = [{classify(j)[0]: j.strip()}]

                    if item_result in general_dict:
                        general_dict[item_result].append({classify(j)[0]: j.strip()})
                    else:
                        general_dict[item_result] = [{classify(j)[0]: j.strip()}]

        general_dict = {**general_dict, **refined_dict}

        return general_dict

    General_dict = general_classifier(raw_data, general_classifier_model)

    def marketing_classifier(general_data, classifier_model):
        Marketing_data = []
        for x in raw_data:
            Marketing_data.append(x)

        Marketing_dict = {}
        for i in Marketing_data:
            for j in i:
                j = j.replace('<', '&lt;').replace('>', '&gt;')
                j = j.split("\n")
                Xtest_laser = laser.embed_sentences(j[0], lang='en')
                item_res = general_classifier_model.predict(Xtest_laser)
                item_res = item_res[0]
                item_prob = general_classifier_model.predict_proba(Xtest_laser)
                item_prob[0].sort()
                prob = item_prob[0][-1]
                if prob >= 0.85:
                    classified_output = item_res
                else:
                    classified_output = 'None'

                if len(i) > 1:
                    i = i[1:]
                if classified_output in ["MARKETING_CLAIM_1", "MARKETING_CLAIM_2", "MARKETING_CLAIM_3",
                                         "MARKETING_CLAIM_4", "MARKETING_CLAIM_5"]:
                    classified_output = "MARKETING_CLAIM"
                    content = str(i[0]).strip()
                    content = content.replace("\t"," ")
                    if classified_output in Marketing_dict:
                        Marketing_dict[classified_output].append({classify(content)[0]: content})
                    else:
                        Marketing_dict[classified_output] = [{classify(content)[0]: content}]

        return Marketing_dict

    Marketing_dict = marketing_classifier(raw_data, general_classifier_model)

    ###### HEADER EXTRACTION / PREDICTION ######

    def header_classifier(general_data, classifier_model):
        header_dict = {}
        for i in raw_data:
            print("gggggggg---------->",i)
            for j in i:
                Xtest_laser = laser.embed_sentences(j, lang='en')
                item_res = general_classifier_model.predict(Xtest_laser)
                item_result_head = item_res[0]
                item_prob = general_classifier_model.predict_proba(Xtest_laser)
                item_prob[0].sort()
                prob = item_prob[0][-1]
                if prob >= 0.80:
                    classified_output = item_result_head
                else:
                    classified_output = 'None'

                if classified_output in ['BRAND_NAME', 'PACKAGING_SAP_NUMBER',
                                         'GENERIC_NAME', 'FUNCTIONAL_NAME', 'NET_CONTENT_STATEMENT',
                                         'MANUFACTURER_NAME', 'MANUFACTURER_ADDRESS']:
                    content = str(i[1:][0]).strip()
                    content = re.sub("\t"," ",content)
                    content = content.replace('<', '&lt;').replace('>', '&gt;')
                    print("hello----->",str(j))
                    if item_result_head in header_dict:
                        header_dict[item_result_head].append({classify(content)[0]: content})
                    else:
                        header_dict[item_result_head] = [{classify(content)[0]: content}]

        return header_dict

    Header_dict = header_classifier(raw_data, general_classifier_model)

    ###### SERVING EXTRACTION / PREDICTION ######

    # def serving_classifier(general_data, classifier_model):
    #     serve_keys = ['servings per pack', 'serving size', 'per serve']
    #     serve_keys_base = []
    #     serve_values = []
    #     serve_values_combined = []
    #     serve_bool = False
    #     for i in raw_data:
    #         for j in i:
    #             if 'nutrition information' in j.lower():
    #                 j = j.split('\n')
    #                 j = j[1:]
    #                 for k in j:
    #                     serve_values_combined.append(" ".join(k.split(',')))
    #                 serve_bool = True
    #                 break
    #
    #             if j.lower() in serve_keys:
    #                 serve_keys_base.append(["".join(i[0])])
    #                 serve_values.append([" ".join(i[1:])])
    #
    #     serve_values_combined_fin = []
    #     serve_values_combined_fin_keys = []
    #     if len(serve_keys_base) != 0:
    #         if serve_bool:
    #             for i in serve_values_combined:
    #                 i = i.split(':')
    #                 serve_values_combined_fin_keys.append(i[0])
    #                 i = i[1:]
    #                 for j in i:
    #                     j = j.strip()
    #                     serve_values_combined_fin.append((j.split('\n')))
    #
    #         serving_values = []
    #         if len(serve_values) > 0:
    #             for i in serve_values:
    #                 for j in i:
    #                     j = j.replace('<', '&lt;').replace('>', '&gt;')
    #                     serving_values.append([{'en': j.strip()}])
    #         else:
    #             for i in serve_values_combined_fin:
    #                 for j in i:
    #                     j = j.replace('<', '&lt;').replace('>', '&gt;')
    #                     serving_values.append([{'en': j.strip()}])
    #
    #         serving_final_keys = []
    #
    #         if len(serve_values_combined_fin_keys) > 0:
    #             for i in serve_values_combined_fin_keys:
    #                 Xtest_laser = laser.embed_sentences(i, lang='en')
    #                 item_res = general_classifier_model.predict(Xtest_laser)
    #                 item_result = item_res[0]
    #                 serving_final_keys.append([item_result])
    #
    #         else:
    #             for i in serve_keys_base:
    #                 Xtest_laser = laser.embed_sentences(i, lang='en')
    #                 item_res = general_classifier_model.predict(Xtest_laser)
    #                 item_result = item_res[0]
    #                 serving_final_keys.append([item_result])
    #
    #         assert (len(serving_final_keys) == len(serving_values))
    #         output_dict = dict()
    #         for index in range(len(serving_final_keys)):
    #             output_dict[serving_final_keys[index][0]] = serving_values[index]
    #     else:
    #         output_dict = dict()
    #     return output_dict

    def serving_classifier(general_data, classifier_model):
        serve_keys = ['servings per pack', 'serving size', 'per serve']
        serve_keys_base = []
        serve_values = []
        serve_values_combined = []
        serve_bool = False
        for i in general_data:
            for j in i:
                if 'nutrition information' in j.lower():
                    j = j.split('\n')
                    j = j[1:]
                    for k in j:
                        serve_values_combined.append(" ".join(k.split(',')))
                    serve_bool = True
                    break

                if j.lower() in serve_keys:
                    serve_keys_base.append(["".join(i[0])])
                    serve_values.append([" ".join(i[1:])])

        serving_final_keys = []
        serving_values = []
        serve_values_combined_fin = []
        serve_values_combined_fin_keys = []
        if len(serve_keys_base) == 0:
            if serve_bool:
                for i in serve_values_combined:
                    i = i.split(':')
                    serve_values_combined_fin_keys.append(i[0])
                    i = i[1:]
                    for j in i:
                        j = j.strip()
                        j = j.replace('<', '&lt;').replace('>', '&gt;')
                        serve_values_combined_fin.append((j.split('\n')))
                        serving_values.append([{'en': j.strip()}])

                if len(serve_values_combined_fin_keys) > 0:
                    for i in serve_values_combined_fin_keys:
                        for j in i.split(','):
                            Xtest_laser = laser.embed_sentences(j, lang='en')
                            item_res = general_classifier_model.predict(Xtest_laser)
                            item_result = item_res[0]
                            serving_final_keys.append([item_result])

            assert (len(serving_final_keys) == len(serving_values))
            output_dict = dict()
            for index in range(len(serving_final_keys)):
                output_dict[serving_final_keys[index][0]] = serving_values[index]

        elif len(serve_keys_base) != 0:
            for i in serve_values:
                for j in i:
                    j = j.replace('<', '&lt;').replace('>', '&gt;')
                    serving_values.append([{'en': j.strip()}])
            else:
                for i in serve_keys_base:
                    Xtest_laser = laser.embed_sentences(i, lang='en')
                    item_res = general_classifier_model.predict(Xtest_laser)
                    item_result = item_res[0]
                    serving_final_keys.append([item_result])

            assert (len(serving_final_keys) == len(serving_values))
            output_dict = dict()
            for index in range(len(serving_final_keys)):
                output_dict[serving_final_keys[index][0]] = serving_values[index]
        else:
            output_dict = dict()
        return output_dict

    Serving_dict = serving_classifier(raw_data, general_classifier_model)

    combined_dict = {**Header_dict, **General_dict, **Marketing_dict, **Serving_dict, **Nutrition_dict}

    combined_dict = {key: val for key, val in combined_dict.items() if key != 'None'}

    def bold_dict(general_data, classifier_model):

        def pdf2docx_pdf_html(input_pdf,input_docx_location):
            # docx_name = r"/Users/vigneshramamurthy/opt/anaconda3/Workscripts/Spyder/Sprint 2.21 -  Mexico Unilever, Sydney Chennai, APAC Pepsico Penang, APAC Sydeny:Chennai /Accounts/GWF/Script/Word_location/Test/xx.docx"
            parse(input_pdf, input_docx_location)
            # parse(input_pdf, docx_name, start=page_no - 1, end=page_no)
            x = mammoth.convert_to_html(input_docx_location, style_map="b => b").value
            html = BeautifulSoup(x, 'html.parser')
            return html

        soup = pdf2docx_pdf_html(file_input,input_docx_location)

        content_list = []

        for div in soup.find_all("p"):
            content_list.append(str(div))

        def search_bold_content(text):
            score_dict = {}
            for index, div_text in enumerate(content_list):
                score = fuzz.ratio(text, re.sub("<.*?>", "", div_text))
                if score > 30:
                    temp_score_recur, upto_index_recur = recursive(content_list, index, score, div_text,
                                                                   text).try_recursion()
                    # print(index,upto_index_recur)
                    score_dict[temp_score_recur] = " ".join(content_list[index:upto_index_recur + 1])

            if score_dict and max(score_dict) > 80:
                return score_dict[max(score_dict)]

        class recursive(object):
            def __init__(self, _list, index, score, text, src_text):
                self.score = score
                self.index = index
                self._list = _list
                self.text = text
                self.src_text = src_text

            def try_recursion(self):
                combine_next_seg = lambda x: ''.join((self.text, self._list[x + 1]))  # one line function
                temp_text = combine_next_seg(self.index)
                temp_score = fuzz.ratio(re.sub("<.*?>", "", temp_text.lower()), self.src_text.lower())
                if temp_score > self.score:
                    self.score = temp_score
                    self.index = self.index + 1
                    self.text = temp_text
                    self.try_recursion()
                # print(f"return value ========>{self.score}---->{self.index}")
                return self.score, self.index

        bold_dict_final = {}
        content_raw = []

        for i in general_data:
            i = i[1:]
            for j in i:
                try:
                    temp = search_bold_content(j)
                    temp = temp.split("\n")
                    content_raw.append(temp)
                except:
                    pass

        for i in content_raw:
            if i is None:
                continue
            for j in i:
                if "<b>" not in j:
                    continue
                Xtest_laser = laser.embed_sentences(j.replace('<b>', '').replace('</b>', ''), lang='en')
                item_res = classifier_model.predict(Xtest_laser)
                item_prob_1 = classifier_model.predict_proba(Xtest_laser)
                item_prob_1[0].sort()
                prob_1 = item_prob_1[0][-1]

                if prob_1 >= 0.75:
                    classified_output = item_res[0]
                else:
                    classified_output = 'None'

                    # j = j.replace('<(?!\/?b).*?>', '')
                # print("hello------>",repr(j))
                j = re.sub(r'\t',' ', str(j))
                # print("cleaned------->",repr(j))
                j = re.sub(r'<(?!\/?b).*?>', '', str(j))
                # j = j.replace('<p>', '').replace('</p>', '')
                j = j.replace('<', '&lt;').replace('>', '&gt;')

                if classified_output in bold_dict_final:
                    bold_dict_final[classified_output].append({classify(j)[0]: j.strip()})
                else:
                    bold_dict_final[classified_output] = [{classify(j)[0]: j.strip()}]

        bold_dict_final = {key: val for key, val in bold_dict_final.items() if key != 'None'}
        return bold_dict_final

    bold_dict = bold_dict(raw_data, general_classifier_model)

    return combined_dict, bold_dict

def gwf_main(file_input,page_nos):
    page_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    input_docx_location = f'{temp_directory.name}/input.docx'
    file_input = get_input(file_input,input_pdf_location)
    pdf = pdfplumber.open(file_input)
    for page_no in page_nos.split(','):
        if int(page_no) - 1 in range(len(pdf.pages)):
            d, check_bold_dict = overall_dict(file_input, int(page_no),input_docx_location)
            res = {key: check_bold_dict.get(key, d[key]) for key in d}
            page_dict[str(page_no)] = res
    return page_dict

#no need -- to run on console
# gwf_dict = gwf_main(pdf_file)
# print(gwf_dict)