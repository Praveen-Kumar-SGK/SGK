import os, re
import requests
import pytesseract as pt
import fitz
import json
import cv2
import tempfile, shutil
from fuzzywuzzy import process , fuzz
from .excel_processing import *

def textract_ocr_api(input_image):
    '''AWS custom modified ocr from Bala Team'''
    url = "https://ummg2iyo1l.execute-api.us-east-2.amazonaws.com/prod/textract"
    payload = {}
    files = [
        ('file', ('input.png', open(input_image, 'rb'), 'image/png'))
    ]
    headers = {}
    response = requests.request("POST", url, headers=headers, data=payload, files=files)
    print(response.text)
    response_dict = json.loads(response.text)
    # assert response_dict.get("message","fail").lower() == "success","Error in textract API"
    return response_dict

def api_response_to_df(input_dict):
    df_list = []
    for index , row_dict in enumerate(input_dict["data"]):
        row_values = []
        for _ , value in row_dict.items():
            if value and str(value).strip():
                row_values.append(value)
        if re.findall(r"^\d*%?$","".join(row_values).strip(),flags=re.M):
            if index > 0:
                df_list[index-1].extend(row_values)
                row_values = []
        df_list.append(row_values)
    return pd.DataFrame(df_list)


def api_response_to_df_update(input_dict):
    join_single_line = ["per servings container", "calories per serving","nutrition facts"]
    row_values_as_list = lambda input_dict , index: [value for _ , value in input_dict["data"][index].items() if value and str(value).strip()]
    df_list = []
    index_to_skip = []
    for index , row_dict in enumerate(input_dict["data"]):
        row_values = row_values_as_list(input_dict,index)
        row_string = " ".join(row_values).strip()
        if index not in index_to_skip:
            if re.findall(r"^\d*%?$",row_string,flags=re.M):
                if index > 0:
                    df_list[-1].extend(row_values)
                    row_values = []
            if index < len(input_dict["data"])-1:
                next_row_values = row_values_as_list(input_dict,index + 1)
                next_row_string = " ".join(next_row_values).strip()
                # print(" ".join((row_string,next_row_string)))
                _,matched_score = process.extractOne(" ".join((row_string,next_row_string)).lower().strip(),join_single_line,scorer=fuzz.WRatio)
                # print(matched_score)
                if matched_score > 94:
                    index_to_skip.append(index+1)
                    row_values.extend(next_row_values)
            df_list.append(row_values)
        else:
            continue
    return pd.DataFrame(df_list)

def daily_intake_extract(df) -> list:
    is_content_available = False
    rows , columns = df.shape
    daily_intake = []
    for column in range(columns):
        daily_intake_temp = []
        for row in range(rows):
            cell_content = df[column][row]
            if cell_content and str(cell_content).strip():
                if str(cell_content).strip().startswith("*"):
                    if daily_intake_temp:
                        daily_intake.append("\n".join(daily_intake_temp))
                        daily_intake_temp = []
                    daily_intake_temp.append(str(cell_content))
                    df[column][row] = ""
                    is_content_available = True
                    continue
                if is_content_available and str(cell_content).strip().endswith("."):
                    daily_intake_temp.append(str(cell_content))
                    df[column][row] = ""
                    is_content_available = False
                    continue
                if is_content_available:
                    daily_intake_temp.append(str(cell_content))
                    df[column][row] = ""
        if daily_intake_temp:
            daily_intake.append("\n".join(daily_intake_temp))
    return daily_intake

def ocr_data_loss_preprocessing(text:str):
    replace_dict = {"carb.":"carbohydrates","serv.":"serving","saturated":"saturated fat","trans":"trans fat","includes":"sugar","folate":"folic acid","thiamin":"vitamin b1","riboflavin":"vitamin b2"}
    text = str(text).lower()
    for text_to_replace , with_text in replace_dict.items():
        text = text.replace(text_to_replace,with_text)
    text = re.sub(r"\b(o)(\s{0,2})(g|mg|mcg)\b",lambda pat: "0"+pat.group(2)+pat.group(3),text,flags=re.M|re.I)
    return text

