import openpyxl
import io
from xlsxwriter.utility import xl_rowcol_to_cell,xl_col_to_name

from math import ceil

from decimal import Decimal

from .utils import GoogleTranslate

from .excel_processing import *

from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

# mapping_dict = {'Energy': ('energy','Wartość energetyczna','Energiat','Enerģētiskā vērtība',' Energinė vertė','Energetická hodnota','Energia'),
#                 'Fat': ('Matières grasses','Tłuszcz','Rasva','Tauki',' Riebalų','Tuky','Zsír'),
#                 'Saturates':('dont acides gras saturés','of which saturates','saturates','w tym kwasy nasycone','millest küllastunud','tostarp piesātinātās taukskābes','z toho nasycené mastné kyseliny'),
#                 'Carbohydrate': ('Glucides','Carbohydrates','Węglowodany','Süsivesikuid','Ogļhidrāti','Angliavandenių','Sacharidy'),
#                 'Sugars': ('dont sucres','OF WHICH SUGARS','sugars','sugar','of which sugars','w tym cukry','millest suhkrut','tostarp cukurs',' kuriuose cukrų','z toho cukry'),
#                 'Fibre': ('Fibre','Kiudaineid','Šķiedrvielas','Skaidulinių medžiagų','Vláknina','Vláknina','Rost'),
#                 'Protein': ('Protéines','Białko','Protein','Valku','Olbaltumvielas','Baltymų','Bílkoviny','Fehérje'),
#                 'Salt': ('Sel','Salt','Sól','Soola','Sāls',' Druskų','Sůl','Soľ'),
#                 'None':('grammage')
#                 }

# output_file = io.BytesIO()

# def c_round(number,decimal):
#     number_of_decimal_places = abs(Decimal(str(number)).as_tuple().exponent)
#     if number_of_decimal_places > 0 and decimal < number_of_decimal_places:
#         if str(number)[-1] == "5":
#             return ceil(number * 10 ** decimal) / 10 ** decimal
#         return round(number,decimal)
#     else:
#         return round(number,decimal)

def c_round(number, decimal):
    number_of_decimal_places = lambda number: abs(Decimal(str(number)).as_tuple().exponent)
    custom_round = lambda number, decimal: ceil(number * 10 ** decimal) / 10 ** decimal

    if number_of_decimal_places(number) == decimal + 1 and str(number)[-1] == "5":
        return custom_round(number, decimal)
    else:
        return np.round(number, decimal)

def get_file(file,output_file):
    if file.startswith('\\'):
        print('connecting to SMB share')
        try:
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                output_file.write(f.read())
                output_file.seek(0)
                print('file found')
        except:
            smbclient.reset_connection_cache()
            with smbclient.open_file(r"{}".format(file), mode='rb', username=smb_username,
                                     password=smb_password) as f:
                output_file.write(f.read())
                output_file.seek(0)
                print('file found')
        finally:
            smbclient.reset_connection_cache()
        return 'SMB'
    else:
        return 'LOCAL'

def cell_column_letter(cell):
    try:
        return cell.column_letter
    except:
        return re.search(r"[A-Z]", cell.coordinate).group()

