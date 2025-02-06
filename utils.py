import json
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from datetime import datetime
import pytz
import os
from dotenv import load_dotenv

load_dotenv()

# Google Sheets configuration
# https://docs.google.com/spreadsheets/d/1sRWp95wqo3a7lLBbtNd_3KkTyGjx_9sctTOL5JOb6pA
SPREADSHEET_ID = '1sRWp95wqo3a7lLBbtNd_3KkTyGjx_9sctTOL5JOb6pA'
SHEET_NAME = 'LeetCode Questions'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

def get_google_sheets_service():
    """Authenticate and create Google Sheets service"""
    credentials_json = os.getenv('GOOGLE_CREDENTIALS')
    if not credentials_json:
        raise ValueError("GOOGLE_CREDENTIALS environment variable is not set")
    creds = Credentials.from_service_account_info(json.loads(credentials_json), scopes=SCOPES)
    service = build('sheets', 'v4', credentials=creds)
    return service

def prepare_sheet_data(questions_data):
    """Convert JSON data to spreadsheet-friendly format"""
    headers = [
        'ID', 
        'Problem Name', 
        'Likes', 
        'Dislikes', 
        'Like\nRatio',
        'Topics', 
        'Difficulty',
        'Accepted', 
        'Submissions', 
        'Accept\nRate',
        'Free?',
        'Solution?',
        'Video\nSolution?',
        'Category'
    ]
    
    rows = []
    
    for idx, item in enumerate(questions_data):
        q = item['data']['question']
        
        stats = json.loads(q.get('stats', '{}')) if q.get('stats') else {}
        total_accepted = stats.get('totalAcceptedRaw', 0)
        total_submissions = stats.get('totalSubmissionRaw', 0)
        acceptance_rate = (total_accepted / total_submissions * 100) if total_submissions > 0 else 0

        topic_tags = q.get('topicTags') or []                        
        like_ratio_formula = '=IF(INDEX(C:C, ROW())+INDEX(D:D, ROW())=0, 0, INDEX(C:C, ROW())/(INDEX(C:C, ROW())+INDEX(D:D, ROW())))'
        row = [
            q.get('questionFrontendId', ''),
            f'=HYPERLINK("{q.get("url", "")}", "{q.get("title", "")}")',
            q.get('likes', 0),
            q.get('dislikes', 0),
            like_ratio_formula,
            ', '.join([t.get('name', '') for t in topic_tags]),
            q.get('difficulty', ''),
            total_accepted,
            total_submissions,
            f"{acceptance_rate:.1f}%",
            "Yes" if not q.get('isPaidOnly', False) else "No",
            "Yes" if q.get('hasSolution', False) else "No",
            "Yes" if q.get('hasVideoSolution', False) else "No",
            q.get('categoryTitle', '')
        ]
        rows.append(row)
    
    return [headers] + sorted(rows, key=lambda x: x[2], reverse=True)

