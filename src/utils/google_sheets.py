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
SHEET_ID_TO_NAME = {
    0: 'LeetCode Questions',
    533665120: 'test'
}
TEST_SHEET_NAME = 'test'
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

PROGRAMMING_LANGUAGES = [
    "Python", "JavaScript", "Java", "C++", "C#", "Go", "Ruby", "Swift", "Kotlin", "Rust",
    "PHP", "TypeScript", "Scala", "Haskell", "Objective-C", "Perl", "Lua", "R", "Dart"
]

SPOKEN_LANGUAGES = [
    "English", "Traditional Chinese", "Simplified Chinese", "Hindi", "Spanish", "Arabic", "Bengali", "Portuguese",
    "Russian", "Japanese", "German", "French", "Italian", "Korean", "Vietnamese", "Turkish",
    "Persian", "Polish", "Dutch", "Thai", "Swedish", "Norwegian", "Finnish", "Danish",
    "Hebrew", "Indonesian", "Malay", "Greek", "Czech", "Romanian", "Hungarian", "Slovak",
    "Ukrainian"
]

prog_values = [{"userEnteredValue": lang} for lang in PROGRAMMING_LANGUAGES]
spoken_values = [{"userEnteredValue": lang} for lang in SPOKEN_LANGUAGES]

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
        'Category',
        'LLM Prompt'
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

        row_idx = idx + 4
        prompt_formula = (
            f"=CONCATENATE("
            f"\"Please solve the LeetCode problem '\""
            f", INDIRECT(\"A\" & ROW())"
            f", \". \", INDIRECT(\"B\" & ROW())"
            f", \"'. Follow these steps:\""
            f", \" 1. First Intuition: Provide a high-level explanation of your approach.\""
            f", \" 2. Problem-Solving Approach: Break down the solution into clear, logical steps.\""
            f", \" 3. Code Implementation: Provide the solution in \", O$1, \" code.\""
            f", \" 4. Complexity Analysis: Analyze the time and space complexity of your solution.\""
            f", \" Answer in \", O$2, \".\")"
        )
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
            q.get('categoryTitle', ''),            
            prompt_formula
        ]
        rows.append(row)
    
    return [headers] + sorted(rows, key=lambda x: x[2], reverse=True)

