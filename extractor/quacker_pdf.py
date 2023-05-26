#---------------------------------------------             QUAKER             ----------------------------------------------------------------
import warnings
warnings.filterwarnings("ignore")
from pdf2image import convert_from_path
import cv2
import fitz
import pdfplumber
import tempfile
from .excel_processing import *

# Loading MLP Classifier for classification keys
def nutrition_classifier(model=quacker_nutrition_model):
    return joblib.load(model)

# classifier=joblib.load(r'/Users/praveen/Documents/Study/Projects/Nutrition_model.sav')
#------------------------------------------------------------------------------------------------------------------
def get_input(input_pdf,input_pdf_location):
    if input_pdf.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(input_pdf), mode='rb', username=smb_username,password=smb_password) as f:
                with open(input_pdf_location, 'wb') as pdf:
                    pdf.write(f.read())
                print('file found')
        finally:
            smbclient.reset_connection_cache()
            return input_pdf_location
            # return self.input_pdf_location
    else:
        return document_location+input_pdf
#------------------------------------------------------------------------------------------------------------------
def pdf_to_image(input_pdf,document_location):
    images = convert_from_path(input_pdf)
    for index, image in enumerate(images):
        image.save(f'{document_location}/{index + 1}.png')
    return 'success'
# ------------------------------------------------------------------------------------------------------------------
def find_contours(input_image,area=25000,sub_contour_area=500):
    im = cv2.imread(input_image)
    height = im.shape[0]
    width = im.shape[1]

    lap = np.uint8(np.absolute(cv2.Laplacian(im,ddepth=cv2.CV_64F,ksize=1)))
    # intensify non black pixels to white
    lap[np.any(lap != [0, 0, 0], axis=-1)] = [255,255,255]
    # converting to gray (2 dimensional)
    lap_gray = cv2.cvtColor(lap, cv2.COLOR_BGR2GRAY)
    # horizontal lines
    horizontal_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, tuple([30,1]))
    horizontal_lines = cv2.morphologyEx(lap_gray, cv2.MORPH_OPEN, horizontal_kernel, iterations=2)
    # Vertical lines
    vertical_kernel = cv2.getStructuringElement(cv2.MORPH_RECT, tuple([1, 30]))
    vertical_lines = cv2.morphologyEx(lap_gray, cv2.MORPH_OPEN, vertical_kernel, iterations=2)
    table = cv2.add(horizontal_lines, vertical_lines)
    table = cv2.dilate(table,kernel=tuple([1,5]),iterations=5)
    table = cv2.erode(table,kernel=tuple([1,5]),iterations=5)

    cv2.imwrite(f"{document_location}table.png", table)
    cnts,hierarchy = cv2.findContours(table.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)

    selected_contour_index = []
    for index in range(len(cnts)):
        if cv2.contourArea(cnts[index]) > area:
            selected_contour_index.append(index)

    # print("selected_contours_index----->",selected_contour_index)

    sub_contours = []
    sub_contours_area = []
    for chosen_contour_index in selected_contour_index:
        for i in range(len(hierarchy[0])):
            if hierarchy[0][i][3] in selected_contour_index:
                sub_contour = cnts[i]
                area = cv2.contourArea(sub_contour)
                if area > sub_contour_area and area < 100000:  # Replace with your desired area condition
                    # print("area----->",area)
                    sub_contours.append(sub_contour)
                    sub_contours_area.append(area)
    # print("len of sub contours----->",len(sub_contours))
    # print("max_area----->",max(sub_contours_area))
    duplicate = im.copy()
    for s_contour in sub_contours:
        x1, y1, w1, h1 = cv2.boundingRect(s_contour)
        sss = cv2.rectangle(duplicate, (x1, y1), (x1 + w1, y1 + h1), (255, 0, 0), 2)
        cv2.imwrite(f"{document_location}edited2.png", sss)
        yield (width / (x1 - 10), height / (y1 - 10), width / (x1 + w1 + 20), height / (y1 + h1 + 30))