def convert_to_dataframe(input_excel,sheet_name):
    position = {}
    Excel = openpyxl.load_workbook(input_excel, data_only=True)
    if sheet_name in Excel.sheetnames:
        sheet = Excel[sheet_name]
        final_list = []
        for row in sheet:
            row_list = []
            for cell in row:
                if re.search(r"(\d\.?\d{0,2})\"?(.*)\"?", str(cell.number_format)) and not sheet.column_dimensions[cell_column_letter(cell)].hidden and not sheet.row_dimensions[cell.row].hidden:
                    decimal_text = re.search(r"(\d\.?\d{0,2})\"?(.*)\"?", str(cell.number_format)).group(1)
                    suffix_text = re.search(r"(\d\.?\d{0,2})\"?(.*)\"?", str(cell.number_format)).group(2)
                    suffix, number_of_decimal_points = None, None
                    if decimal_text:
                        number_of_decimal_points = len(decimal_text.split(".")[-1]) if "." in decimal_text else 0
                        # print(f"{cell.value}-------{cell.number_format}------{number_of_decimal_points}")
                    if suffix_text:
                        suffix = re.sub(r"[^A-Za-z%]", "", suffix_text)
                    if suffix and "%" in suffix:
                        try:
                            value = f"{int(round(cell.value * 100))}%"
                        except:
                            value = cell.value
                    else:
                        # print(cell.coordinate, cell.value, f"---{cell.number_format}------")
                        try:
                            print("inside try")
                            # cell.number_format = "".join(("#,##",cell.number_format))

                            print("ccell------>",cell.value)
                            print("ccell------>",number_of_decimal_points)
                            # value = (f"{cell.value}.{number_of_decimal_points}f{suffix}")
                            if number_of_decimal_points > 0:
                                value = float(c_round(cell.value, number_of_decimal_points))       # custom round function
                            else:
                                value = int(c_round(cell.value,0))
                            if suffix:
                                value = f"{value} {suffix}"
                            # print("value---->",value)
                        except:
                            # print("inside except")
                            value = cell.value
                            # print(cell.coordinate, value, f"---{cell.number_format}------")
                    value = str(value).replace(">","&gt;").replace("<","&lt;")
                    row_list.append(value)
                    position[value] = cell.coordinate
                elif sheet.column_dimensions[cell_column_letter(cell)].hidden or sheet.row_dimensions[cell.row].hidden:
                    value = "None"
                    row_list.append(value)
                    position[value] = cell.coordinate
                else:
                    # print(cell.coordinate, cell.value, f"---{cell.number_format}------")
                    value = str(cell.value).replace(">", "&gt;").replace("<", "&lt;")
                    row_list.append(value)
                    position[value] = cell.coordinate
            final_list.append(row_list)
            # print('-----' * 10)
        df = pd.DataFrame(final_list)
        return df , position

def excel_type_classification(df) -> str:
    rows,columns = df.shape
    for col in range(columns):
        for row in range(rows):
            cell_value = df[col][row]
            if cell_value:
                cell_value = str(df[col][row]).lower().strip()
                # if cell_value in ("back of pack typical nutritional values","calculator pc"):
                if cell_value in ("back of pack","back of pack typical nutritional values","calculator pc"):
                    return "T1"
                elif cell_value in "labelling recommendation":
                    return "T2"
                else:
                    pass

def master_nutrition_finder(text):
    text = text.split("/")
    if os.path.exists(master_nutrition_model_location):
        master_nutrition_model = joblib.load(master_nutrition_model_location)
    else:
        master_nutrition_model = training_dataset()
    result = master_nutrition_model.predict(laser.embed_sentences(text, lang="en"))
    probability = master_nutrition_model.predict_proba(laser.embed_sentences(text, lang="en"))
    probability[0].sort()
    max_probability = max(probability[0])
    # print(max_probability, '------>', result)
    if max_probability > 0.80:
        return {'output':result[0],'probability':max_probability}
    else:
        return {'output': 'None', 'probability': max_probability}