def apply_sheet_formatting(service, rows_count):
    """Apply modern formatting to Google Sheet"""
    colors = {
        'header': {'red': 0.16, 'green': 0.31, 'blue': 0.47},  # Dark blue
        # 'header': {'red': 0.1, 'green': 0.1, 'blue': 0.1},
        'text': {'red': 1, 'green': 1, 'blue': 1}, 
        'yes': {'red': 0, 'green': 1, 'blue': 0},     # Green
        'no': {'red': 1, 'green': 0, 'blue': 0},      # Red
        'easy': {'red': 0, 'green': 1, 'blue': 0},    # Green
        'medium': {'red': 1, 'green':1, 'blue': 0},   # Orange
        'hard': {'red': 1, 'green': 0, 'blue': 0}     # Red
    }

    requests = [
        # Freeze header row (now row 2)
        {
            "updateSheetProperties": {
                "properties": {"sheetId": 0, "gridProperties": {"frozenRowCount": 2}},
                "fields": "gridProperties.frozenRowCount"
            }
        },
        # Set filter for columns A-M
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": 0,
                        "startRowIndex": 1,  # Header at row 3
                        "endRowIndex": rows_count,  # Number of rows in the data
                        "startColumnIndex": 0,
                        "endColumnIndex": 14
                    }
                }
            }
        },        
        {
            "repeatCell": {
                "range": {"sheetId": 0, "startRowIndex": 1, "endRowIndex": 2},
                "cell": {
                    "userEnteredFormat": {
                        "backgroundColor": colors['header'],  # Dark background
                        "horizontalAlignment": "CENTER",
                        "textFormat": {
                            "bold": True,
                            "fontSize": 11,
                            "foregroundColor": colors['text']  # White text
                        },
                        "borders": {
                            "top": {"style": "SOLID", "width": 1, "color": colors['text']},
                            "bottom": {"style": "SOLID", "width": 1, "color": colors['header']}
                        }
                    }
                },
                "fields": "userEnteredFormat(backgroundColor,textFormat,horizontalAlignment,borders)"
            }
        },


        # Conditional formatting for Yes/No columns (I-K)
        *[{
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0, "startColumnIndex": col}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": val}]},
                        "format": {"backgroundColor": colors[val.lower()]}
                    }
                }
            }
        } for col in [9, 10, 11] for val in ["Yes", "No"]],  # Columns J, K, L (0-based 9,10,11)
        # Difficulty formatting
        *[{
            "addConditionalFormatRule": {
                "rule": {
                    "ranges": [{"sheetId": 0, "startColumnIndex": 5}],
                    "booleanRule": {
                        "condition": {"type": "TEXT_EQ", "values": [{"userEnteredValue": diff}]},
                        "format": {"backgroundColor": colors[diff.lower()]}
                    }
                }
            }
        } for diff in ["Easy", "Medium", "Hard"]],        
        # Column widths (index: pixels) for columns A-L
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 0,  # Column A
                    "endIndex": 12     # Column L (exclusive)
                },
                "properties": {
                    "pixelSize": 100  # Default width for all columns
                },
                "fields": "pixelSize"
            }
        },
        # Individual column overrides (add these after the default width)
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 0,  # Column A (ID)
                    "endIndex": 1
                },
                "properties": {"pixelSize": 50},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 2,  # Column C D
                    "endIndex": 4
                },
                "properties": {"pixelSize": 90},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 1,  # Column B (Problem Name)
                    "endIndex": 2
                },
                "properties": {"pixelSize": 220},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 5,  # Column E (Topics)
                    "endIndex": 6
                },
                "properties": {"pixelSize": 180},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": 0,
                    "dimension": "COLUMNS",
                    "startIndex": 7,
                    "endIndex": 9
                },
                "properties": {"pixelSize": 140},
                "fields": "pixelSize"
            }
        },
        # Format the Like Ratio (%) column as a percentage.
        {
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startColumnIndex": 4,  # Column index for "Like Ratio (%)"
                    "endColumnIndex": 5,
                    "startRowIndex": 2      # Apply from row 4 onward (header is at row 3)
                },
                "cell": {
                    "userEnteredFormat": {
                        "numberFormat": {
                            "type": "PERCENT",
                            "pattern": "0.0%"  # Display with one decimal place
                        }
                    }
                },
                "fields": "userEnteredFormat.numberFormat"
            }
        },        
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests}
    ).execute()

def update_google_sheet(service, data):
    """Update Google Sheet with prepared data"""
    tz = pytz.timezone('Europe/Berlin')  # Set your timezone
    now_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")
    
    # Update spreadsheet name
    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={
            "requests": [{
                "updateSpreadsheetProperties": {
                    "properties": {"title": f"LeetCode Questions - Last Updated {now_str}"},
                    "fields": "title"
                }
            }]
        }
    ).execute()

    # Clear and update data
    clear_request = {
    "requests": [{
            "repeatCell": {
                "range": {
                    "sheetId": 0,
                    "startRowIndex": 0,
                    "endRowIndex": 10000,  # Adjust row count as needed
                    "startColumnIndex": 0,
                    "endColumnIndex": 26  # Columns A-Z
                },
                "cell": {
                    "userEnteredFormat": {}  # Reset formatting
                },
                "fields": "userEnteredFormat"  # Clear all formatting properties
            }
        }]
    }

    service.spreadsheets().batchUpdate(
    spreadsheetId=SPREADSHEET_ID,
        body=clear_request
    ).execute()
    
    service.spreadsheets().values().clear(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_NAME}'!A:Z"
    ).execute()
    
    # Add info row at row 1
    total_problems = len(data) - 1  # Subtract 1 since the first row of `data` is the header.    
    info_row = [f"Total Problems: {total_problems}"] + [""] * 7 + ['=HYPERLINK("https://github.com/noworneverev/leetcode-api", "⭐ Star me on GitHub")', '=HYPERLINK("https://www.linkedin.com/in/yan-ying-liao/", "🦙 Follow me on LinkedIn")', '' ,f"Last Updated: {now_str}"]
    
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_NAME}'!A1:N1",
        valueInputOption='USER_ENTERED',
        body={"values": [info_row]}
    ).execute()    
    
    # Main data starting at row 2
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{SHEET_NAME}'!A2",
        valueInputOption='USER_ENTERED',
        body={"values": data}
    ).execute()
    
    apply_sheet_formatting(service, len(data)+1)  # +2 for header and info rows    