# ------------------------------------------------------------------------------------------------------------------
def convert_coordinates(input_pdf, page_no, coordinates_percent):
    pdf = pdfplumber.open(input_pdf)
    page = pdf.pages[page_no - 1]
    height, width = float(page.height), float(page.width)
    w0, h0, w1, h1 = coordinates_percent
    coordinates = (width / w0, (height / h0)-5, width / w1, (height / h1)-5)
    yield coordinates
# ------------------------------------------------------------------------------------------------------------------
def extract_list_text(input_pdf,document_location,page_no):
    temp=[]
    pdf=fitz.Document(input_pdf)
    page=pdf[int(page_no)-1]
    input_image = f'{document_location}/{page_no}.png'
    # Area - 1lac targets the net contents , if required change these values
    for contour in find_contours(input_image, area=100000, sub_contour_area=11000):
        # print(contour)
        for coor in convert_coordinates(input_pdf, int(page_no), contour):
            # print(coor)
            temp.append(page.get_textbox(coor))
    return temp

# ------------------------------------------------------------------------------------------------------------------
# Data Extraction
def data_extraction(path, page):
    doc = fitz.Document(path)
    data_blocks = doc[page - 1].get_text("blocks")
    data = [list(block)[4].strip() for block in data_blocks]
    return data
# -------------------------------------------------------------------------------------------------------------------------------------
# Nutrition Table Selection
def nutri_data(data):
    temp = []
    cal = 0
    dv = 0
    for index, text in enumerate(data):
        if 'Calories' in text and len(text) < 20:
            temp.append(index)
            cal = cal + 1
        elif '* The % Daily Value (DV)' in text:
            temp.append(index)
            dv = dv + 1
            break
    if len(temp) == 2 and cal == 1 and dv == 1:
        return data[temp[0]:(temp[1])], temp[0]  # ,list(range(temp[0],temp[1]+1))
    else:
        return False


# -------------------------------------------------------------------------------------------------------------------------------------
# Grouping Names and values in Nutriton data
def get_nutrition_data(x):
    element_list = []
    value_list = []
    regex_extracted = re.findall(
        r"([\w\,\-\s]*?)\s+(\<?\s?\-?\d{0,3}\.?\d{0,2}\s?(%|g added sugars|g|kj|kcal|mg|mcg|cal))", x, flags=re.I)
    if not regex_extracted:
        regex_extracted = re.findall(r"([\w\,\-\s]*?)\s+((\<?\s?\-?\d{0,3}\.?\d{0,2}\s?))", x, flags=re.I)
    for tuple_content in regex_extracted:
        if tuple_content[0] and tuple_content[0].strip() not in ("-"):
            element_list.append(tuple_content[0])
        if tuple_content[1]:
            value_list.append(tuple_content[1])
    return " ".join(element_list).strip(), value_list


# ------------------------------------------------------------------------------------------------------------------
# Nutrition Dictionary
def nutri_type1(nutrition_data):
    keys = []
    values = []

    for i in nutrition_data:
        if 'Daily' not in i:
            i = i.replace('(', '').replace(')', '')
            # Calories needs to be corrected '160 Calories' to 'Calories 160' to suit the get_nutrition_data function
            if i[0].isdigit():
                if '\n' in i:
                    temp = i.split('\n')
                    temp = temp[1] + ' ' + temp[0]
                else:
                    temp = i.split(' ', 1)
                    temp = temp[1] + ' ' + temp[0]

                content = get_nutrition_data(temp)

                keys.append(content[0])
                values.append(content[1])
            else:
                content = get_nutrition_data(i)
                keys.append(content[0])
                values.append(content[1])

    return keys, values


# ------------------------------------------------------------------------------------------------------------------
def nutri_type2(nutrition_data):
    keys = []
    values = []
    for i in nutrition_data:
        i = i.replace('\n', ' ').replace('(', '').replace(')', '').replace('Incl.', '')
        if 'DV' not in i:
            temp = i.strip().split(' ')
            if 'calories' not in i.lower():
                el = []
                # ks=[]
                s = 0
                for j in temp:
                    if j.strip() != '%' and j.strip():
                        if j.isdigit():
                            el.append(j + '%')
                        elif j.isalpha():
                            # ks.insert(s,j)
                            el.insert(s, j)
                            s = s + 1
                        else:
                            el.append(j)

                content = get_nutrition_data(' '.join(el))
                keys.append(content[0])
                values.append(content[1])
            else:
                # Calories
                keys.append(temp[0])
                values.append([v for v in temp[1:]])

    return keys, values