def type1_nutrition_table_extraction(df,position=None):
    nutrition_header1 = ('energy','energy per','fat','kcal','saturates','carbohydrate','fibre','sugar','salt','of which saturates','of which sugars','protein','sugars')
    temp_dict = {}
    nutrition_list = []
    final_dict = {}
    nutrition_contents_available = False
    # rows,columns = df.shape
    rows,columns = list(df.index.values),list(df.columns.values)
    row_start_index = find_start_row_position(df)
    if row_start_index:
        df1 = df.copy(deep=True)
        df1 = df1.loc[row_start_index:row_start_index+5]
        # df1 = df1.reset_index(drop=True)
        print("row_start index_table---->",df1)
        row_indexes = list(df1.index.values)
        col_indexes = list(df1.columns.values)
        _rows, _columns = df1.shape
        index_to_cut_off = [_row for _column in col_indexes for _row in row_indexes if
                            ":" in str(df1[_column][_row]) and "100" in str(df1[_column][_row])]
        # print(df1.loc[index_to_cut_off].values)
        # print("index_to_cutoff----->", index_to_cut_off)
        #########   capturing last energy value
        list_to_join = df1.loc[index_to_cut_off,].values[0]
        # list_to_join = [content for content in list_to_join if str(content) not in ("None", "none")]
        joined_text = " ".join(list_to_join)
        if re.search(r"100\s?g", joined_text.lower()) and "kj" in joined_text.lower() and "kcal" in joined_text.lower():
            if "Nutrition Information" not in final_dict:
                for index,value in enumerate(list_to_join):
                    if value and str(value) not in ("None","none"):
                        header = "Nutrition Information"
                        if header in final_dict:
                            final_dict[header].append({f"{xl_rowcol_to_cell(index_to_cut_off[0],index)}_en":value})
                        else:
                            final_dict[header] = [{f"{xl_rowcol_to_cell(index_to_cut_off[0],index)}_en":value}]
            # final_dict["Nutrition Information"] = joined_text
            # print("0000000000000-------------->",joined_text)
        ##########
        if index_to_cut_off:
            df1 = df1.loc[:index_to_cut_off[0]-1]
            # print(df1)
            # df1 = df1.reset_index(drop=True)
        df1 = df1.T
        # print(df1)
        nutrition = normal_nutrition_table_extraction(df1,type="row")
        nutrition.pop("glossary",None)              # deleting glossary
        # print("row nutrition----->",nutrition)
        nutrition_list.append(nutrition)
    for col in columns[:1]:
        for row in rows:
            cell_value = df[col][row]
            if cell_value and str(cell_value).lower() not in ("none"):
                cell_value = str(cell_value).lower().strip()
                if cell_value == "kcal":
                    cell_value = "energy"
                if cell_value in ("ingredient","front of pack traffic lights","back of pack typical nutritional values","front of pack","back of pack"):
                    if temp_dict:
                        nutrition_list.append(temp_dict)
                        # print("appending nutrition table---->", nutrition_list)
                    temp_dict = {}
                    print('nutrition data available')
                    nutrition_contents_available = True
                elif  cell_value in ('back  of pack recycling and disposal information',"for r&d use only - r&d sign off"):
                    if temp_dict:
                        nutrition_list.append(temp_dict)
                        # print("appending nutrition table---->", nutrition_list)
                    temp_dict = {}
                    nutrition_contents_available = False
                    print("ending the program")
                    final_dict["Nutrition_Facts"] = nutrition_list
                    return final_dict
                elif nutrition_contents_available:
                    cell_value = str(cell_value).lower().strip()
                    result = master_nutrition_finder(cell_value)
                    if (cell_value in nutrition_header1) or (result["output"] not in ("None","Nutrition information") and result["probability"] > 0.80):
                        # print('inside nutrition header check----->',cell_value)
                        if result["output"] in ("None"):
                            header = cell_value
                        else:
                            header = result["output"]
                        for _col_in in columns[columns.index(col)+1:]:
                            column_value = df[_col_in][row]
                            if column_value and (re.search(r"\d",str(column_value)) or re.search(r"\b(kj|kcal|g)\b",str(column_value),flags=re.I)):
                                column_value = str(df[_col_in][row])
                                inner_header = "Unit" if re.search(r"\b(kj|kcal|g)\b",str(column_value),flags=re.I) else ("PDV" if "%" in column_value else "Value")
                                # cell_position = position[column_value]
                                cell_position = xl_rowcol_to_cell(row,_col_in)
                                if header in temp_dict:
                                    temp_dict[header].append({inner_header:{f"{cell_position}_en":column_value}})
                                else:
                                    temp_dict[header] = [{inner_header:{f"{cell_position}_en":column_value}}]
                    elif re.search(r"100\s?g"," ".join(df.loc[row,].to_list()).lower()) and "kj" in " ".join(df.loc[row,].to_list()).lower().lower() and "kcal" in " ".join(df.loc[row,].to_list()).lower().lower():
                        list_to_join = df.loc[row,].to_list()
                        if "Nutrition Information" not in final_dict:
                            for index, value in enumerate(list_to_join):
                                if value and str(value).lower() not in ("none"):
                                    header = "Nutrition Information"
                                    if header in final_dict:
                                        final_dict[header].append({f"{xl_rowcol_to_cell(row, index)}_en": value})
                                    else:
                                        final_dict[header] = [{f"{xl_rowcol_to_cell(row, index)}_en": value}]
            elif not cell_value and nutrition_contents_available:
                if "kcal" in df.loc[row,].to_list():
                    header = "energy"
                    for _col_in in columns[columns.index(col)+1:]:
                        column_value = df[_col_in][row]
                        if column_value and (re.search(r"\d",str(column_value)) or re.search(r"\b(kj|kcal|g)\b",str(column_value),flags=re.I)):
                            column_value = str(df[_col_in][row])
                            inner_header = "Unit" if re.search(r"\b(kj|kcal|g)\b",str(column_value),flags=re.I) and not re.search(r"\d",str(column_value)) else ("PDV" if "%" in column_value else "Value")
                            # cell_position = position[column_value]
                            cell_position = xl_rowcol_to_cell(row,_col_in)
                            if header in temp_dict:
                                temp_dict[header].append({inner_header: {f"{cell_position}_en":column_value}})
                            else:
                                temp_dict[header] = [{inner_header: {f"{cell_position}_en":column_value}}]
            elif str(cell_value).lower() in ("none","energy per 100g") and nutrition_contents_available:
                list_to_join = df.loc[row,].to_list()
                # list_to_join = [content for content in list_to_join if str(content) not in ("None","none")]
                joined_text = " ".join(list_to_join)
                if "Nutrition Information" not in final_dict:
                    if re.search(r"100\s?g",joined_text.lower()) and "kj" in joined_text.lower() and "kcal" in joined_text.lower():
                        for index, value in enumerate(list_to_join):
                            if value and str(value).lower() not in ("none"):
                                header = "Nutrition Information"
                                if header in final_dict:
                                    final_dict[header].append({f"{xl_rowcol_to_cell(row,index)}_en": value})
                                else:
                                    final_dict[header] = [{f"{xl_rowcol_to_cell(row, index)}_en": value}]
                    # final_dict["Nutrition Information"] = joined_text
                    # print("0000000000000000000000000000----------->",final_dict)
    final_dict["Nutrition_Facts"] = nutrition_list
    return final_dict

