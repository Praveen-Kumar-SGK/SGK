import fitz
from tempfile import TemporaryDirectory
from .utils import GetInput
from .excel_processing import document_location

def capture_annotations(input_file:str,pages:str) -> dict:
    if pages:
        pages_list = pages.split(",")
        pages_list = list(map(int,pages_list))
    final_dict = {}
    temp_dir = TemporaryDirectory(dir=document_location)
    temp_pdf = f"{temp_dir.name}/input.pdf"
    input_file = GetInput(input_file,temp_pdf).get_from_smb()
    doc = fitz.Document(input_file)
    for page in range(doc.page_count):
        page_dict_list = []
        for a in doc[page].annots():
            annotation_type = a.info["subject"]
            annotated = str(doc[page].get_text("block",a.rect)).strip()
            comment = a.info["content"]
            page_dict_list.append({"type":annotation_type,"annotated":annotated,"comment":comment})
        if pages:
            if int(page)+1 in pages_list:
                final_dict[int(page)+1] = page_dict_list
        else:
            final_dict[int(page)+1] = page_dict_list
    return final_dict

def capture_annotations_for_n_files(input_files:list,pages_list:list) -> dict:
    bulk_response = {}
    for index,file in enumerate(input_files):
        try:
            pages_string = pages_list[index]
        except:
            pages_string = ""
        response = capture_annotations(file,pages_string)
        bulk_response[file] = response
    return bulk_response