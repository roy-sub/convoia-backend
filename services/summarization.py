import os
import sys
from pathlib import Path
from pydantic import BaseModel, Field
from langchain.prompts import PromptTemplate
from langchain.output_parsers import PydanticOutputParser

sys.path.append(str(Path(__file__).resolve().parent.parent))

from dataExtraction.gmail.data_extraction import GmailDataExtractor
from vectorDatabase.data_preprocessing import DataPreprocessor
from vectorDatabase.pinecone_chatbot_handler import Chatbot
from email_operations.gmail import GmailAutomation
from aws.utils import fetch_tokens

class DaysOutput(BaseModel):
    days: int = Field(ge=0) 

class GenerateSummarization:
    
    def __init__(self):
        
        self.chatbot = Chatbot()
        self.parser = PydanticOutputParser(pydantic_object=DaysOutput)
        
        self.days_prompt = """Extract the number of days for email summarization from the user's request.

        CRITICAL RULES:
        1. Output ONLY the number of days as an integer
        2. If user mentions "recent" or "last login", output 0
        3. For specific days mentioned (like "last 7 days"), use that number
        4. Default to 0 if no time period is specified
        
        User Request: {input_text}
        
        Return only the number in this format: {format_instructions}"""

    def _extract_days(self, text: str) -> int:

        try:
            # Create prompt
            days_prompt = PromptTemplate(
                template=self.days_prompt,
                input_variables=["input_text"],
                partial_variables={"format_instructions": self.parser.get_format_instructions()}
            )
            
            # Get response
            response = self.chatbot.get_response(days_prompt.format(input_text=text), "days")
            
            # Parse response
            parsed = self.parser.parse(response)
            return parsed.days
            
        except Exception as e:
            print(f"Error extracting days: {str(e)}")
            return 0
    
    def _generate_summary(self, summarization_prompt: str, namespace: str) -> str:

        try:
            summary_instruction = """Based on the email data provided, generate a clear and concise summary.

            FOCUS ON:
            1. Important conversations and their key points
            2. Any critical action items or deadlines
            3. Significant updates or decisions
            4. Ongoing discussions that need attention

            FORMAT:
            - Use clear paragraphs
            - Highlight important points
            - Keep it concise but informative
            - Focus on the most relevant information

            User Request: {input_text}"""

            # Create complete prompt
            complete_prompt = summary_instruction.format(input_text=summarization_prompt)
            
            # Get summary from chatbot
            summary = self.chatbot.get_response(complete_prompt, namespace)
            return summary

        except Exception as e:
            print(f"Error generating summary: {str(e)}")
            return ""

    def generate_summarization(self, user_email: str, user_input_text: str) -> str:

        try:
            # Extract number of days
            days = self._extract_days(user_input_text)
            print(f"Extracting summary for past {days} days")

            # Get User Details
            user_details = fetch_tokens(user_email)
            if not user_details:
                print("Error: Could not fetch user details")
                return False, ""

            # Divide Based on User 'Mode'
            if user_details.get('mode') == 'oauth':

                # Method 1 : More Reliable but Time Consuming

                gmailDataExtractor = GmailDataExtractor(user_email)
                json_file_path = gmailDataExtractor.fetch_email_threads()

                dataPreprocessor = DataPreprocessor(json_file_path)
                txt_file_path = dataPreprocessor.convert()

                chatbot = Chatbot()
                namespace_summary = f"{user_email.split('@')[0]}_summarization"
                chatbot.upload_file(txt_file_path, namespace_summary)

                # Generate Summarize
                summary = self._generate_summary(user_input_text, namespace_summary)
                
                # Delete the Namespace
                chatbot.delete_namespace(namespace_summary)

                # Delete the Files
                os.remove(json_file_path)
                os.remove(txt_file_path)

                # # Method 2 : Less Reliable but Faster

                # namespace = user_email.split('@')[0]
                # summary = self._generate_summary(user_input_text, namespace)

                return True, summary
            
            else:
                print("Error: Manual mode not yet implemented")
                return True, ""

        except Exception as e:
            print(f"Error in generate_summarization: {str(e)}")
            return False, ""

# if __name__ == "__main__":
    
#     generator = GenerateSummarization()
#     user_email = "roysubhradip001@gmail.com"
#     user_input_text = "Summarize my emails from the last 5 days"
    
#     success, result = generator.generate_summarization(user_email, user_input_text)
#     print(f"\n\n{result}")