# x1 = type1_nutrition_table_extraction(df)

def find_start_column_position(df) -> int:
    value_check = ['energy', 'fat', 'protein', 'fibre', 'salt', 'sugar', 'sugars','of which sugars']
    rows , columns  = df.shape
    for col in range(columns):
        column_value_list =  df.iloc[:,col].to_list()
        convert_to_lower = lambda x: str(x).lower()
        column_value_list = list(map(convert_to_lower,column_value_list))
        if len(set(column_value_list).intersection(set(value_check))) > 3:
            return col
    for col in range(columns)[:5][::-1]:
        column_value_list = df.iloc[:, col].to_list()
        convert_to_lower = lambda x: str(x).lower()
        column_value_list = list(map(convert_to_lower, column_value_list))
        column_value_list = [value for value in column_value_list if value != "none"]
        # print(column_value_list)
        column_laser_checked_value = [master_nutrition_finder(nutrition)['output'] for nutrition in column_value_list]
        # column_laser_checked_value = [nutrition_column_finder(nutrition) for nutrition in column_value_list]
        column_laser_checked_value = [value.lower().strip() for value in column_laser_checked_value if value]
        # print(column_laser_checked_value)
        if len(set(column_laser_checked_value).intersection(set(value_check))) > 3:
            return col

def find_start_row_position(df) -> int:
    value_check = ['energy', 'fat', 'protein', 'fibre', 'salt', 'sugar', 'sugars', 'of which sugars','saturates']
    rows , columns  = df.shape
    for row in range(rows):
        row_value_list =  df.loc[row,].to_list()
        convert_to_lower = lambda x: str(x).lower()
        row_value_list = list(map(convert_to_lower,row_value_list))
        if len(set(row_value_list).intersection(set(value_check))) > 3:
            return row
    for row in range(rows):
        row_value_list =  df.loc[row,].to_list()
        convert_to_lower = lambda x: str(x).lower()
        row_value_list = list(map(convert_to_lower,row_value_list))
        row_value_list = [value for value in row_value_list if value != "none"]
        row_laser_checked_value = [master_nutrition_finder(nutrition)['output'] for nutrition in row_value_list]
        # row_laser_checked_value = [nutrition_column_finder(nutrition) for nutrition in row_value_list]
        row_laser_checked_value = [value.lower().strip() for value in row_laser_checked_value if value]
        # print(row_laser_checked_value)
        if len(set(row_laser_checked_value).intersection(set(value_check))) > 3:
            return row

