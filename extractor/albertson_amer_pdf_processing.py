from pdf2image import convert_from_path
import tempfile
import pandas as pd
import cv2
import numpy as np
import imutils
import pdfplumber
import camelot
# from tabulate import tabulate
import re
from collections import Counter
import joblib
import smbclient
from fuzzywuzzy import fuzz


from .excel_processing import smb_password,smb_username,laser,classify,model_location,document_location

# path_to_bpe_codes = r"/Users/vijaykanagaraj/PycharmProjects/pre_trained_models/Laser/93langs.fcodes"
# path_to_bpe_vocab = r"/Users/vijaykanagaraj/PycharmProjects/pre_trained_models/Laser/93langs.fvocab"
# path_to_encoder = r"/Users/vijaykanagaraj/PycharmProjects/pre_trained_models/Laser/bilstm.93langs.2018-12-26.pt"
# laser = Laser(path_to_bpe_codes,path_to_bpe_vocab,path_to_encoder)

# input_pdf = f"FLC-8108-6057-0-21130-13676-SC-Meat Lovers Pizza 40.2oz-NATIONS-V1.pdf"
# input_pdf = f"FLC-5215-5898-0-21130-17475-SC-CoconutMilkHairConditioner-13floz-Apollo-V1.pdf"
# input_pdf = f"FLC-8202-5773-0-21130-14773-SR-GIRASOLI WITH GORGONZOLA AND WALNUT-BERTAGNI-V1.pdf"
# input_pdf = f"FLC-8466-5785-0-2113013258-Signature Farms-S FARMS VEGGIE TRAY W_DIP-40OZ-BRAGA-V1.pdf"

temp_directory = tempfile.TemporaryDirectory(dir=document_location)
classifier = joblib.load(model_location)

is_df_with_multiple_columns = lambda table,threshold: True if any([True for row in table if len(row) > threshold]) or len([True for row in table if len(row) > 1]) > threshold else False

chunk_condition = {"SLIC DETAILS":"SLIC DETAILS",
                   "SUPERSESSION":"SUPERSESSION",
                   "BRAND DETAILS":"This section to be completed by OWN BRANDS",
                   "SUPPLIER DETAILS":"COMPANY CONTACT INFORMATION",
                   # "SUPPLIER DETAILS":"This section to be completed by SUPPLIER",
                   "PRODUCT INFORMATION":"PRODUCT INFORMATION",
                   "FLAVOR INFORMATION":"FLAVOR INFORMATION",
                   "PRODUCT HANDLING":"PRODUCT HANDLING",
                   "OTHER":"OTHER",
                   "PROP65 INFORMATION":"PROP65 INFORMATION",
                   "PACKAGING INFORMATION":"PACKAGING INFORMATION",
                   "COUNTRY OF ORIGIN":"COUNTRY OF ORIGIN",
                   "PRODUCT SPECIFIC INFORMATION":"PRODUCT SPECIFIC REQUIRED INFORMATION",
                   "CLAIM INFORMATION":"THIRD PARTY CLAIMS",
                   "WARNING":"HAZARDS & WARNINGS",
                   "INGREDIENT DETAILS":"INGREDIENT STATEMENT",
                   "ALLERGEN DETAILS":"ALLERGEN DETAILS",
                   "ALLERGEN STATEMENT":"ALLERGEN STATEMENT",
                   "NUTRITION FACTS INFORMATION": "FACTS PANEL INFORMATION",
                   "NUTRITION FACTS":"FACTS PANEL",
                   "PREPARATION INSTRUCTIONS":"PREP. INSTRUCTIONS AND RECIPE"
                   }

