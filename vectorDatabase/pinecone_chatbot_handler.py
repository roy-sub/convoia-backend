import os
import uuid
from typing import List
from openai import OpenAI
from dotenv import load_dotenv
from pinecone import Pinecone

# Load environment variables
load_dotenv()

class Chatbot:
    def __init__(self):
        try:
            self.pinecone_api_key = os.getenv('PINECONE_API_KEY')
            self.openai_api_key = os.getenv('OPENAI_API_KEY')
            
            if not self.pinecone_api_key or not self.openai_api_key:
                raise ValueError("Missing API keys in .env file")
            
            self.pc = Pinecone(api_key=self.pinecone_api_key)
            self.openai_client = OpenAI(api_key=self.openai_api_key)
            self.index = self.pc.Index("convoia")
            
        except Exception as e:
            print(f"Error initializing Chatbot: {str(e)}")
            raise
    
    def create_embedding(self, text: str) -> List[float]:
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model="text-embedding-ada-002"
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error creating embedding: {str(e)}")
            raise
    
    def upload_file(self, file_path: str, namespace: str, chunk_size: int = 1000) -> None:
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                text = file.read()

            chunks = [text[i:i + chunk_size] for i in range(0, len(text), chunk_size)]
            vectors = []
            
            for i, chunk in enumerate(chunks):
                embedding = self.create_embedding(chunk)
                vector = {
                    'id': f"{os.path.basename(file_path)}_{str(uuid.uuid4())}",
                    'values': embedding,
                    'metadata': {
                        'text': chunk,
                        'source': os.path.basename(file_path),
                        'chunk_number': i
                    }
                }
                vectors.append(vector)

            self.index.upsert(vectors=vectors, namespace=namespace)
            print(f"Uploaded {len(vectors)} chunks to namespace '{namespace}'")
            
        except Exception as e:
            print(f"Error uploading file: {str(e)}")
            raise

    def get_response(self, question: str, namespace: str) -> str:
        try:
            query_embedding = self.create_embedding(question)
            
            results = self.index.query(
                vector=query_embedding,
                top_k=3,
                namespace=namespace,
                include_metadata=True
            )
            
            context = "\n".join([match.metadata["text"] for match in results.matches])
            
            messages = [
                {"role": "system", "content": "You are a helpful assistant. Use the provided context to answer questions."},
                {"role": "system", "content": f"Context: {context}"},
                {"role": "user", "content": question}
            ]

            response = self.openai_client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=messages
            )

            return response.choices[0].message.content
            
        except Exception as e:
            print(f"Error getting response: {str(e)}")
            raise

    def delete_namespace(self, namespace: str) -> None:
        try:
            self.index.delete(delete_all=True, namespace=namespace)
            print(f"Successfully deleted all vectors from namespace: '{namespace}'")
            
            # Print updated stats to confirm deletion
            stats = self.index.describe_index_stats()
            print("\nUpdated index stats:")
            print(stats)
            
        except Exception as e:
            print(f"Error deleting namespace: {str(e)}")
            raise

    def display_index_details(self) -> None:
        try:
            # List all indexes
            print("\nAvailable Indexes:")
            indexes = self.pc.list_indexes()
            print(indexes)
            
            # Get current index stats
            print("\nCurrent Index Stats:")
            stats = self.index.describe_index_stats()
            print(stats)
            
            # Print namespaces if available in stats
            if hasattr(stats, 'namespaces'):
                print("\nNamespaces:")
                for namespace, info in stats.namespaces.items():
                    print(f"Namespace: {namespace}")
                    print(f"Vector count: {info.vector_count}")
                    
        except Exception as e:
            print(f"Error getting index details: {str(e)}")
            raise