def normal_nutrition_table_extraction(df,type=None):
    # print("inside normal ntrition table")
    nutrition_header1 = ('energy','energy per','fat', 'kcal', 'saturates', 'carbohydrate', 'fibre', 'sugar', 'salt', 'of which saturates',
    'of which sugars', 'protein', 'sugars')
    temp_dict = {}
    glossary_dict = {}
    # rows, columns = df.shape
    rows = list(df.index.values)
    columns = list(df.columns.values)
    # print("rows----->",rows)
    # print("columns----->",columns)
    # print(df)
    for col in columns[:1]:
        for row in rows:
            cell_value = df[col][row]
            if not cell_value or str(cell_value) == "None":
                # print("illada----------->",df.loc[row].tolist())
                # print("illada")
                row_content = df.loc[row].tolist()
                row_content = [row_value for row_value in row_content if row_value]
                joined_row = " ".join(row_content).strip()
                if "kcal" in joined_row.lower():
                    cell_value = "Energy"
                if "*" in joined_row:
                    # print("illada----------->", df.loc[row].tolist())
                    if df[col][row-1]:
                        cell_value = df[col][row-1]
            if cell_value and ":" not in str(cell_value):
                cell_value = str(cell_value).lower().strip()
                result = master_nutrition_finder(cell_value)
                if (cell_value in nutrition_header1) or (result["output"] not in ("None","Nutrition information") and result["probability"] > 0.70):
                # if cell_value in nutrition_header1:
                #     print('inside nutrition header check----->', cell_value, '-------->', result["output"])
                    if result["output"] in ("None"):
                        header = cell_value
                    else:
                        header = result["output"]
                    for _col_in in columns[columns.index(col) + 1:]:
                        column_value = df[_col_in][row]
                        # print("hhhhhhhhh------->",column_value)
                        if column_value and ":" not in str(column_value) and (re.search(r"[\d\*]", str(column_value)) or re.search(r"\b(kj|kcal|g)\b", str(column_value),
                                                                                              flags=re.I)):
                            column_value = str(df[_col_in][row])
                            inner_header = "Unit" if re.search(r"(kj|kcal|g|\*)", str(column_value), flags=re.I) and not re.search(r"\d",str(column_value)) else (
                                "PDV" if "%" in column_value else "Value")
                            # cell_position = position[column_value]
                            if type == "row":
                                cell_position = xl_rowcol_to_cell(_col_in, row)
                            else:
                                cell_position = xl_rowcol_to_cell(row,_col_in)
                            if header in temp_dict:
                                temp_dict[header].append({inner_header: {f"{cell_position}_en":column_value}})
                            else:
                                temp_dict[header] = [{inner_header: {f"{cell_position}_en":column_value}}]
                        elif column_value:               #for glossary value retrive

                            column_value = str(column_value)
                            # inner_result = master_nutrition_finder(column_value)
                            if column_value.strip() and column_value not in ("None"):
                                # lang = classify(column_value)[0]
                                with GoogleTranslate(column_value) as output:
                                    lang = output["language"]
                                if type == "row":
                                    cell_position = xl_rowcol_to_cell(_col_in, row)
                                else:
                                    cell_position = xl_rowcol_to_cell(row, _col_in)
                                if header in glossary_dict:
                                    glossary_dict[header].append({f"{cell_position}_{lang}":column_value})
                                else:
                                    glossary_dict[header] = [{f"{cell_position}_{lang}":column_value}]
                '''
                else:
                    print("ulla illada------->",cell_value,'------->',df.loc[row].tolist())
                    row_content = df.loc[row].tolist()
                    row_content = [row_value for row_value in row_content if row_value]
                    joined_row = " ".join(row_content)
                    if "kcal" in joined_row.lower():
                        header = "Energy"
                        for _col_in in columns[columns.index(col) + 1:]:
                            column_value = df[_col_in][row]
                            if column_value and ":" not in str(column_value) and (
                                    re.search(r"\d", str(column_value)) or re.search(r"\b(kj|kcal|g)\b",
                                                                                     str(column_value),
                                                                                     flags=re.I)):
                                column_value = str(df[_col_in][row])
                                inner_header = "Unit" if re.search(r"\b(kj|kcal|g)\b", str(column_value),
                                                                   flags=re.I) and not re.search(r"\d",
                                                                                                 str(column_value)) else (
                                    "PDV" if "%" in column_value else "Value")
                                # cell_position = position[column_value]
                                if type == "row":
                                    cell_position = xl_rowcol_to_cell(_col_in, row)
                                else:
                                    cell_position = xl_rowcol_to_cell(row, _col_in)
                                if header in temp_dict:
                                    temp_dict[header].append({inner_header: {f"{cell_position}_en": column_value}})
                                else:
                                    temp_dict[header] = [{inner_header: {f"{cell_position}_en": column_value}}]
                            elif column_value:  # for glossary value retrive

                                column_value = str(column_value)
                                # inner_result = master_nutrition_finder(column_value)
                                if column_value.strip() and column_value not in ("None"):
                                    lang = classify(column_value)[0]
                                    # with GoogleTranslate(column_value) as output:
                                    #     lang = output["language"]
                                    if type == "row":
                                        cell_position = xl_rowcol_to_cell(_col_in, row)
                                    else:
                                        cell_position = xl_rowcol_to_cell(row, _col_in)
                                    if header in glossary_dict:
                                        glossary_dict[header].append({f"{cell_position}_{lang}": column_value})
                                    else:
                                        glossary_dict[header] = [{f"{cell_position}_{lang}": column_value}]
                '''

    # print("glossary dict--------->",glossary_dict)
    temp_dict['glossary'] = glossary_dict
    return temp_dict