manual_mapper_dict = {"BRAND_NAME":["^BRAND"],
                      "VARIANT":["LEGAL PRODUCT NAME"],
                      "FUNCTIONAL_NAME":["PRODUCT DESCRIPTOR"],
                      "NET_CONTENT_STATEMENT":["RETAIL UNIT NET CONTENT"],
                      "OTHER_INSTRUCTIONS":["HANDLING STATEMENT","DIRECTIONS FOR USE","COOK INSTRUCTIONS","YES","OTHER MANDATORY","Other","Directions"],
                      "LOCATION_OF_ORIGIN":["COUNTRY OF ORIGIN:","COUNTRY OF ORIGIN STATEMENT"],
                      # "MARKETING_CLAIM":["YES"],
                      "ALLERGEN_STATEMENT":["CONTAINS STATEMENT","MAY CONTAIN STATEMENT"],
                      "SERVING_SIZE":["SERVING SIZE"],
                      "NUMBER_OF_SERVINGS_PER_PACKAGE":["SERVINGS PER CONTAINER"],
                      "COPYRIGHT_TRADEMARK_STATEMENT":["COPYRIGHT STATEMENTS"],

                      }

# ["ingredients","marketing claim","warning statement","usage instruction","storage instruction"]
key_mapper = {"ingredients":"INGREDIENTS_DECLARATION",
              "marketing claim":"OTHER_INSTRUCTIONS",
              "usage instruction":"OTHER_INSTRUCTIONS",
              "storage instruction":"OTHER_INSTRUCTIONS",
              "warning statement":"WARNING_STATEMENTS",
              }

def pdf_to_image(input_pdf,location):
    images = convert_from_path(input_pdf)
    for index, image in enumerate(images):
        image.save(f'{location}/{index + 1}.png')
    return 'success'

def image_processing(img,h_buffer=210,v_buffer=13):
    input_img = cv2.imread(img)
    # plt.imshow(input_img)
    kernal_h = np.ones((1, h_buffer), np.uint8)
    kernal_v = np.ones((v_buffer, 1), np.uint8)

    de_img = cv2.GaussianBlur(input_img, (5,5),0)
    img_bin_h = cv2.morphologyEx(de_img, cv2.MORPH_OPEN, kernal_h)
    img_bin_v = cv2.morphologyEx(de_img, cv2.MORPH_OPEN, kernal_v)
    img = img_bin_v + img_bin_h
    lap = cv2.Laplacian(img,ddepth=cv2.CV_16S,ksize=1)
    lap[np.any(lap != [0, 0, 0], axis=-1)] = [255,255,255]
    threshold = np.uint8(cv2.threshold(lap, 250, 255, cv2.THRESH_BINARY)[1])    # converted to int8 format
    gray_scale = cv2.cvtColor(threshold, cv2.COLOR_BGR2GRAY)
    return gray_scale