def apply_sheet_formatting(service, rows_count, sheet_id=0):
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
                "properties": {"sheetId": sheet_id, "gridProperties": {"frozenRowCount": 3}},
                "fields": "gridProperties.frozenRowCount"
            }
        },
        # Set filter for columns A-M
        {
            "setBasicFilter": {
                "filter": {
                    "range": {
                        "sheetId": sheet_id,
                        "startRowIndex": 2,  # Header at row 3
                        "endRowIndex": rows_count,  # Number of rows in the data
                        "startColumnIndex": 0,
                        "endColumnIndex": 15
                    }
                }
            }
        },        
        {
            "repeatCell": {
                "range": {"sheetId": sheet_id, "startRowIndex": 2, "endRowIndex": 3},
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
                    "ranges": [{"sheetId": sheet_id, "startColumnIndex": col}],
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
                    "ranges": [{"sheetId": sheet_id, "startColumnIndex": 5}],
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
                    "sheetId": sheet_id,
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
                    "sheetId": sheet_id,
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
                    "sheetId": sheet_id,
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
                    "sheetId": sheet_id,
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
                    "sheetId": sheet_id,
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
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 7,
                    "endIndex": 9
                },
                "properties": {"pixelSize": 140},
                "fields": "pixelSize"
            }
        },
        {
            "updateDimensionProperties": {
                "range": {
                    "sheetId": sheet_id,
                    "dimension": "COLUMNS",
                    "startIndex": 14,  # Column O (LLM Prompt)
                    "endIndex": 15
                },
                "properties": {"pixelSize": 200},
                "fields": "pixelSize"
            }
        },
        # Format the Like Ratio (%) column as a percentage.
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startColumnIndex": 4,  # Column index for "Like Ratio (%)"
                    "endColumnIndex": 5,
                    "startRowIndex": 3      
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
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startColumnIndex": 13,  
                    "endColumnIndex": 14,
                    "startRowIndex": 0,     
                    "endRowIndex": 2        
                },
                "cell": {
                    "userEnteredFormat": {
                        "horizontalAlignment": "RIGHT"
                    }
                },
                "fields": "userEnteredFormat.horizontalAlignment"
            }
        },            
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,     # O1 (row 1)
                    "endRowIndex": 1,
                    "startColumnIndex": 14, # Column O
                    "endColumnIndex": 15
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": prog_values
                    },
                    "showCustomUi": True,
                    "strict": True
                }
            }
        },
        # Set default value for cell O1 to "Python"
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 0,
                    "endRowIndex": 1,
                    "startColumnIndex": 14,
                    "endColumnIndex": 15
                },
                "cell": {
                    "userEnteredValue": {
                        "stringValue": "Python"
                    }
                },
                "fields": "userEnteredValue"
            }
        },
        {
            "setDataValidation": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,     # O2 (row 2)
                    "endRowIndex": 2,
                    "startColumnIndex": 14, # Column O
                    "endColumnIndex": 15
                },
                "rule": {
                    "condition": {
                        "type": "ONE_OF_LIST",
                        "values": spoken_values
                    },
                    "showCustomUi": True,
                    "strict": True
                }
            }
        },
        # Set default value for cell O2 to "English"
        {
            "repeatCell": {
                "range": {
                    "sheetId": sheet_id,
                    "startRowIndex": 1,
                    "endRowIndex": 2,
                    "startColumnIndex": 14,
                    "endColumnIndex": 15
                },
                "cell": {
                    "userEnteredValue": {
                        "stringValue": "English"
                    }
                },
                "fields": "userEnteredValue"
            }
        }  
    ]

    service.spreadsheets().batchUpdate(
        spreadsheetId=SPREADSHEET_ID,
        body={"requests": requests}
    ).execute()

def update_google_sheet(service, data, sheet_id=0):
    """Update Google Sheet with prepared data"""
    tz = pytz.timezone('Europe/Berlin')
    now_str = datetime.now(tz).strftime("%Y-%m-%d %H:%M %Z")
    sheet_name = SHEET_ID_TO_NAME.get(sheet_id, TEST_SHEET_NAME)
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
                    "sheetId": sheet_id,
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
        range=f"'{sheet_name}'!A:Z"
    ).execute()
    
    # Add info row at row 1
    total_problems = len(data) - 1  # Subtract 1 since the first row of `data` is the header.    
    info_row1 = [f"🧩 Total Problems: {total_problems}", "", "", '=HYPERLINK("https://github.com/noworneverev/leetcode-api", "⭐ Star me on GitHub")']
    info_row2 = [f"🕰️ Last Updated: {now_str}", "", "", '=HYPERLINK("https://www.linkedin.com/in/yan-ying-liao/", "🦙 Follow/Connect with me on LinkedIn")']
    info_row3 = ['Choose the Programming Language for the Prompt']
    info_row4 = ['Choose the Language for the Answer']
    
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A1:D1",
        valueInputOption='USER_ENTERED',
        body={"values": [info_row1]}
    ).execute()    

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A2:D2",
        valueInputOption='USER_ENTERED',
        body={"values": [info_row2]}
    ).execute()    

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!N1:N1",
        valueInputOption='USER_ENTERED',
        body={"values": [info_row3]}
    ).execute()   

    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!N2:N2",
        valueInputOption='USER_ENTERED',
        body={"values": [info_row4]}
    ).execute()   
    
    # Main data starting at row 3
    service.spreadsheets().values().update(
        spreadsheetId=SPREADSHEET_ID,
        range=f"'{sheet_name}'!A3",
        valueInputOption='USER_ENTERED',
        body={"values": data}
    ).execute()
    
    apply_sheet_formatting(service, len(data)+2, sheet_id=sheet_id)  # +2 for info row