def type2_nutrition_table_extraction(df,position=None):
    nutrition_list = []
    temp_dict = {}
    # df_original = df.copy(deep=True)
    row_start_index = find_start_row_position(df)
    col_start_index = find_start_column_position(df)
    print("row start index---->",row_start_index)
    print("column start index---->",col_start_index)
    if row_start_index:
        print("row index exists")
        local_df = df[row_start_index:row_start_index+10]
        # local_df = local_df.reset_index(drop=True)
        # print(local_df)
        # x1 = local_df[0].to_list()
        # rows , columns = local_df.shape
        rows , columns = list(local_df.index.values) , list(local_df.columns.values)
        index_to_cut_off = [row for column in columns for row in rows if ":" in str(local_df[column][row]) and "100" in str(local_df[column][row])]
        # print("index_to_cutoff----->",index_to_cut_off)
        #########   capturing last energy value
        list_to_join = local_df.loc[index_to_cut_off,].values[0]
        # list_to_join = [content for content in list_to_join if str(content) not in ("None", "none")]
        joined_text = " ".join(list_to_join)
        if re.search(r"100\s?g", joined_text.lower()) and "kj" in joined_text.lower() and "kcal" in joined_text.lower():
            for index, value in enumerate(list_to_join):
                if value and str(value) not in ("None", "none"):
                    header = "Nutrition Information"
                    if header in temp_dict:
                        temp_dict[header].append({f"{xl_rowcol_to_cell(index_to_cut_off[0], index)}_en": value})
                    else:
                        temp_dict[header] = [{f"{xl_rowcol_to_cell(index_to_cut_off[0], index)}_en": value}]
            # temp_dict["Nutrition Information"] = joined_text
            # print("0000000000000-------------->",joined_text)
        ##########
        if index_to_cut_off:
            local_df = local_df.loc[:index_to_cut_off[0] - 1]
            # print(local_df)
            # local_df = local_df.reset_index(drop=True)
        local_df = local_df.T
        # print('inverted_df----->',local_df)
        nutrition = normal_nutrition_table_extraction(local_df,type='row')
        nutrition.pop("glossary",None)                  # deleting glossary
        nutrition_list.append(nutrition)
        df = df[:row_start_index]         # this is to be used by another table , so that this table wont interfere
    if col_start_index and row_start_index:
        df = df.iloc[:,col_start_index:]
        # print("*"*10)
        # print("normal table----->", df)
        # print("*" * 10)
        # df.columns = range(df.shape[1])
        nutrition = normal_nutrition_table_extraction(df)
        if "glossary" in nutrition:
            if nutrition["glossary"]:
                # temp_dict["glossary"] = nutrition["glossary"]    # deleting glossary
                temp_dict = {**temp_dict,**nutrition["glossary"]}    # deleting glossary
        nutrition.pop("glossary",None)                  # deleting glossary
        nutrition_list.append(nutrition)
    if col_start_index and not row_start_index:
        # print('inside exception content processing')
        df = df.iloc[:,col_start_index:]
        # df.columns = range(df.shape[1])
        # rows, columns = df.shape
        rows, columns = list(df.index.values),list(df.columns.values)
        for col in columns[:1]:
            for row in rows:
                cell_value = df[col][row]
                if cell_value:
                    cell_value = str(cell_value).lower().strip()
                    nutrition_output = master_nutrition_finder(cell_value)
                    if nutrition_output['output'] not in ['None'] and nutrition_output['probability'] > 0.80:
                        # print('inside nutrition header check----->', cell_value)
                        header = nutrition_output['output']
                        for _col_in in columns[columns.index(col) + 1:]:
                            column_value = df[_col_in][row]
                            # lang = classify(column_value)
                            with GoogleTranslate(column_value) as output:
                                lang = output["language"]
                            # cell_position = position[column_value]
                            cell_position = xl_rowcol_to_cell(row,_col_in)
                            if header in temp_dict:
                                temp_dict[header].append({f"{cell_position}_{lang}":column_value})
                            else:
                                temp_dict[header] = [{f"{cell_position}_{lang}": column_value}]
    temp_dict['Nutrition_Facts'] = nutrition_list
    return temp_dict

