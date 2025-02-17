from typing import List, Dict, Optional
from datetime import datetime, timedelta
import imaplib
import email
from email.header import decode_header
from email.utils import parsedate_to_datetime
import pytz
from collections import defaultdict
import json
import uuid
import re
from pathlib import Path

# URGENT - Simplify the Script
# IMPORTANT - Upgrade the Code to be Applicable to all Domains 

def decode_header_value(header_value: str) -> str:
    """Safely decode email header value."""
    try:
        decoded_headers = decode_header(header_value or '')
        decoded_parts = []
        for content, charset in decoded_headers:
            if isinstance(content, bytes):
                decoded_parts.append(content.decode(charset or 'utf-8', errors='replace'))
            else:
                decoded_parts.append(str(content))
        return ' '.join(decoded_parts)
    except Exception as e:
        print(f"Error decoding header: {str(e)}")
        return str(header_value)

def extract_email_details(email_message) -> Dict:
    """Extract relevant details from an email message."""
    try:
        # Parse subject
        subject = decode_header_value(email_message.get("Subject", ""))
        
        # Parse from/to headers
        from_header = decode_header_value(email_message.get("From", ""))
        to_header = decode_header_value(email_message.get("To", ""))
        
        # Parse date
        date_str = email_message.get("Date")
        if date_str:
            try:
                date = parsedate_to_datetime(date_str)
            except:
                date = datetime.now(pytz.UTC)
        else:
            date = datetime.now(pytz.UTC)
        
        # Extract body
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    try:
                        payload = part.get_payload(decode=True)
                        if payload:
                            body = payload.decode('utf-8', errors='replace')
                            break
                    except:
                        continue
        else:
            try:
                payload = email_message.get_payload(decode=True)
                if payload:
                    body = payload.decode('utf-8', errors='replace')
            except:
                body = email_message.get_payload(decode=False) or ""
        
        # Remove quoted text
        body = re.sub(r"(?s)On\s.+?\s\w+:\s.*$", "", body).strip()
        
        # Get labels/flags
        labels = []
        flags = getattr(email_message, 'flags', []) or []
        for flag in flags:
            if isinstance(flag, bytes):
                flag = flag.decode('utf-8', errors='replace')
            labels.append(str(flag))
        
        # Add INBOX or SENT label based on folder
        folder = getattr(email_message, 'folder', '')
        if folder:
            if 'sent' in folder.lower():
                labels.append('SENT')
            elif 'inbox' in folder.lower():
                labels.append('INBOX')
        
        return {
            "message_id": email_message.get("Message-ID", ""),
            "datetime": date.strftime("%Y-%m-%d %H:%M:%S %Z"),
            "timestamp": date.timestamp(),
            "sender": from_header,
            "receiver": to_header,
            "subject": subject,
            "body": body,
            "references": email_message.get("References", "").split(),
            "in_reply_to": email_message.get("In-Reply-To", ""),
            "labels": labels
        }
    except Exception as e:
        print(f"Error extracting email details: {str(e)}")
        return {}