def find_contours(image,tree=None,area=15000):
    height = image.shape[0]
    width = image.shape[1]
    if not tree:
        cnts = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    else:
        cnts = cv2.findContours(image.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts1 = imutils.grab_contours(cnts)
    cnts2 = [cnt for cnt in cnts1 if cv2.contourArea(cnt)]
    i = 0
    for contour in cnts2:
        if cv2.contourArea(contour) > area:                 # 4000 for lase footer subject localization ...normal : 50000
            x, y, w, h = cv2.boundingRect(contour)
            i = i + 1
            yield (width / (x - 10), height / (y - 10), width / (x + w + 20), height / (y + h + 30))

def content_within_bounding_box_camelot(input_pdf,page_no,normalized_contour):
    pdf = pdfplumber.open(input_pdf)
    page = pdf.pages[int(page_no) - 1]
    width , height = float(page.width) , float(page.height)
    w0, h0, w1, h1 = normalized_contour
    coordinates = (width / w0, height / h0, width / w1,height / h1)
    coordinates = [coordinate if coordinate > 0 else float(0.0) for coordinate in coordinates]
    # for camelot
    coordinates_int = [int(value) for value in coordinates]
    coordinates_int = [coordinates_int[0], int(height) - coordinates_int[1], coordinates_int[2],
                       int(height) - coordinates_int[3]]
    try:
        try:
            camelot_table = camelot.read_pdf(input_pdf, pages=str(page_no), flavor="stream",row_tol=16,edge_tol=711,columns=["180,306,430"],table_areas=[f'{coordinates_int[0]},{int(coordinates_int[1])},{coordinates_int[2]},{coordinates_int[3]}'])
        except:
            camelot_table = camelot.read_pdf(input_pdf, pages=str(page_no), flavor="stream",row_tol=16,edge_tol=711,table_areas=[f'{coordinates_int[0]},{int(coordinates_int[1])},{coordinates_int[2]},{coordinates_int[3]}'])
        # print(len(camelot_table))
    except Exception as E:
        # print("error---->", E)
        # print("camelot content not available")
        yield ("", "content")
    else:
        df = camelot_table[0].df
        if is_df_with_multiple_columns(df.values.tolist(), 2):
            df[0] = df[0].apply(lambda x: re.sub(r"^([A-Z]{1})\s([A-Z]*)", lambda pat: pat.group(1) + pat.group(2),
                                                 str(x)) if not pd.isna(x) else x)

            if len(df) > 1:
                content = [df.values.tolist()]
                yield (content, "table")
        else:
            content = []
            for row in list(df.index):
                content.append(" ".join([value for value in df.loc[row].tolist() if value]))
            content = "\n".join(content)
            # print("content_extracted- new---->", content)
            yield (content, "content")

def merge_headers(df):                   # remove folded line within brackets ()
    rows, columns = list(df.index) , list(df.columns)
    temp_rows = []
    rows_to_join = []
    rows_to_exclude = []
    temp_rows.append(df.loc[df.index[0]].to_list())
    for column in columns[:1]:
        for row in rows[1:]:
            header = df[column][row]
            # print(header)
            if row not in rows_to_exclude:
                if pd.isna(header) or ":" in header or "?" in header:
                    temp_rows.append(df.loc[row].to_list())
                    # print("appending---->",df.loc[row].to_list())
                else:
                    # print("inside else")
                    for _row in rows[rows.index(row):]:
                        if pd.isna(df[column][_row]):
                            rows_to_join.append(_row)
                            # print("row index appending for nan header", _row)
                        elif ":" not in str(df[column][_row]):
                            rows_to_join.append(_row)
                            # print("row index appending",_row)
                        elif ":" in df[column][_row]:
                            rows_to_join.append(_row)
                            # print(rows_to_join)
                            row_data = df.loc[rows_to_join[0]]
                            # print(row_data)
                            for row_index in rows_to_join[1:]:
                                current_data = df.loc[row_index].fillna("")
                                # print("current_data---->",current_data)
                                if not current_data.empty:
                                    # print("appending_data")
                                    row_data  = row_data.fillna("") + "\n" + current_data
                                    # print("row_data------>",row_data)
                                # print(row_data)
                            else:
                                row_data = [str(value).strip() if value and str(value).strip() else "" for value in row_data.to_list()]
                                temp_rows.append(row_data)
                                rows_to_exclude.extend(rows_to_join)
                                rows_to_join = []
                                break
    if rows_to_exclude:
        return pd.DataFrame(temp_rows)
    else:
        return df

def merge_header_columns(df):
    print(df.values.tolist())
    rows, columns = list(df.index), list(df.columns)
    if len(columns) < 3:
        return df
    if any([True if ":" in str(value) else False for value in df[columns[0]].to_list()]) and any([True if ":" in str(value) else False for value in df[columns[1]].to_list()]):
        df[0] = df[df.columns[0]].combine_first(df[df.columns[1]])
        df.drop(df.columns[1], axis="columns", inplace=True)
        # print("aftercolumn combine------>",tabulate(df,tablefmt="grid"))
    return df

def duplicate_removal_by_row_indexing(df):
    # print("duplicate_removal------->",tabulate(df,tablefmt="grid"))
    if df.empty:
        return df
    if len([value for value in df[df.columns[0]] if not pd.isna(value)]) != len(set([value for value in df[df.columns[0]] if not pd.isna(value)])):
        count_dictionary = dict(Counter([value for value in df[df.columns[0]] if not pd.isna(value)]))
        for key, count in count_dictionary.items():
            if count != 1:
                for column in df.columns[:1]:
                    for row in df.index:
                        value = df[column][row]
                        if not pd.isna(value) and str(value).strip() == key:
                            df[column][row] = str(key) + "_" + str(row)
        return df
    else:
        return df

def chunk_df(result):
    try:
        df12 = pd.DataFrame(result[0][0])
    except:
        df12 = pd.DataFrame([result[0]])
    rows, columns = list(df12.index), list(df12.columns)
    header = None
    start_index = 0
    chunked_dict = {}
    for row in rows:
        content = " ".join(df12.loc[row]).strip()
        # print("content_to_check------>", content)
        for c_header, condition in chunk_condition.items():
            # print("condition_to_check------>",condition)
            if condition.lower() in content.lower():
                # print("condition matched----->",condition)
            # if re.search(r"{}".format(condition),content):
            #     print("available condition",condition)
            #     print("available in content",content)
                # if header:
                #     chunked_dict[header] = df12.loc[start_index:row]
                #     print("header matched----->", header)
                #     yield df12.loc[start_index:row-1]
                yield df12.loc[start_index:row - 1]
                start_index = row
                header = c_header
    if header:
        chunked_dict[header] = df12.loc[start_index:]
        print("header----->",header)
        yield df12.loc[start_index:]
    else:
        chunked_dict["ACTUAL"] = df12
        # print("header not matched----->", header)
        yield df12

def remove_unwanted_content(text:str):
    if not isinstance(text,str):
        return text
    unwanted_contents = ("N/A","n/a","This section to be completed by OWN BRANDS","This section to be completed by  SUPPLIER","COMPANY CONTACT INFORMATION","PRODUCT HANDLING")
    if text.strip() in unwanted_contents:
        return np.nan
    else:
        return text

def group_by_header(df):

    rows, columns = list(df.index),list(df.columns)
    if not len(columns) > 1:
        return df

    groups = df.groupby([df.columns[0]]).groups
    overall_list = []
    for key, value in groups.items():
        temp_list = []
        if len(list(value)) == 1:
            temp_list.extend(df.loc[list(value)[0]].to_list()[1:])
        else:
            for row_index in list(value):
                for column in columns[1:]:
                    cell_value = df[column][row_index]
                    if str(cell_value).strip() and not pd.isna(cell_value):
                        temp_list.append(cell_value)
        final_content = '\n'.join([str(item) for item in temp_list if not pd.isna(item)])
        overall_list.append([key,final_content])
    return pd.DataFrame(overall_list)

def normalizing_content(feed_from_camelot):
    # print(feed_from_camelot[0][0])
    if not feed_from_camelot.empty:
        if isinstance(feed_from_camelot,pd.DataFrame):
           df = feed_from_camelot.copy(deep=True)
        else:
            df = pd.DataFrame(feed_from_camelot[0][0])
        df[0] = df[0].apply(lambda x: re.sub(r"^([A-Z]{1})\s([A-Z]*)", lambda pat: pat.group(1) + pat.group(2), str(x)) if not pd.isna(x) else x)
        df = df.applymap(lambda x: str(x) if str(x).strip() and x else np.nan)

        # print("after cleaning duplicate----->",tabulate(df,tablefmt="grid"))
        if all([True if ":" not in str(value) and "(g)" not in str(value) and not "other" == str(value).strip().lower() else False for value in df[df.columns[0]] if not pd.isna(value)]):
            df.drop(df.columns[0],axis="columns",inplace=True)
        # if len(df) - sum(df[df.columns[0]].isnull()) == 1:
        #     df.drop(df.columns[0], axis="columns", inplace=True)
        # print(df.values.tolist())
        # print(df.columns)
        # print("after drop----->",tabulate(df,tablefmt="grid"))
        if len(df.columns) == 4:
            if sum([True if ":" in str(value) else False for value in df[df.columns[0]] if not pd.isna(value)]) > 1 and sum([True if ":" in str(value) else False for value in df[df.columns[2]] if not pd.isna(value)]) > 1:
                df = pd.DataFrame(np.vstack([df.iloc[:, :2], df.iloc[:, 2:]]))
        df = df.dropna(axis=1, how="all")
        df = df.dropna(axis=0, how="all")

        df = duplicate_removal_by_row_indexing(df)

        # print("after drop na----->",tabulate(df,tablefmt="grid"))
        if len(df.columns) > 1 and not all(df[df.columns[0]].isnull()):    # table
            if sum(df[df.columns[0]].isnull()) > len(df)/2 and len(df.columns) == 4:
                # df = pd.DataFrame(np.vstack([df.iloc[:,:2],df.iloc[:,2:]]))
                df = df.applymap(remove_unwanted_content)
                # print(tabulate(df, tablefmt="grid"))

                # print("before mergr column",tabulate(df,tablefmt="grid"))
                df = merge_header_columns(df)
                # print("after mergr column",tabulate(df,tablefmt="grid"))
                df = merge_headers(df)  # commented need to check
                df[df.columns[0]].fillna(method='ffill', axis=0, inplace=True)
                df[df.columns[0]].fillna(method='bfill', axis=0, inplace=True)
                # print("df after drop ist column---->", tabulate(df, tablefmt="grid"))
                if not any([True if str(value).strip().lower() == "other" or "(g)" in str(value) else False for value in df[df.columns[0]] if not pd.isna(value)]):
                    df = group_by_header(df)
                # df = duplicate_removal_by_row_indexing(df)
                    # print("df after drop ist column grouped---->", tabulate(df, tablefmt="grid"))
                yield df
            else:
                # print(tabulate(df, tablefmt="grid"))
                df = df.applymap(remove_unwanted_content)
                # df = df.dropna(axis=1, how="all")
                # df = df.dropna(axis=0, how="all")
                df = merge_header_columns(df)
                df = merge_headers(df)  # commented need to check
                df[df.columns[0]].fillna(method='ffill', axis=0, inplace=True)
                df[df.columns[0]].fillna(method='bfill', axis=0, inplace=True)
                # print("df after drop 2st column---->", tabulate(df, tablefmt="grid"))
                if not any([True if str(value).strip().lower() == "other" or "(g)" in str(value) else False for value in df[df.columns[0]] if not pd.isna(value)]):
                    df = group_by_header(df)
                # df = duplicate_removal_by_row_indexing(df)
                    # print("df after drop 2st column grouped---->", tabulate(df, tablefmt="grid"))
                yield df
        else:
            # if len(df.columns) == 1 and df.columns == [2]:    # content
                # print("\n".join(df[2]).strip())
                # yield "\n".join(df[2]).strip()

            try:
                if len(df.columns) == 1:
                    yield "\n".join(df[df.columns[0]]).strip()
            except:
                yield ""
        print("-----" * 10)

def main_data_extractor(input_pdf,page_no,location_path):
    img = image_processing(f"{location_path}/{str(page_no)}.png")
    for normalized_contour in find_contours(img, tree=True):
        for result in content_within_bounding_box_camelot(input_pdf=f"{input_pdf}", page_no=str(page_no),
                                                          normalized_contour=normalized_contour):
            for chunk in chunk_df(result):
                for result in normalizing_content(chunk):
                    print("*" * 10)
                    if isinstance(result, str):
                        # print(tabulate(pd.DataFrame([result]), tablefmt="grid"))
                        yield ("content",result)
                    else:
                        # print(tabulate(result, tablefmt="grid"))
                        yield ("table", result)

def nutrition_processing(df):
    print('inside nutrition processing')
    nutrition_dict = {}
    rows, columns = list(df.index),list(df.columns)
    for column in columns[:1]:
        for row in rows:
            header = df[column][row].lower().strip()
            header = re.sub(r"\(.*?\)","",header).strip()
            if header:
                for _col in columns[1:]:
                    value = str(df[_col][row]).strip()
                    value = [val for val in set(re.findall(r"(\d*)",value)) if str(val).strip()]
                    if value:
                        value = value[0]
                    else:
                        value = ""
                    if value:
                        value_header = 'PDV' if "%" in value else "Value"
                        if 'added' in header and 'sugars' in header:
                            header = 'added sugar'
                        if 'serving size' in header:
                            value = value.replace(" ", "")
                            if header in nutrition_dict:
                                nutrition_dict['serving size'].append(value)
                            else:
                                nutrition_dict['serving size'] = [value]
                            continue
                        if 'varied' in header:
                            if header in nutrition_dict:
                                nutrition_dict['varied'].append(value)
                            else:
                                nutrition_dict['varied'] = [value]
                            continue
                        if re.search(r"\d",value):
                            value = value.replace(" ", "")
                            if header in nutrition_dict:
                                nutrition_dict[header].append({value_header:{'en':value}})
                            else:
                                nutrition_dict[header] = [{value_header:{'en':value}}]
    return nutrition_dict

def get_page_dict(input_pdf,page,location_path):
    temp_page_dict = {}
    contents_in_page = []
    for type,result in main_data_extractor(input_pdf=f"{input_pdf}",page_no=int(page),location_path=location_path):
        if type == "content":
            if result and str(result).strip() and re.search(r"[A-Za-z]",result):
                if ":" not in result:
                    contents_in_page.append(result)
                elif ":" in result and len(result) > 100:
                    contents_in_page.append(result)
        else:
            df =result
            if any([True if "(g)" in str(value) else False for value in df[df.columns[0]] if not pd.isna(value)]):
                print("Nutrition data")
                nutrition_dict = nutrition_processing(df)
                temp_page_dict.setdefault("NUTRITION_FACTS",[]).append(nutrition_dict)
                continue
            rows , columns = list(df.index), list(df.columns)
            for column in columns[:1]:
                for row in rows:
                    header = str(df[column][row]) if not pd.isna(df[column][row]) and  str(df[column][row]).strip() else ""
                    for classifier_class,mapping_list in manual_mapper_dict.items():
                        for mapping_string in mapping_list:
                            if re.search(r"{}".format(mapping_string),header,flags=re.I|re.M):
                                for _col in columns[1:]:
                                    print(classifier_class,"------->",df[_col][row])
                                    if df[_col][row]:
                                        temp_page_dict.setdefault(classifier_class,[]).append(df[_col][row])
    else:
        print("string contenst------>",contents_in_page)
        for content in contents_in_page:
            prediction = classifier.predict(laser.embed_sentences([content], lang='en'))
            probability = classifier.predict_proba(laser.embed_sentences([content], lang='en'))
            probability[0].sort()
            max_probability = max(probability[0])
            print("content---->",content)
            print("class ---->",prediction)
            print("probability---->",max_probability)
            print("-----"*10)
            if prediction[0] in ["ingredients","marketing claim","warning statement","usage instruction","storage instruction"] and max_probability > 0.60:
                if content and str(content).strip() and not pd.isna(content):
                    if max_probability > 0.80:
                        temp_page_dict.setdefault(key_mapper[prediction[0]],[]).append(content)
                    else:
                        temp_page_dict.setdefault("OTHER_INSTRUCTIONS", []).append(content)
    duplicate_removal_dict = {}
    for key , value in temp_page_dict.items():
        if key == "NUTRITION_FACTS":
            duplicate_removal_dict[key] = value
            continue
        # if key == "OTHER_INSTRUCTIONS":
        #     for content in set(value):
        #         match_scores = []
        #         for original_content in set(value):
        #             if len(content) < len(original_content):
        #                 match_score = fuzz.partial_ratio(content,original_content)
        #                 match_scores.append(match_score)
        #         if 100 not in match_scores:
        #             duplicate_removal_dict.setdefault("OTHER_INSTRUCTIONS",[]).append(content)
        #     continue
        duplicate_removal_dict[key] = [{"en":content} for content in set(value) if not pd.isna(content) and str(content).strip()]
    return duplicate_removal_dict

def get_smb_or_local(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                with open(input_pdf_location,'wb') as pdf:
                    pdf.write(f.read())
            print('file found')
        except:
            pass
            # raise Exception('File is being used by another process / smb not accessible')
        finally:
            smbclient.reset_connection_cache()
        return input_pdf_location
    else:
        return document_location+input_pdf

def albertson_amer_main(input_pdf,pages):
    input_pdf_location = f'{temp_directory.name}/input_pdf.pdf'
    print("temp_dir------->",temp_directory.name)
    input_pdf = get_smb_or_local(input_pdf,input_pdf_location)
    image_conversion_status = pdf_to_image(f"{input_pdf}",temp_directory.name)
    assert image_conversion_status == "success" , "please provide right path"
    plumber_pdf_obj = pdfplumber.open(f"{input_pdf}")
    page_dict = {}
    for page in pages.split(","):
        if int(page)-1 in range(len(plumber_pdf_obj.pages)):
            temp_dict = get_page_dict(input_pdf,page,temp_directory.name)
            page_dict[page] = temp_dict
    try:
        temp_directory.cleanup()
    except:
        pass
    return page_dict
