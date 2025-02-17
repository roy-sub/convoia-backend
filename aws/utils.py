import csv
import boto3
import codecs
from typing import List
from botocore.exceptions import ClientError

def fetch_tokens(email):
    
    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Use scan with correct filter expression syntax
        response = table.scan(
            FilterExpression='email = :email_val',
            ExpressionAttributeValues={
                ':email_val': email
            }
        )

        # Check if any items were found
        if not response.get('Items'):
            return None

        # Get the first matching item
        item = response['Items'][0]
        
        # Transform the response by removing the {'S': } wrapper
        transformed_item = {}
        
        for key, value in item.items():
            # Handling string values wrapped in {'S': value}
            if isinstance(value, dict) and 'S' in value:
                transformed_item[key] = value['S']
            else:
                transformed_item[key] = value

        return transformed_item

    except ClientError as e:
        print(f"An error occurred: {e}")
        return None
    except Exception as e:
        print(f"Unexpected error: {e}")
        return None

def get_all_email_ids():
    
    try:
        # Read AWS credentials
        aws_credentials = {}
        with codecs.open('credentials/credential_aws.csv', 'r', encoding='utf-8-sig') as file:
            reader = csv.DictReader(file)
            for row in reader:
                aws_credentials['aws_access_key_id'] = row.get('Access key ID', '').strip()
                aws_credentials['aws_secret_access_key'] = row.get('Secret access key', '').strip()
        
        # Initialize DynamoDB client
        dynamodb = boto3.resource(
            'dynamodb',
            aws_access_key_id=aws_credentials['aws_access_key_id'],
            aws_secret_access_key=aws_credentials['aws_secret_access_key'],
            region_name='us-west-2'
        )

        table = dynamodb.Table('ConvoiaUsers')
        
        # Scan the entire table without any filter
        response = table.scan()
        
        # Extract email_ids from the response
        email_ids = [item['email'] for item in response.get('Items', [])]
        
        # Handle pagination if necessary
        while 'LastEvaluatedKey' in response:
            response = table.scan(
                ExclusiveStartKey=response['LastEvaluatedKey']
            )
            email_ids.extend([item['email'] for item in response.get('Items', [])])
        
        print(f"Found total of {len(email_ids)} emails")
        return email_ids
        
    except ClientError as e:
        print(f"Error retrieving emails: {str(e)}")
        return []
