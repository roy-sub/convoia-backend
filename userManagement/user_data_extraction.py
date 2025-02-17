import os
import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from dataExtraction.gmail.data_extraction import GmailDataExtractor
from vectorDatabase.data_preprocessing import DataPreprocessor
from vectorDatabase.pinecone_chatbot_handler import Chatbot

class UserDataExtractor:

    def __init__(self):
        pass

    def new_user_data_extraction(self, email_id, mode):

        try:

            gmailDataExtractor = GmailDataExtractor(email_id)

            if mode == "oauth": 
                json_file_path = gmailDataExtractor.fetch_email_threads()
            elif mode == "manual":
                pass

            dataPreprocessor = DataPreprocessor(json_file_path)
            txt_file_path = dataPreprocessor.convert()

            chatbot = Chatbot()
            namespace = email_id.split('@')[0]
            chatbot.upload_file(txt_file_path, namespace)

            os.remove(json_file_path)
            os.remove(txt_file_path)

            return True
        
        except Exception as e:
            print(e)
            return False
    
    def existing_user_data_extraction(self, email_id, mode):

        try:

            gmailDataExtractor = GmailDataExtractor(email_id)

            if mode == "oauth": 
                json_file_path = gmailDataExtractor.fetch_email_threads(1)
            elif mode == "manual":
                pass

            dataPreprocessor = DataPreprocessor(json_file_path)
            txt_file_path = dataPreprocessor.convert()

            chatbot = Chatbot()
            namespace = email_id.split('@')[0]
            chatbot.upload_file(txt_file_path, namespace)

            os.remove(json_file_path)
            os.remove(txt_file_path)

            return True
        
        except Exception as e:
            print(e)
            return False
