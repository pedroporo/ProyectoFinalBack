import array
from datetime import datetime
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse
from fastapi import APIRouter, Depends, status, HTTPException, FastAPI, Request, Cookie
import requests
import json
from schemas import FunctionHandler, FunctionSchema
from typing import Dict, Any, Callable, Optional, List
from websocket_server.Services.Google import get_calendar_service
from app.users.models import GoogleCredential
from app.users.routers import get_google_creds

# import logging

# logging.basicConfig(level=logging.DEBUG)
scopes = ['https://www.googleapis.com/auth/calendar', 'https://www.googleapis.com/auth/calendar.readonly',
          'https://www.googleapis.com/auth/calendar.events',
          'https://www.googleapis.com/auth/calendar.events.readonly']

google_creds = None


class FunctionHandlerArray:
    def __init__(self):
        self._array: List[FunctionHandler] = []

    def to_dict(self):
        """Convierte la instancia del modelo a un diccionario serializable"""
        print(jsonable_encoder([f.schema.to_dict() for f in self._array]))
        return jsonable_encoder([f.schema.to_dict() for f in self._array])

    def toJSON(self):
        return json.dumps(self.to_dict(), indent=4)

    def append(self, item: Dict[str, Any]):
        # Validar que el objeto tenga las claves necesarias
        if not isinstance(item, dict) or "schema" not in item or "handler" not in item:
            raise TypeError("Item must be a dictionary with 'schema' and 'handler' keys.")

        # Crear instancia de FunctionSchema desde el diccionario
        schema_data = item["schema"]
        schema = FunctionSchema(
            name=schema_data["name"],
            parameters=schema_data["parameters"],
            description=schema_data.get("description")
        )

        # Crear instancia de FunctionHandler con la función handler proporcionada
        handler = FunctionHandler(schema=schema, handler=item["handler"])

        # Agregar al array interno
        self._array.append(handler)

    def get_all(self) -> List[FunctionHandler]:
        return self._array


functions = FunctionHandlerArray()

functions.append({
    "schema": {
        "name": "get_weather_from_coords",
        "type": "function",
        "description": "Get the current weather",
        "parameters": {
            "type": "object",
            "properties": {
                "latitude": {
                    "type": "number",
                },
                "longitude": {
                    "type": "number",
                },
            },
            "required": ["latitude", "longitude"],
        },
    },
    "handler": lambda args: get_weather(args)
})

functions.append({
    "schema": {
        "name": "check_google_calendar",
        "type": "function",
        "description": "Verifica disponibilidad en el calendario",
        "parameters": {
            "type": "object",
            "properties": {
                "time_min": {"type": "string", "format": "date-time"},
                "time_max": {"type": "string", "format": "date-time"},
            },
            "required": ["time_min", "time_max"],
            "additionalProperties": False,
        },
        "strict": True
    },
    "handler": lambda args, creds: check_google_calendar(args, creds)
})
functions.append({
    "schema": {
        "name": "create_google_event",
        "type": "function",
        "description": "Crea un evento en el calendario",
        "parameters": {
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"},
                "email": {"type": "string"}
            },
            "required": ["summary", "start", "end", "email"],
            "additionalProperties": False,
        },
        "strict": True
    },
    "handler": lambda args, creds: create_google_event(args, creds)
})


async def check_google_calendar(args, creds):
    google_service = await get_calendar_service(creds.access_token)
    events_result = google_service.events().list(
        calendarId='primary',
        timeMin=args['time_min'],
        timeMax=args['time_max'],
        singleEvents=True
    ).execute()
    return events_result.get('items', [])


async def create_google_event(args, creds):
    google_service = await get_calendar_service(creds.access_token)
    try:
        event = {
            'summary': args['summary'],
            'start': {'dateTime': datetime.fromisoformat(args['start'])},
            'end': {'dateTime': datetime.fromisoformat(args['end'])},
            'attendees': [{'email': args['email']}]
        }
        return google_service.events().insert(
            calendarId='primary',
            body=event
        ).execute()
    except Exception as e:
        return {"error": f"Formato de fecha inválido, usar ISO 8601: {e}"}


async def get_weather(args):
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={args['latitude']}&longitude={args['longitude']}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    current_temp = data.get('current', {}).get('temperature_2m')
    return json.dumps({"temp": current_temp})
