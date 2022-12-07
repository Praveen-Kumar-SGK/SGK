from xlsxwriter.utility import xl_rowcol_to_cell
import tempfile
from .excel_processing import *
import openpyxl
from math import ceil

from decimal import Decimal


# document_location = r"/Users/sakthivel/Documents/SGK/Fontom/"
classifier=joblib.load(fontem_model_location)


def get_input(input_file, input_excel_location):
  if input_file.startswith('\\'):
    print('connecting to SMB share')
    try:
      with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                               password=smb_password) as f:
        with open(input_excel_location, 'wb') as pdf:
          pdf.write(f.read())
        print('file found')
    except:
      smbclient.reset_connection_cache()
      with smbclient.open_file(r"{}".format(input_file), mode='rb', username=smb_username,
                               password=smb_password) as f:
        with open(input_excel_location, 'wb') as pdf:
          pdf.write(f.read())
        print('file found')
    finally:
      smbclient.reset_connection_cache()
    return input_excel_location
  else:
    return document_location + input_file


#filetered row and column wise data
def row_equal_func(columns, rows, df):
    r_slice, c_slice = 0, 0
    for col in range(columns):
        for row in range(rows):
            if str(df[col][row]) in ("blu product"):
                c_slice, r_slice = col, row
                break
    df_slice = df.iloc[r_slice:, c_slice:]
#     df_index_reset = df_slice.reset_index(drop=True)
    df_slice1 = df_slice.dropna(how='all')
# print(df_index_reset.T)
    return df_slice1.T


def data_classification(column_return_df):
    overall_dict = {}
    row_indexes = list(column_return_df.index.values)
    col_indexes = list(column_return_df.columns.values)
    # for _ , value in column_return_df.iterrows():
    for _col in col_indexes[:1]:
        for _row in row_indexes:
    #         print(column_return_df[_col][_row])
            key = str(column_return_df[_col][_row])
            rem_squ = re.sub("[\(\[].*?[\)\]]", "", key)
            rem_key = re.sub(r"\d","",rem_squ)
            key_fontem = rem_key.replace("CLP Article","").replace("EUTPD Article","")
    #         print(key_fontem)
            x_font = classifier.predict_proba(laser.embed_sentences(key_fontem, lang = "en"))[0]
            x_font.sort()
            classified = classifier.predict(laser.embed_sentences(key_fontem, lang = "en"))[0]
            if x_font[-1]>0.60: # Changed from 70 to 60
                classified_key = classified
            else:
                classified_key = "UNMAPPED"
    #         print(classified_key)
            for inner_col in col_indexes[1:]:
                value = str(column_return_df[inner_col][_row])
                if value not in ("nan","None","0"):
                    if classified_key in overall_dict:
                        overall_dict[classified_key].append({xl_rowcol_to_cell(inner_col,_row) + "_" +classify(value)[0]:value})
                    else:
                        overall_dict[classified_key] = [{xl_rowcol_to_cell(inner_col,_row) + "_" +classify(value)[0]:value}]
    return overall_dict

def c_round(number, decimal):
    number_of_decimal_places = lambda number: abs(Decimal(str(number)).as_tuple().exponent)
    custom_round = lambda number, decimal: ceil(number * 10 ** decimal) / 10 ** decimal

    if number_of_decimal_places(number) == decimal + 1 and str(number)[-1] == "5":
        return custom_round(number, decimal)
    else:
        return np.round(number, decimal)

def convert_to_dataframe(input_excel,sheet_name):
    position = {}
    Excel = openpyxl.load_workbook(input_excel, data_only=True)
    if sheet_name in Excel.sheetnames:
        sheet = Excel[sheet_name]
        final_list = []
        for row in sheet:
            row_list = []
            if sheet.row_dimensions[row[0].row].hidden == False:
                for cell in row:
                    if re.search(r"(\d\.?\d{0,2})\"?(.*)\"?", str(cell.number_format)):
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
                                if re.search(r"[a-zA-z]", str(cell.value)):
                                    value = cell.value
                                else:
                                    value = f"{cell.value * 100}%"
                            except:
                                value = cell.value
                        else:
    
                            try:
                               
                                if number_of_decimal_points > 0:
                                    value = float(c_round(cell.value, number_of_decimal_points))       # custom round function
                                else:
                                    value = int(c_round(cell.value,0))
                                if suffix:
                                    value = f"{value} {suffix}"
                            except:
                                value = cell.value
                        value = str(value).replace(">","&gt;").replace("<","&lt;")
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


def fontem_main(path,sheetnames):
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    input_excel_location = f'{temp_directory.name}/input_excel.xlsx'
    path = get_input(path, input_excel_location)
    final_dict = {}
    for sheet_name in sheetnames.split(","):
        print("filemneame *******",path)
        print('sheetname ********', sheet_name)
        df,_ = convert_to_dataframe(path,sheet_name)
        rows, columns = df.shape
        column_return_df = row_equal_func(columns, rows, df)
        diction = data_classification(column_return_df)
        final_dict[sheet_name] = diction
    return final_dict