def fetch_email_threads(
    email_address: str,
    password: str,
    num_prev_days: Optional[int] = None,
    imap_server: str = "imap.gmail.com",
    output_file: str = "email_threads.json"
) -> str:
    """
    Fetch email threads from an email account.
    
    Args:
        email_address: Email address
        password: Email password or app-specific password
        num_prev_days: Number of previous days to fetch emails from (None for all)
        imap_server: IMAP server address
        output_file: Path to save the JSON output
    
    Returns:
        Path to the saved JSON file
    """
    try:
        # Connect to IMAP server
        mail = imaplib.IMAP4_SSL(imap_server)
        mail.login(email_address, password)
        
        all_emails = []
        
        def fetch_folder_emails(folder_name):
            """Helper function to fetch emails from a specific folder."""
            try:
                # Handle Gmail's special folder names
                if '[Gmail]' in folder_name:
                    # Remove any existing quotes
                    folder_name = folder_name.replace('"', '')
                    # Properly quote the entire folder name
                    folder_name = f'"{folder_name}"'
                elif ' ' in folder_name and not (folder_name.startswith('"') and folder_name.endswith('"')):
                    folder_name = f'"{folder_name}"'

                status, _ = mail.select(folder_name, readonly=True)
                if status != 'OK':
                    print(f"Failed to select folder {folder_name}: {status}")
                    return []
                
                # Set search criteria
                if num_prev_days is not None:
                    date_filter = (datetime.now(pytz.UTC) - timedelta(days=num_prev_days))
                    search_criteria = f'SINCE "{date_filter.strftime("%d-%b-%Y")}"'
                else:
                    search_criteria = "ALL"
                
                status, message_numbers = mail.search(None, search_criteria)
                if status != 'OK':
                    return []
                
                folder_emails = []
                for num in message_numbers[0].split():
                    try:
                        status, msg_data = mail.fetch(num, "(RFC822)")
                        if status != 'OK' or not msg_data or not msg_data[0]:
                            continue
                        
                        email_body = msg_data[0][1]
                        email_message = email.message_from_bytes(email_body)
                        email_message.folder = folder_name  # Add folder info
                        
                        # Get flags
                        status, flag_data = mail.fetch(num, "(FLAGS)")
                        if status == 'OK' and flag_data and flag_data[0]:
                            email_message.flags = re.findall(r'\(([^)]*)\)', flag_data[0].decode('utf-8'))
                        
                        email_details = extract_email_details(email_message)
                        if email_details:
                            folder_emails.append(email_details)
                            
                    except Exception as e:
                        print(f"Error processing email {num}: {str(e)}")
                        continue
                
                return folder_emails
            except Exception as e:
                print(f"Error accessing folder {folder_name}: {str(e)}")
                return []
        
        # Fetch from Sent folder
        print("\nFetching from Sent Mail...")
        sent_folders = ['[Gmail]/Sent Mail', '[Gmail]/Sent', 'Sent', 'Sent Items']
        for folder in sent_folders:
            sent_emails = fetch_folder_emails(folder)
            if sent_emails:
                print(f"Found {len(sent_emails)} sent emails")
                all_emails.extend(sent_emails)
                break
        
        # Fetch from Inbox
        print("\nFetching from Inbox...")
        inbox_emails = fetch_folder_emails('INBOX')
        if inbox_emails:
            print(f"Found {len(inbox_emails)} inbox emails")
            all_emails.extend(inbox_emails)
        
        mail.logout()
        
        # Organize into threads
        email_map = {e["message_id"]: e for e in all_emails if e.get("message_id")}
        thread_map = defaultdict(list)
        
        # Build thread relationships
        for email_data in all_emails:
            msg_id = email_data.get("message_id")
            if msg_id:
                if email_data.get("in_reply_to"):
                    thread_map[email_data["in_reply_to"]].append(msg_id)
                for ref in email_data.get("references", []):
                    thread_map[ref].append(msg_id)
        
        def build_thread(root_id: str, visited: set = None) -> List[Dict]:
            if visited is None:
                visited = set()
            if root_id in visited or root_id not in email_map:
                return []
            
            visited.add(root_id)
            thread = [email_map[root_id]]
            for reply_id in thread_map[root_id]:
                thread.extend(build_thread(reply_id, visited))
            return thread
        
        # Process all emails into threads
        threads = []
        processed = set()
        
        for email_data in all_emails:
            msg_id = email_data.get("message_id")
            if not msg_id or msg_id in processed:
                continue
            
            # Find thread root
            current_id = msg_id
            current_email = email_data
            while current_email.get("in_reply_to") and current_email["in_reply_to"] in email_map:
                current_id = current_email["in_reply_to"]
                current_email = email_map[current_id]
            
            # Build thread from root
            thread_messages = build_thread(current_id)
            if thread_messages:
                # Sort chronologically
                thread_messages.sort(key=lambda x: x["timestamp"])
                
                # Create thread object
                thread = {
                    "thread_id": str(uuid.uuid4()),  # Generate unique thread ID
                    "total_messages": len(thread_messages),
                    "labels": list(set(sum([msg.get("labels", []) for msg in thread_messages], []))),
                    "reply_to_message_id": thread_messages[-1]["message_id"] if thread_messages else None,
                    "messages": thread_messages
                }
                
                threads.append(thread)
                processed.update(msg["message_id"] for msg in thread_messages)
        
        # Sort threads by latest message
        threads.sort(key=lambda x: max(msg["timestamp"] for msg in x["messages"]), reverse=True)
        
        # Save to JSON
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(threads, f, indent=2, ensure_ascii=False)
        
        print(f"\nSuccessfully saved {len(threads)} threads to {output_path.absolute()}")
        return str(output_path.absolute())
    
    except Exception as e:
        print(f"Error: {str(e)}")
        return ""