def main(input_excel,sheet_names):
    final_dict = {}
    output_file = io.BytesIO()
    out = get_file(input_excel,output_file)
    if out == 'SMB':
        input_excel = output_file
    else:
        input_excel = document_location + input_excel
    for sheet_name in sheet_names.split(","):
        sheet_dict = {}
        df , position = convert_to_dataframe(input_excel,sheet_name)
        excel_type = excel_type_classification(df)
        # print("*"*10)
        # print('excel type ---->',excel_type)
        # print("df------>",df.values.tolist())
        # print("*" * 10)
        if excel_type == "T1":
            # print("Type 1")
            nutrition_output = type1_nutrition_table_extraction(df,position)
            # sheet_dict['Nutrition_Facts'] = nutrition_output
            sheet_dict = nutrition_output
        elif excel_type == "T2":
            # print("Type 1")
            nutrition_output = type2_nutrition_table_extraction(df,position)
            sheet_dict = nutrition_output
        else:
            print('this format is not supported')
        final_dict[sheet_name] = sheet_dict
    try:
        output_file.truncate(0)
        output_file.close()
    except:
        pass
    return final_dict

def training_dataset():
    print("training_dataset")
    dataset_location = master_nutrition_dataset_location
    df = pd.read_excel(dataset_location)
    df = df.sample(frac=1)
    X_train_laser = laser.embed_sentences(df['text'], lang='en')
    mlp = MLPClassifier(hidden_layer_sizes=(80,), solver='adam', activation='tanh', max_iter=750, random_state=0,shuffle=True)
    mlp.fit(X_train_laser, df['category'])
    joblib.dump(mlp, master_nutrition_model_location)
    return mlp
