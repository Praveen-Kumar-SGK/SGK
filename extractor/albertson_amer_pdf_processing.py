import shutil
import camelot
import pandas as pd
import numpy as np
import tempfile

# from tabulate import tabulate
import re
import cv2
import imutils
from collections import ChainMap
import fitz
from pdf2image import convert_from_path
import smbclient
import joblib

from .excel_processing import document_location,model_location,laser,smb_username,smb_password,classify

manual_mapper_dict = {"BRAND_NAME":["^BRAND"],
                      "VARIANT":["LEGAL PRODUCT NAME"],
                      "FUNCTIONAL_NAME":["PRODUCT DESCRIPTOR"],
                      "NET_CONTENT_STATEMENT":["RETAIL UNIT NET CONTENT","NET WEIGHT"],
                      "OTHER_INSTRUCTIONS":["HANDLING STATEMENT","DIRECTIONS FOR USE","COOK INSTRUCTIONS","OTHER MANDATORY","DIRECTIONS"],
                      "LOCATION_OF_ORIGIN":["COUNTRY OF ORIGIN:","COUNTRY OF ORIGIN STATEMENT"],
                      # "MARKETING_CLAIM":["YES"],
                      "ALLERGEN_STATEMENT":["CONTAINS STATEMENT","MAY CONTAIN STATEMENT"],
                      "SERVING_SIZE":["SERVING SIZE"],
                      "NUMBER_OF_SERVINGS_PER_PACKAGE":["SERVINGS PER CONTAINER"],
                      "COPYRIGHT_TRADEMARK_STATEMENT":["COPYRIGHT STATEMENTS"],
                      "INGREDIENTS_DECLARATION": ["INGREDIENT STATEMENT"]
                      }

# for content classification
key_mapper = {"ingredients":"INGREDIENTS_DECLARATION",
              "marketing claim":"OTHER_INSTRUCTIONS",
              "usage instruction":"OTHER_INSTRUCTIONS",
              "storage instruction":"OTHER_INSTRUCTIONS",
              "warning statement":"WARNING_STATEMENTS",
              }

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

def pdf_to_image(input_pdf,location):
    images = convert_from_path(input_pdf)
    for index, image in enumerate(images):
        image.save(f'{location}/{index + 1}.png')
    return len(images)

def image_processing_v1(input_img):
    input_img = cv2.imread(input_img)
    de_img = cv2.GaussianBlur(input_img, (5,5),0)
    lap = cv2.Laplacian(de_img,ddepth=cv2.CV_16S,ksize=1)
    lap[np.any(lap != [0, 0, 0], axis=-1)] = [255,255,255]
    threshold = np.uint8(cv2.threshold(lap, 250, 255, cv2.THRESH_BINARY)[1])    # converted to int8 format
    gray_scale = cv2.cvtColor(threshold, cv2.COLOR_BGR2GRAY)
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(55,1))
    horizontal_lines = cv2.morphologyEx(gray_scale, cv2.MORPH_OPEN, horizontal_kernel,iterations=4)
    # Vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT,(1,20))
    vertical_lines = cv2.morphologyEx(gray_scale, cv2.MORPH_OPEN, vertical_kernel,iterations=2)
    table = cv2.add(horizontal_lines, vertical_lines)
    return table

