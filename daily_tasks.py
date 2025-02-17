import asyncio
from typing import List
from aws.email_automation_preferences import EmailAutomationPreferences
from aws.utils import get_all_email_ids

async def update_database(email_id: str):

    print(f"Updated database for email: {email_id}")

###

async def initiate_follow(email_id: str):

    print(f"Initiated follow up for email: {email_id}")

async def daily_database_addition() -> None:

    # Fetch list of email IDs (replace with your actual fetching logic)
    email_ids = get_all_email_ids()
    
    # Create tasks for each email ID
    tasks = [update_database(email_id) for email_id in email_ids]
    
    # Run all database updates concurrently
    await asyncio.gather(*tasks)
    print("Completed all database updates")

async def automated_follow_up() -> None:

    # Fetch list of email IDs (replace with your actual fetching logic)
    email_ids = EmailAutomationPreferences().get_email_ids_with_active_follow_up()
    
    # Create tasks for each email ID
    tasks = [initiate_follow(email_id) for email_id in email_ids]
    
    # Run all follow-ups concurrently
    await asyncio.gather(*tasks)
    print("Completed all follow-ups")

async def daily():

    # Create tasks for both main functions
    database_task = asyncio.create_task(daily_database_addition())
    follow_up_task = asyncio.create_task(automated_follow_up())
    
    # Run both tasks concurrently
    await asyncio.gather(database_task, follow_up_task)
    print("Daily tasks completed")

# Run the daily function
if __name__ == "__main__":
    asyncio.run(daily())