# ------------------------------------------------------------------------------------------------------------------
def nutri_keys_val(keys, values):
    nut = {}
    for index, i in enumerate(keys):
        i = i.replace('DFE', '').replace('less than', '')
        prob = nutrition_classifier().predict_proba(laser.embed_sentences(i, lang='en'))[0]
        prob.sort()
        nkey_temp = ''
        if prob[-1] > 0.85:
            nkey_temp = nutrition_classifier().predict(laser.embed_sentences(i, lang='en'))[0]
        else:
            nkey_temp = i
        temp = []
        for value in values[index]:
            if '%' in value:
                temp.append({'PDV': {'en': value.replace(' ', '')}})
            else:
                temp.append({'Value': {'en': value}})

        if str(nkey_temp) in nut:
            nut[str(nkey_temp)].extend(temp)
        else:
            nut[str(nkey_temp).strip()] = temp
    return nut


# ------------------------------------------------------------------------------------------------------------------
# General Information
def general(data):
    keys = []
    values = []
    nets = []
    general_elements = {'label version': 'LABEL_VERSION',
                        '* the % daily value (dv)': 'NUTRITION_TABLE_DECLARATION',
                        'per container': 'SERVING_SIZE', 'serving size': 'SERVING_SIZE'}
    matches = ['oz', 'net wt', 'kg']
    for index, i in enumerate(data):
        if i.strip() == 'g)':
            data[index - 1] = data[index - 1] + data[index]
    for index, j in enumerate(data):
        temp = [ge for ge in general_elements if ge in j.lower() and 'disclose' not in j.lower() and len(j) < 200]
        if any(1 for k in matches if k in j.lower()) and 'and' not in j.lower():
            pass
        elif j.startswith('CONTAINS') or j.startswith('MAY CONTAINS'):
            keys.append('ALLERGEN_STATEMENT')
            values.append([{classify(j)[0]: j}])
        elif j.lower().startswith('ingredients'):
            keys.append('INGREDIENTS_DECLARATION')
            values.append([{classify(j)[0]: j}])
        elif temp:
            for pe in temp:
                keys.append(general_elements[pe])
                values.append([{classify(j)[0]: j}])
        else:
            keys.append('Unmapped')
            values.append([{classify(j)[0]: j}])
    gen = {}
    for index, i in enumerate(keys):
        if i in gen:
            gen[i].extend(values[index])
        else:
            gen[i] = values[index]
    return gen



# ------------------------------------------------------------------------------------------------------------------

def quaker_main(input_file,pages):
    output = {}
    temp_dir = tempfile.TemporaryDirectory(dir=document_location)
    input_pdf_location = f'{temp_dir.name}/input_pdf.pdf'
    # Status
    input_file= get_input(input_file,input_pdf_location)
    pdf_to_image(input_file, temp_dir.name)
    page_numbers = [int(x) for x in pages.split(",")]
    for page in page_numbers:
        temp = extract_list_text(input_file,temp_dir.name, str(page))
        net_weight = [*set(content for content in temp if 'net wt' in content.lower() or 'oz' in content.lower())]
        net_weight = [{classify(x)[0]:x.strip()} for x in net_weight]
        print(net_weight)
        data = data_extraction(input_file, page)
        nutrition_data = nutri_data(data)
        nut = {}
        if nutrition_data:
            if data[nutrition_data[1]].startswith('Calories'):
                temp = [want for want in data if want not in nutrition_data[0]]
                keys, values = nutri_type2(nutrition_data[0])


            else:
                temp = [want for want in data if want not in nutrition_data[0]]
                keys, values = nutri_type1(nutrition_data[0])

            nut = nutri_keys_val(keys, values)
            gen = general(temp)
            if net_weight:
                gen['NET_CONTENT'] = net_weight
            output[page] = {**gen, **{'NUTRITION_FACTS': [nut]}}


        else:
            gen=general(data)
            if net_weight:
                gen['NET_CONTENT'] = net_weight
            output[page] = general(data)

    return output
# ------------------------------------------------------------------------------------------------------------------