def draw_contours_over_pdf(input_pdf,image,tree=None,area=10000,page_index=1,thickness=0.5):
    i_height = image.shape[0]
    i_width = image.shape[1]
    # print("image_height---->",i_height)
    # print("image_width---->",i_width)
    if not tree:
        cnts = cv2.findContours(image.copy(), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    else:
        cnts = cv2.findContours(image.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    cnts1 = imutils.grab_contours(cnts)
    cnts2 = [cnt for cnt in cnts1 if cv2.contourArea(cnt)]
    # i = 0
    # img_draw = original_image.copy()
    doc = fitz.open(input_pdf)
    width_list = []
    height_list = []
    rect_list = []
    for contour in cnts2:
        if cv2.contourArea(contour) > area:                 # 4000 for lase footer subject localization ...normal : 50000
            x, y, w, h = cv2.boundingRect(contour)
            a,b,c,d = i_width / x, i_height / y, i_width / (x + w), i_height / (y + h)
            width = doc[page_index].rect.width
            height = doc[page_index].rect.height
            # print("page_width---->",width)
            # print("page_height---->",height)
            width_list.append(round(width / a))
            width_list.append(round(width / c))
            height_list.append(round(height / b))
            height_list.append(round(height / d))
            coordinates = [width / a, height / b, width / c, height / d]
            # print("coordinates----->",coordinates)
            rect_list.append(coordinates)

    width_list.sort()
    width_replace_dict = dict(ChainMap(*[{value: value, value + 1: value, value + 2: value, value + 3: value,value + 4: value,value + 5: value} for value in width_list]))
    width_list = list(set([width_replace_dict[value] for value in width_list]))
    # print("width_list------>",width_list)

    height_list.sort()
    height_replace_dict = dict(ChainMap(*[{value: value, value + 1: value, value + 2: value, value + 3: value,value + 4: value,value + 5: value} for value in height_list]))
    height_list = list(set([height_replace_dict[value] for value in height_list]))

    rect_list_final = set()
    for coor in rect_list:
        coor_rounded = (width_replace_dict[round(coor[0])],height_replace_dict[round(coor[1])],width_replace_dict[round(coor[2])],height_replace_dict[round(coor[3])])
        rect_list_final.add(coor_rounded)

    for width in width_list:
        # print("width----->",width)
        min_height, max_height = max(height_list), min(height_list)
        for rect in rect_list_final:
            if width in rect:
                if rect[1] < min_height:
                    min_height = rect[1]

                if rect[3] > max_height:
                    max_height = rect[3]
        # print(min_height,max_height)
        if min_height > 0:
            doc[page_index].draw_line([width, min_height], [width, max_height], color=(0, 0, 0),width=thickness)

    for coordinate in rect_list:
        doc[page_index].draw_line([min(width_list), height_replace_dict[round(coordinate[1])]], [max(width_list), height_replace_dict[round(coordinate[1])]], color=(0, 0, 0),width=thickness)
        doc[page_index].draw_line([min(width_list), height_replace_dict[round(coordinate[3])]], [max(width_list), height_replace_dict[round(coordinate[3])]], color=(0, 0, 0),width=thickness)

    # doc.save(filename=f'/Users/vijaykanagaraj/PycharmProjects/testing/s11.pdf')
    doc.saveIncr()
    return "success"

def draw_tables_over_pdf(input_pdf,location_to_save_image):
    len_pages = pdf_to_image(input_pdf, location=location_to_save_image)
    for index in range(len_pages):
        # img = cv2.imread(f"{location_to_save_image}{index + 1}.png")
        processed_image = image_processing_v1(f"{location_to_save_image}/{index + 1}.png")
        draw_contours_over_pdf(input_pdf, processed_image, tree=True, page_index=index, thickness=0.5)
    return len_pages

def remove_unwanted_content(text:str):
    if not isinstance(text,str):
        return text
    unwanted_contents = ("N/A","n/a","NA","This section to be completed by OWN BRANDS","This section to be completed by  SUPPLIER","COMPANY CONTACT INFORMATION","PRODUCT HANDLING")
    if text.strip() in unwanted_contents:
        return np.nan
    else:
        return text

def nutrition_processing(df):
    print('inside nutrition processing')
    nutrition_dict = {}
    rows, columns = list(df.index),list(df.columns)
    for column in columns[:1]:
        for row in rows:
            header = str(df[column][row]).lower().strip()
            header = re.sub(r"\(.*?\)","",header).strip()
            if header:
                for _col in columns[1:]:
                    value = str(df[_col][row]).strip()
                    value = [val for val in set(re.findall(r"(\d*\.?\d*)",value)) if str(val).strip()]
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

def extract_data(input_pdf,page_no):
    page_dict = {}
    unmapped = set()
    classifier = joblib.load(model_location)
    empty_cell_to_na = lambda cell: cell if (str(cell).strip() and cell) else np.nan
    extracted_data = camelot.read_pdf(input_pdf, pages=str(page_no))
    for df_obj in extracted_data:
        df = df_obj.df
        df = df.applymap(remove_unwanted_content)
        df = df.applymap(empty_cell_to_na)
        df[0] = df[0].apply(lambda x: re.sub(r"^([A-Z]{1})\s([A-Z]*)", lambda pat: pat.group(1) + pat.group(2), str(x)) if not pd.isna(x) else x)  # first letter space extraction error rectification

        rows_to_divide = df[df.isna().all(axis=1)].index.to_list()
        rows_to_divide.extend([df.index[0], df.index[-1] + 1])
        rows_to_divide.sort()

        df_dict = {}
        for id, row_num in enumerate(rows_to_divide):
            if row_num > 0:
                df_chunk = df[rows_to_divide[id - 1]:row_num]
                df_chunk.dropna(how='all', axis=1, inplace=True)  # drop empty columns
                df_chunk.dropna(how='all', axis=0, inplace=True)  # drop empty rows
                if not isinstance(df_chunk,pd.DataFrame) or len(df_chunk.columns) < 1:         # filter non dataframe object to opass through
                    continue
                df_dict[id] = df_chunk
                # print("hellooooooooooo------>",tabulate(df_chunk,tablefmt="grid"))
                # print("hellooooooooooo type------>",type(df_chunk))
                # print("hellooooooooooo shape------>",df_chunk.shape)

                if len(df_chunk.columns) == 1:
                    # print("inside single comntent")
                    for content in df_chunk[df_chunk.columns[0]]:
                        # print("content_classification_content------->", str(content))
                        if not pd.isna(content) and str(content).strip() and len(str(content)) > 40:
                            prediction = classifier.predict(laser.embed_sentences([content], lang='en'))
                            probability = classifier.predict_proba(laser.embed_sentences([content], lang='en'))
                            probability[0].sort()
                            max_probability = max(probability[0])
                            # print("prediction------->", str(prediction[0]))
                            # print("prediction probability------->", max_probability)
                            if prediction[0] in ("ingredients", "marketing claim", "warning statement",
                                                 "usage instruction", "storage instruction") and max_probability > 0.70:
                                page_dict.setdefault(key_mapper[prediction[0]], []).append({classify(str(content))[0]:str(content)})
                    continue

                if any([True if "(g)" in str(value) else False for value in df_chunk[df_chunk.columns[0]] if not pd.isna(value)]):
                    nutrition_dict = nutrition_processing(df_chunk)
                    page_dict.setdefault("NUTRITION_FACTS", []).append(nutrition_dict)
                    continue

                if len(df_chunk.columns) == 4 and sum([True if ":" in str(value) else False for value in df_chunk[df_chunk.columns[0]] if not pd.isna(value)]) > 1 and sum([True if ":" in str(value) else False for value in df_chunk[df_chunk.columns[2]] if not pd.isna(value)]) > 1:
                    # df_chunk.fillna(method='bfill', axis=1, inplace=True)
                    for row_index in df_chunk.index:
                        if df_chunk.loc[row_index].isnull().sum() > 1:
                            df_chunk.loc[row_index] = df_chunk.loc[row_index].bfill()
                    df_chunk = pd.DataFrame(np.vstack([df_chunk.iloc[:, :2], df_chunk.iloc[:, 2:]]))
                    df_chunk.dropna(how='all', axis=1, inplace=True)  # drop empty columns
                    df_chunk.dropna(how='any', axis=0, inplace=True)  # drop empty rows


                rows, columns = list(df_chunk.index), list(df_chunk.columns)
                for column in columns[:1]:
                    for row in rows:
                        header = str(df_chunk[column][row]) if not pd.isna(df_chunk[column][row]) and str(
                            df_chunk[column][row]).strip() else ""
                        if not header:
                            for _col in columns[1:]:
                                content = df_chunk[_col][row]
                                print("content_classification_content------->",str(content))
                                if not pd.isna(content) and str(content).strip() and len(str(content)) > 25:
                                    prediction = classifier.predict(laser.embed_sentences([content], lang='en'))
                                    probability = classifier.predict_proba(laser.embed_sentences([content], lang='en'))
                                    probability[0].sort()
                                    max_probability = max(probability[0])
                                    print("prediction------->", str(prediction[0]))
                                    print("prediction probability------->",max_probability)
                                    if prediction[0] in ["ingredients","marketing claim","warning statement","usage instruction","storage instruction"] and max_probability > 0.70:
                                        page_dict.setdefault(key_mapper[prediction[0]], []).append({classify(str(content))[0]:str(content)})
                        else:
                            classified = False
                            for classifier_class, mapping_list in manual_mapper_dict.items():
                                for mapping_string in mapping_list:
                                    if re.search(r"{}".format(mapping_string), header, flags=re.I | re.M):
                                        classified = True
                                        for _col in columns[1:]:
                                            print(classifier_class, "------->", df_chunk[_col][row])
                                            if not pd.isna(df_chunk[_col][row]) and df_chunk[_col][row].strip():
                                                page_dict.setdefault(classifier_class, []).append({classify(str(df_chunk[_col][row]))[0]:str(df_chunk[_col][row])})
                            if not classified:
                                for _col in columns[1:]:
                                    print("unmapped", "------->", df_chunk[_col][row])
                                    if not pd.isna(df_chunk[_col][row]) and df_chunk[_col][row].strip():
                                        unmapped.add(df_chunk[_col][row])
                                        # page_dict.setdefault("unmapped", []).append({classify(str(df_chunk[_col][row]))[0]:str(df_chunk[_col][row])})

                # print(tabulate(df_chunk,tablefmt="grid"))
        # print(df)
    print("page_dict----------->",page_dict)
    for unmapped_element in unmapped:
        page_dict.setdefault("unmapped", []).append({"en": str(unmapped_element)})
    return page_dict

def albertson_amer_main(input_pdf,page_numbers):
    final_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    target_pdf = f"{temp_directory.name}/input.pdf"
    target_pdf = get_smb_or_local(input_pdf,target_pdf)
    print("target_pdf------>",target_pdf)
    # shutil.copy(input_pdf,target_pdf)
    len_pages = draw_tables_over_pdf(input_pdf=target_pdf,location_to_save_image=temp_directory.name)
    # assert status == "success" , "pdf table and image conversion issue"
    print(range(len_pages))

    for page in page_numbers.split(","):
        print("page------->", page)
        page_dict = {}
        if int(page)-1 in range(int(len_pages)):
            page_dict = extract_data(target_pdf,page)
        final_dict[str(page)] = page_dict
    temp_directory.cleanup()
    return final_dict
