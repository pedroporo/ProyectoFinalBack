from dotenv import load_dotenv
from datetime import datetime
from fastapi.encoders import jsonable_encoder
import os
import requests
import json
from websocket_server.schemas import FunctionHandler, FunctionSchema
from typing import Dict, Any, Callable, Optional, List
from websocket_server.Services.Google import get_calendar_service

load_dotenv()

MAIL_HOST = os.getenv('MAIL_HOST')
MAIL_PORT = int(os.getenv('MAIL_PORT'))
MAIL_USERNAME = os.getenv('MAIL_USERNAME')
MAIL_PASSWORD = os.getenv('MAIL_PASSWORD')
MAIL_RECIVERS = os.getenv('MAIL_RECIVERS')
# import logging

# logging.basicConfig(level=logging.DEBUG)
scopes = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events',
          'https://www.googleapis.com/auth/calendar.events.readonly']

google_creds = None
host = 'smtp.gmail.com'
port = 465


class FunctionHandlerArray:
    def __init__(self):
        self._array: List[FunctionHandler] = []

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        # print(jsonable_encoder([f.schema.to_dict() for f in self._array]))
        return jsonable_encoder([f.schema.to_dict() for f in self._array])

    def toJSON(self):
        return json.dumps(self.to_dict(), indent=4)

    # def append(self, item: Dict[str, Any]):
    #     # Validar que el objeto tenga las claves necesarias
    #     if not isinstance(item, dict) or "schema" not in item or "handler" not in item:
    #         raise TypeError("Item must be a dictionary with 'schema' and 'handler' keys.")
    #
    #     # Crear instancia de FunctionSchema desde el diccionario
    #     schema_data = item["schema"]
    #     schema = FunctionSchema(
    #         name=schema_data["name"],
    #         parameters=schema_data["parameters"],
    #         description=schema_data.get("description")
    #     )
    #
    #     # Crear instancia de FunctionHandler con la función handler proporcionada
    #     handler = FunctionHandler(schema=schema, handler=item["handler"])
    #
    #     # Agregar al array interno
    #     self._array.append(handler)
    def append(self, item: FunctionHandler):
        self._array.append(item)

    def get_by_name(self, name: str) -> Optional[FunctionHandler]:
        return next((f for f in self._array if f.schema.name == name), None)

    def get_all(self) -> List[FunctionHandler]:
        return self._array


functions = FunctionHandlerArray()


# functions.append({
#     "schema": {
#         "name": "get_weather_from_coords",
#         "type": "function",
#         "description": "Get the current weather",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "latitude": {
#                     "type": "number",
#                 },
#                 "longitude": {
#                     "type": "number",
#                 },
#             },
#             "required": ["latitude", "longitude"],
#         },
#     },
#     "handler": lambda args: get_weather(args)
# })
#
# functions.append({
#     "schema": {
#         "name": "check_google_calendar",
#         "type": "function",
#         "description": "Verifica disponibilidad en el calendario",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "time_min": {"type": "string", "format": "date-time"},
#                 "time_max": {"type": "string", "format": "date-time"},
#             },
#             "required": ["time_min", "time_max"],
#             "additionalProperties": False,
#         },
#         "strict": True
#     },
#     "handler": lambda args, creds: check_google_calendar(args, creds)
# })
# functions.append({
#     "schema": {
#         "name": "create_google_event",
#         "type": "function",
#         "description": "Crea un evento en el calendario",
#         "parameters": {
#             "type": "object",
#             "properties": {
#                 "summary": {"type": "string"},
#                 "start": {"type": "string", "format": "date-time"},
#                 "end": {"type": "string", "format": "date-time"},
#                 "email": {"type": "string"}
#             },
#             "required": ["summary", "start", "end", "email"],
#             "additionalProperties": False,
#         },
#         "strict": True
#     },
#     "handler": lambda args, creds: create_google_event(args, creds)
# })


async def check_google_calendar(args, creds):
    # print(f'Google creds in fun: {creds}')
    google_service = get_calendar_service(creds)
    events_result = google_service.events().list(
        calendarId='primary',
        timeMin=args['time_min'],
        timeMax=args['time_max'],
        singleEvents=True
    ).execute()
    # print(events_result.get('items', []))
    return events_result.get('items', [])


async def create_google_event(args, creds):
    # print(f'Google creds in fun: {creds}')
    google_service = get_calendar_service(creds)
    try:
        event = {
            'summary': args['summary'],
            'start': {'dateTime': args['start']},
            'end': {'dateTime': args['end']},
            'attendees': [{'email': args['email']}]
        }
        # print(f"Credenciales usadas: {creds[:15]}...")
        # print(f"Intentando crear evento: {json.dumps(event, indent=2)}")
        return google_service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
    except Exception as e:
        return {"error": f"Formato de fecha inválido, usar ISO 8601: {e}"}


def send_email(args):
    # print(f'Google creds in fun: {creds}')
    import smtplib
    from email.mime.text import MIMEText
    # smtpObj = smtplib.SMTP(host, port)
    recivers = json.loads(MAIL_RECIVERS)
    try:
        msg = MIMEText(args['body'])
        msg['Subject'] = args['subject']
        msg['From'] = MAIL_USERNAME
        msg['To'] = ', '.join(recivers)
        with smtplib.SMTP_SSL(MAIL_HOST, MAIL_PORT) as smtp_server:
            smtp_server.login(MAIL_USERNAME, MAIL_PASSWORD)
            smtp_server.sendmail(MAIL_USERNAME, recivers, msg.as_string())
        return {"success": f"El email a sido enviado con exito"}

    except Exception as e:
        return {"error": f"Ha ocurrido un error enviando el email: {e}"}


async def get_weather(args):
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={args['latitude']}&longitude={args['longitude']}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    current_temp = data.get('current', {}).get('temperature_2m')
    return json.dumps({"temp": current_temp})


functions.append(FunctionHandler(
    schema=FunctionSchema(
        name="create_google_event",
        description="Crea un evento en el calendario",
        parameters={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"},
                "email": {"type": "string"}
            },
            "required": ["summary", "start", "end", "email"],
            "additionalProperties": False,
        }
    ),
    handler=create_google_event
))
functions.append(FunctionHandler(
    schema=FunctionSchema(
        name="check_google_calendar",
        description="Verifica disponibilidad en el calendario importante hacer esto antes de crear un nuevo evento",
        parameters={
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "format": "date-time"},
                "time_max": {"type": "string", "format": "date-time"},
            },
            "required": ["time_min", "time_max"],
            "additionalProperties": False,
        }
    ),
    handler=check_google_calendar
))

functions.append(FunctionHandler(
    schema=FunctionSchema(
        name="send_email",
        description="Envia un email a hugo con el correo del cliente si esta interesado en que lo contactemos y si se puede se envia algo de contexto de la conversacion",
        parameters={
            "type": "object",
            "properties": {
                "subject": {"type": "string",
                            "description": "Aviso de que hay un cliente interesado en que le contactemos."},
                "body": {"type": "string",
                         "description": "El contenido del correo a enviar, junto a la presentacion de quien eres y la informacion."}
            },
            "required": [
                "subject",
                "body"
            ],
            "additionalProperties": False,
        }
    ),
    handler=send_email
))
