from googleapiclient.discovery import build
from google.oauth2.credentials import Credentials


def get_calendar_service(access_token: str):
    creds = Credentials(token=access_token)
    return build('calendar', 'v3', credentials=creds)

