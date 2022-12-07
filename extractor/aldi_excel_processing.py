import openpyxl
import pandas as pd

from .excel_processing import *
import tempfile
# from xls2xlsx import XLS2XLSX


def test(file_name,sheet_name):
    language_list_1=("en","de","dk","pl","pt","es","fr","slo","english","original text","german","danish","portuguese","french","poland","italien","italian","denmark","spain","portugal","hungarian","dutch","spanish","polish","eng","english language","slovenia")
    language_list_2=("at","ch","si","hu","it")
    language_list_3=("de","hu","it","si","fr","danish","portuguese","dutch","spanish","polish")
    doc_format = os.path.splitext(file_name)[1].lower()
    if doc_format == ".xls":
        pandas_wb = pd.ExcelFile(file_name)
        sheet_names = pandas_wb.sheet_names
        if sheet_name in sheet_names:
            df = pandas_wb.parse(sheet_name,header=None,engine="openpyxl")
        else:
            raise Exception("Sheet name does not exist")
    else:
        openpyxl_wb = openpyxl.load_workbook(file_name)
        sheet_names = openpyxl_wb.sheetnames
        if sheet_name in sheet_names:
            sheet = openpyxl_wb[sheet_name]
            df = pd.DataFrame(sheet.values)
        else:
            raise Exception("sheet name does not exist")

    df = df.applymap(lambda x: str(x))

    rows, columns = df.shape

    def fetching_values(columns,rows,df):
        lang_lst=[]
        for col in range(columns):
            for row in range(rows):
                if df[col][row]!=None:
                    lang_regex=re.sub(r"\((.*?)\)","",df[col][row].lower()).strip()
                    if lang_regex in language_list_1:
                        lang_lst.append(lang_regex)
                    elif lang_regex in language_list_2:
                        lang_lst.append(lang_regex)

        def Grp_2_4_knives_and_Ultrasonic_files(lang_lst,df,columns,rows):
            col_value, row_value=None,None
            for col in range(columns):
                for row in range(rows):
                    if df[col][row]!=None:
                        lang_regex=re.sub(r"\((.*?)\)","",df[col][row].lower()).strip()
                        if lang_regex in lang_lst:
                            col_value, row_value = col, row
                            break

                if col_value!=None and row_value!=None:
                    print("-loop,group=2,4 ultrasonic,knives")
                    df=df.iloc[row_value+1:,col_value-1:]
                    df = df.dropna(how='all')
                    return df

        def Grp_1_3_files(lang_lst,df,columns,rows):
            col_value, row_value=None,None
            for col in range(columns):
                for row in range(rows):
                    if df[col][row]!=None:
                        lang_regex=re.sub(r"\((.*?)\)","",df[col][row].lower()).strip()
                        if lang_regex in lang_lst:
                            col_value, row_value = col, row
                            break

                if col_value!=None and row_value!=None:
                    print("\n 1st and 3rd files---Grp_1_3_files(check this def function)")
                    df=df.iloc[row_value+1:,col_value:]
                    df = df.dropna(how='all')
                    return df

        def Grp_5_toothbrush(lang_lst,df,columns,rows):
            col_value, row_value=None,None
            for col in range(columns):
                for row in range(rows):
                    if df[col][row]:
                        col_value, row_value = col, row
                        break
                print("\n group 5 tooth brush file")
                df=df.iloc[row_value:,col_value:]
                df = df.dropna(how='all')
                return df
        if set(lang_lst)==set(language_list_3) and len(lang_lst)==len(language_list_3):
            print("@@@ 4-fetching_values(def)",lang_lst)
            grp_2_4=Grp_2_4_knives_and_Ultrasonic_files(lang_lst,df,columns,rows)
            return grp_2_4
        elif len(lang_lst)==0:
            print("@@@ 5-fetching_values(def)",lang_lst)
            group_5=Grp_5_toothbrush(lang_lst,df,columns,rows)
            return group_5
        else:
            print("@@@ 1,2,3-fetching_values(def)",lang_lst)
            lang_lst1_variable = len(set(lang_lst).intersection(set(language_list_1)))
            lang_lst2_variable = len(set(lang_lst).intersection(set(language_list_2)))
            print(lang_lst1_variable)
            if lang_lst1_variable >= 4:
                print("group _1&3 ", lang_lst1_variable)
                group_1_3 = Grp_1_3_files(lang_lst, df, columns, rows)
                return group_1_3
            elif lang_lst2_variable > len(set(language_list_2)) - 1:
                print("group 2&4 ", lang_lst2_variable)
                group_2_4 = Grp_2_4_knives_and_Ultrasonic_files(lang_lst, df, columns, rows)
                return group_2_4
            else:
                print("group 5")
                df = df.dropna(how='all')
                return df


    return_df = fetching_values(columns, rows,df)
    def colnum_string(n):
        string = ""
        while n > 0:
            n, remainder = divmod(n - 1, 26)
            string = chr(65 + remainder) + string
        return string
    outer_list=[]
    tes=["set a","这个是title","这部分是背面的feature信息","refer to column b","pl的","nl的","be","dk","pt","这个是title 部分颜色上方的文字的译文","以下的是title 部分的尺寸 和材质的译文  具体的做法可以参考ly artwork (sp)","product image for reference"]
    for index, row in return_df.iterrows():
        index=index+1
        inner_lst=[]
        for  col_index,col_value in row.items():
            col_alph=colnum_string(col_index+1)
            if col_value:
                temp=col_value.strip()
                if temp.replace(":","").lower() not in tes and temp!=None:
                    temp=str(temp).strip()
                    remove_none_val = temp.replace('none','').replace('None','').replace('nan','').replace('NA', '').replace('N/A', '').replace('\xa0', ' ').replace('<', '&lt;').replace('>', '&gt;')
                    if remove_none_val:
                        cell_val={col_alph+""+str(index)+"_"+classify(remove_none_val)[0]:remove_none_val.strip()}
                        inner_lst.append(cell_val)
        outer_list.append(inner_lst)
    final_dictionary={}
    for i,inner_list in enumerate(outer_list):
        for n,inner_dic in enumerate(inner_list):
            if "MARKETING_CLAIM" in final_dictionary:
                final_dictionary["MARKETING_CLAIM"].append(inner_dic)
            else:
                final_dictionary["MARKETING_CLAIM"] = [inner_dic]
    return final_dictionary

from .utils import GetInput
def main(file_name, sheet_names):
    sheet_dict = {}
    temp_directory = tempfile.TemporaryDirectory(dir=document_location)
    doc_format = os.path.splitext(file_name)[1].lower()
    input_excel_location = f'{temp_directory.name}/input_excel{doc_format}'
    # input_excel_converted_location = f'{temp_directory.name}/input_excel.xlsx'
    get_input = GetInput(file_name, input_excel_location)
    file_name = get_input()
    # if doc_format == ".xls":
    #     x2x = XLS2XLSX(file_name)
    #     x2x.to_xlsx(input_excel_converted_location)
    #     file_name = input_excel_converted_location
    for sheet_name in sheet_names.split(","):
        final_response=test(file_name,sheet_name)
        sheet_dict[sheet_name] = final_response
    return sheet_dict