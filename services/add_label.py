import sys
from pathlib import Path
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

sys.path.append(str(Path(__file__).resolve().parent.parent))

from vectorDatabase.pinecone_chatbot_handler import Chatbot
from services.send_reply import MessageID_Extractor
from email_operations.gmail import GmailAutomation
from aws.utils import fetch_tokens

class LabelOutput(BaseModel):
    # Ensure label is alphanumeric with spaces and underscores only
    label: str = Field(
        min_length=1,
        max_length=50,
        pattern=r'^[a-zA-Z0-9\s_-]+$'
    )

class LabelExtractor:
    
    def __init__(self):
        
        self.chatbot = Chatbot()
        self.parser = PydanticOutputParser(pydantic_object=LabelOutput)
        
        self.label_prompt = """Extract or determine the label name from this request.

        CRITICAL INSTRUCTIONS:
        1. Return ONLY the label name, nothing else
        2. Labels should be short and descriptive
        3. Remove any special characters except hyphens and underscores
        4. Do not include words like "label", "tag", "category"
        5. Extract exactly what should be the label name
        
        Examples:
        Input: "Add a label 'Important' to this email"
        Output: Important
        
        Input: "Mark this email with the label high priority"
        Output: High_Priority
        
        Input: "Create a new label called project updates"
        Output: Project_Updates
        
        Current request: {input_text}
        
        Return the label in this format: {format_instructions}"""

    def get_label(self, text: str) -> str:

        try:
            # Create prompt with format instructions
            label_prompt = PromptTemplate(
                template=self.label_prompt,
                input_variables=["input_text"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )
            
            # Get response from chatbot
            response = self.chatbot.get_response(
                label_prompt.format(input_text=text),
                "labels"  # Using a generic namespace for label operations
            )
            
            # Parse and validate the response
            parsed = self.parser.parse(response)
            return parsed.label.strip()
            
        except Exception as e:
            print(f"Error extracting label: {str(e)}")
            return ""

class EmailLabel:

    def __init__(self):
        pass

    def add_label_to_message(self, user_email, user_input_text):

        # Validate inputs
        if not user_email or not user_input_text:
            print("Error: Missing required inputs")
            return False
        
        # Getting the Namespace
        namespace = user_email.split('@')[0]

        messageID_extractor = MessageID_Extractor()
        message_id = messageID_extractor.get_message_id(user_input_text, namespace)

        print(f"\nmessage_id to add label : {message_id}\n")

        if not message_id:
            print("Error: Could not determine message_id")
            return False

        # Get the label name 
        extractor = LabelExtractor()
        label_name = extractor.get_label(user_input_text)

        print(f"\nlabel to add: {label_name}\n")

        if not label_name:
            print("Error: Could not determine label_name")
            return False

        # Get User Details
        user_details = fetch_tokens(user_email)
        if not user_details:
            print("Error: Could not fetch user details")
            return False

        # Divide Based on User 'Mode'
        if user_details.get('mode') == 'oauth':
            
            refresh_token = user_details.get('refresh_token')
            access_token = user_details.get('access_token')

            gmail_automation = GmailAutomation(user_email, refresh_token, access_token)
            label_creation_status = gmail_automation.create_label(label_name)

            print(f"\nlabel creation status : {label_creation_status}\n")

            if label_creation_status and label_creation_status.get('status') == 'success':
                
                result = gmail_automation.add_label_to_message(message_id, label_name)

                print(f"\nadd_label_to_message result: {result}\n")

                if result and result.get('status') == 'success':
                    return True
                else:
                    print("Error: Failed to add the Label")
                    return False
            else:
                print("Error: Unable to Create the Label")
                return False
        else:
            print("Error: Manual mode not yet implemented")
            return True
        
    def create_label(self, user_email, user_input_text):

        # Validate inputs
        if not user_email or not user_input_text:
            print("Error: Missing required inputs")
            return False
        
        # Getting the Namespace
        namespace = user_email.split('@')[0]

        messageID_extractor = MessageID_Extractor()
        message_id = messageID_extractor.get_message_id(user_input_text, namespace)

        if not message_id:
            print("Error: Could not determine message_id")
            return False

        # Get the label name 
        extractor = LabelExtractor()
        label_name = extractor.get_label(user_input_text)

        if not label_name:
            print("Error: Could not determine label_name")
            return False

        # Get User Details
        user_details = fetch_tokens(user_email)
        if not user_details:
            print("Error: Could not fetch user details")
            return False

        # Divide Based on User 'Mode'
        if user_details.get('mode') == 'oauth':
            
            refresh_token = user_details.get('refresh_token')
            access_token = user_details.get('access_token')

            gmail_automation = GmailAutomation(user_email, refresh_token, access_token)
            label_creation_status = gmail_automation.create_label(label_name)

            if label_creation_status and label_creation_status.get('status') == 'success':
                
                return True
            
            else:
                print("Error: Unable to Create the Label")
                return False
        else:
            print("Error: Manual mode not yet implemented")
            return True

# if __name__ == "__main__":
    
#     extractor = EmailLabel()
#     user_email = "roysubhradip001@gmail.com"
#     user_input_text = "Add a label 'Follow Up' to the email received from Jonathan about Reviewing the Resume"
#     result = extractor.add_label_to_message(user_email, user_input_text)
#     print(result)