class BG_FOODS:
    input_pdf , pages = None , None
    def __init__(self):
        self.temp_directory = tempfile.TemporaryDirectory(dir=document_location)
        self._input_pdf_location = f'{self.temp_directory.name}/input_pdf.pdf'
        self.image_converted_pdf = f'{self.temp_directory.name}/image.pdf'

    def get_input(self,input_doc):
        if input_doc.startswith('\\'):
            with smbclient.open_file(r"{}".format(input_doc), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                with open(self._input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
            return self._input_pdf_location
        else:
            return document_location + input_doc

    def image_to_pdf(self,input_image, preprocessing=False):
        "output pdf name ---> image.pdf"

        if not os.path.exists(input_image):
            raise FileNotFoundError("Input image doesn't exist")

        with open(self.image_converted_pdf, "wb") as pdf:
            if preprocessing:
                print("doing preprocessing")
                img = cv2.imread(input_image, cv2.IMREAD_GRAYSCALE)
                pdf.write(pt.image_to_pdf_or_hocr(img))
            else:
                print("direct conversion")
                pdf.write(pt.image_to_pdf_or_hocr(input_image))
        return "Success"

    def get_image_from_pdf(self,pdf: str, page: int, path_to_save: str = None) -> dict:  # output image format image_0.png
        if not path_to_save:
            path_to_save = self.temp_directory.name
        try:
            doc = fitz.Document(pdf)
            page = doc[page - 1]
        except (AttributeError, IndexError):
            raise Exception("page number doesn't exist")
        except (FileNotFoundError, FileExistsError, RuntimeError):
            raise Exception("Pdf doesn't exists")

        images = page.get_images()
        for image_index, image_detail in enumerate(images):
            xref = image_detail[0]
            base_image = doc.extractImage(xref)
            # with open(r"/Users/vijaykanagaraj/PycharmProjects/testing/input.{}".format(base_image["ext"]),"wb") as img:
            with open(r"{}/image_{}.png".format(path_to_save, image_index), "wb") as img:
                img.write(base_image["image"])
        return {"status": 1, "images_count": len(images), "path_saved": path_to_save}

    def get_content_from_pdf(self,pdf: str,page: int) -> list:
        '''list of tuple as output --> tuple[5] 0: text , 1 : image
        tuple[4] -> text
        '''
        try:
            doc = fitz.Document(pdf)
            page = doc[page - 1]
        except (AttributeError, IndexError):
            raise Exception("page number doesn't exist")
        except (FileNotFoundError, FileExistsError, RuntimeError):
            raise Exception("Pdf doesn't exists")

        content_list = page.get_text("blocks")
        return content_list

    @staticmethod
    def content_list_to_dict(content_list:list) -> dict:
        local_dict = {}
        model = joblib.load(model_location)
        for tuple_content in content_list:
            if tuple_content[6] == 0: # {0:text,1:image}
                content = str(tuple_content[4]).strip()
                lang = classify(content)[0]
                # content_class = "content"
                content_class = model.predict(laser.embed_sentences(content,lang="en"))[0]
                content_class_probability = np.max(model.predict_proba(laser.embed_sentences(content,lang="en")))
                # print(content_class,"---->",content_class_probability)
                if content_class_probability < 0.80:
                    content_class = "unmapped"
                local_dict.setdefault(content_class,[]).append({lang:content})
        return local_dict

    @staticmethod
    def content_list_to_dict_2(content_list:list) -> dict:
        local_dict = {}
        model = joblib.load(model_location)
        content_list_data_only = [str(tuple_content[4]).strip() for tuple_content in content_list if tuple_content[6] == 0]
        content_classes = model.predict(laser.embed_sentences(content_list_data_only, lang="en"))
        content_class_probabilities = model.predict_proba(laser.embed_sentences(content_list_data_only, lang="en"))
        # print("content_class---->",list(content_classes))
        # print("content_class_probabilities---->",list(content_class_probabilities))
        for index , content_class in enumerate(content_classes):
            if content_list_data_only[index]:
                lang = classify(str(content_list_data_only[index]))[0]
                if content_class == "ingredients" and np.max(content_class_probabilities[index]) > 0.80:
                    local_dict.setdefault("INGREDIENTS_DECLARATION",[]).append({lang:content_list_data_only[index]})
                else:
                    local_dict.setdefault("OTHER_INSTRUCTIONS", []).append({lang: content_list_data_only[index]})
        return local_dict

    @staticmethod
    def regex_nutrition_extract(x):
        element_list = []
        value_list = []
        regex_extracted = re.findall(
            r"([\w\,\/\-\s]*?)\s+(\<?\s?\-?\d{0,3}\.?\d{0,2}\s?(%|g added sugars|g\b|kj|kcal|mg|mcg|cal\b))", x, flags=re.I)
        if not regex_extracted:
            regex_extracted = re.findall(r"([\w\,\-\s]*?)\s+((\<?\s?\-?\d{0,3}\.?\d{0,2}\s?))", x, flags=re.I)
        for tuple_content in regex_extracted:
            if tuple_content[0] and tuple_content[0].strip() not in ("-"):
                element_list.append(tuple_content[0])
            if tuple_content[1]:
                value_list.append(tuple_content[1])
        return {" ".join(element_list).strip():value_list}

    def extract_nutrition_data(self,df):
        others_dict = {}
        nutri_dict = {}
        rows = df.index.tolist()
        _,column_count = df.shape
        nutrition_model = joblib.load(master_nutrition_model_location)
        get_row_list = lambda df, row: [value for value in df.loc[row].tolist() if not pd.isna(value)]

        def nutri_extract_classifier(nutri_key):
            nutri_key = nutri_key.split("/")
            nutrition_class = nutrition_model.predict(laser.embed_sentences(nutri_key, lang="en"))[0].strip()
            nutrition_class_probability = np.max(
                nutrition_model.predict_proba(laser.embed_sentences(nutri_key, lang="en")))
            # print(nutrition_class, "------------>", nutrition_class_probability)
            if nutrition_class_probability > 0.90:
                for value in value_list:
                    if nutrition_class in ("Calories"):
                        value = re.sub("%", "", str(value)).strip()
                    nutri_header = "PDV" if "%" in str(value) else "Value"
                    nutri_dict.setdefault(nutrition_class, []).append({nutri_header: {"en": str(value).strip()}})
                    # print(nutrition_class)
            else:
                nutri_key = ocr_data_loss_preprocessing(row_list[0])
                nutri_key = nutri_key.split("/")
                nutrition_class = nutrition_model.predict(laser.embed_sentences(nutri_key, lang="en"))[0]
                nutrition_class_probability = np.max(
                    nutrition_model.predict_proba(laser.embed_sentences(nutri_key, lang="en")))
                if nutrition_class_probability > 0.90:
                    for value in row_list[1:]:
                        if nutrition_class in ("Calories"):
                            value = re.sub("%", "", str(value)).strip()
                        nutri_header = "PDV" if "%" in str(value) else "Value"
                        nutri_dict.setdefault(nutrition_class, []).append(
                            {nutri_header: {"en": str(value).strip()}})
                else:
                    for value in row_list:
                        lang = classify(str(value))[0]
                        others_dict.setdefault("OTHER_INSTRUCTIONS", []).append({lang: str(value).strip()})

        for row in rows:
            row_list = get_row_list(df, row)
            row_list_string = " ".join(row_list)
            row_list_string = ocr_data_loss_preprocessing(row_list_string)
            # print("row_string+_list----->",row_list_string)
            nutri_key_value_dict = self.regex_nutrition_extract(row_list_string)
            # print(nutri_key_value_dict)

            for nutri_key , value_list in nutri_key_value_dict.items():
                if "calories" in "".join(row_list).lower() or re.search(r"^\d+$","".join(row_list).lower().strip()):
                    for value in row_list:
                        if re.search(r"\d",str(value)):
                            value = re.sub(r"calories","",str(value),flags=re.I).strip()
                            nutri_header = "PDV" if "%" in str(value) else "Value"
                            nutri_dict.setdefault("Calories", []).append({nutri_header: {"en": value}})
                    continue

                elif "serving" in "".join(row_list).lower() and "container" in "".join(row_list).lower() and re.search(r"\d"," ".join(row_list).lower().strip()):
                    for value in row_list:
                        others_dict.setdefault("NUMBER_OF_SERVINGS_PER_PACKAGE", []).append({"en": str(value).strip()})
                    continue

                elif ("serving" in "".join(row_list).lower() and "per" not in "".join(row_list).lower()) or re.search(r"\d+\s+[a-zA-Z]+\s+(\(\d+\s{0,2}(ml|g|mcg|mg|kg)\))"," ".join(row_list).lower()):
                    # \d+\s+[a-zA-Z]+\s+(\(\d+\s{0,2}(ml|g|mcg|mg|kg|lb|oz)\s{0,2}\d{0,2}\s{0,2}(ml|g|mcg|mg|kg|lb|oz)?\)) we can use this also for regex serving size match
                    for value in row_list:
                        if re.search(r"\d", str(value)):
                            others_dict.setdefault("SERVING_SIZE", []).append({"en": str(value).strip()})
                    continue

                elif nutri_key and str(nutri_key).strip() and value_list and "%" not in row_list[0] and "serving" not in row_list[0] and column_count > 1:
                    nutri_extract_classifier(nutri_key)

                elif nutri_key and str(nutri_key).strip() and value_list and "serving" not in row_list[0] and column_count == 1:
                    nutri_extract_classifier(nutri_key)

                else:
                    for value in row_list:
                        lang = classify(str(value))[0]
                        others_dict.setdefault("OTHER_INSTRUCTIONS", []).append({lang: str(value).strip()})
        print({"NUTRITION_FACTS":[nutri_dict],**others_dict})
        return {"NUTRITION_FACTS":[nutri_dict],**others_dict}

    def main(self,input_pdf,pages):
        final_dict = {}
        self.input_pdf = self.get_input(input_pdf)
        self.pages = pages
        is_df_with_multiple_columns = lambda x: True if len(x[0]) > 1 else False
        nan_replace = lambda x: x.strip() if x and str(x).strip() else np.nan

        for page in pages.split(","):
            page_dict = {}
            content_list = self.get_content_from_pdf(self.input_pdf,int(page))
            page_dict = {**self.content_list_to_dict_2(content_list),**page_dict}
            img_conversion_details = self.get_image_from_pdf(self.input_pdf,int(page))  # {"status": 1, "images_count": len(images), "path_saved": path_to_save}
            if img_conversion_details["status"] and img_conversion_details["images_count"] > 0:
                textract_api_data = textract_ocr_api(f"{img_conversion_details.get('path_saved')}/image_0.png")
                # print(textract_api_data)
                if textract_api_data["status"] and textract_api_data["data"] and is_df_with_multiple_columns(textract_api_data["data"]):
                # if textract_api_data["status"] and textract_api_data["data"]:
                    df = api_response_to_df_update(textract_api_data)
                    daily_intake_statements = daily_intake_extract(df)
                    print("daily intake statement---->",daily_intake_statements)
                    for daily_intake_statement in daily_intake_statements:
                        lang = classify(daily_intake_statement)[0]
                        page_dict.setdefault("daily_intake_statement",[]).append({lang:daily_intake_statement})
                    df = df.applymap(nan_replace)
                    df.dropna(inplace=True,axis=0,how="all")
                    nutrition_table_dict = self.extract_nutrition_data(df)
                    page_dict["NUTRITION_FACTS"] = nutrition_table_dict.pop("NUTRITION_FACTS")
                    for key , value_list in nutrition_table_dict.items():
                        page_dict.setdefault(key,[]).extend(value_list)
                # elif page_dict:
                #     # pytesseract extraction
                #     img = cv2.imread(f"{img_conversion_details.get('path_saved')}/image_0.png",cv2.COLOR_BGR2GRAY)
                #     text_extracted = pt.image_to_string(img)
                #     text_list = [str(value) for value in text_extracted.split("\n") if value and str(value).strip()]
                #     df = pd.DataFrame(text_list)
                #     nutrition_table_dict = self.extract_nutrition_data(df)
                #     page_dict["NUTRITION_FACTS"] = nutrition_table_dict.pop("NUTRITION_FACTS")
                #     for key, value_list in nutrition_table_dict.items():
                #         page_dict.setdefault(key, []).extend(value_list)
                else:
                    img = cv2.imread(f"{img_conversion_details.get('path_saved')}/image_0.png",cv2.COLOR_BGR2GRAY)
                    height, width = img.shape[:2]
                    if width > height:
                        # divide image into two parts
                        div_width = int(width / 2.25)
                        cv2.imwrite(f"{self.temp_directory.name}/div_{1}.png",img[int(0):height,int(0):div_width])
                        cv2.imwrite(f"{self.temp_directory.name}/div_{2}.png",img[int(0):height,div_width:width])
                        merged_data = []
                        for image in [1,2]:
                            textract_api_data = textract_ocr_api(f"{self.temp_directory.name}/div_{image}.png")
                            api_df = api_response_to_df_update(textract_api_data)
                            api_df_list = api_df.values.tolist()
                            # print(api_df_list)
                            merged_data.extend(api_df_list)
                        df = pd.DataFrame(merged_data)
                        daily_intake_statements = daily_intake_extract(df)
                        print("daily intake statement---->", daily_intake_statements)
                        for daily_intake_statement in daily_intake_statements:
                            lang = classify(daily_intake_statement)[0]
                            page_dict.setdefault("daily_intake_statement", []).append({lang: daily_intake_statement})
                        df = df.applymap(nan_replace)
                        df.dropna(inplace=True, axis=0, how="all")
                        nutrition_table_dict = self.extract_nutrition_data(df)
                        page_dict["NUTRITION_FACTS"] = nutrition_table_dict.pop("NUTRITION_FACTS")
                        for key, value_list in nutrition_table_dict.items():
                            page_dict.setdefault(key, []).extend(value_list)
            final_dict[page] = page_dict
        try:
            self.temp_directory.cleanup()
        except:
            shutil.rmtree(self.temp_directory.name)
        finally:
            print("temp_folder_cleaned")
        return final_dict
