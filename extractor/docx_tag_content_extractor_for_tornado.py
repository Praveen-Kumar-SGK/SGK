import io
import smbclient
from bs4 import BeautifulSoup
from environment import MODE

if MODE == 'local':
    from .local_constants import *
else:
    from .dev_constants import *

class docx_tag_extractor_for_tornado:
    def __init__(self,input_file,tags,input_type):
        self.input_file = input_file
        self.tags = tags
        self.input_type = input_type
        # self.input_io = io.BytesIO()
        self.input_io = None

    def get_file_content(self):
        if self.input_file.startswith('\\'):
            print('connecting to SMB share')
            try:
                with smbclient.open_file(r"{}".format(self.input_file), mode='rb', username=smb_username,
                                         password=smb_password) as f:
                    self.input_io = f.read()
                    print('file found')
            except:
                raise Exception('cannot access the file')
            finally:
                smbclient.reset_connection_cache()
            return self.input_io
        else:
            with open(document_location+self.input_file,'r') as f:
                self.input_io = f.read()
            return self.input_io

    def extract(self):
        final_list = []
        content = self.get_file_content()
        if self.input_type == 'html':
            soup = BeautifulSoup(content,'html.parser')
        else:
            soup = BeautifulSoup(content,'xml')
        for tag in self.tags.split(','):
            temp_tag_list = soup.find_all(tag)
            temp_tag_value = [str(soup_tag.text) for soup_tag in temp_tag_list if soup_tag.text.strip()]
            final_list.extend(temp_tag_value)
        return final_list









