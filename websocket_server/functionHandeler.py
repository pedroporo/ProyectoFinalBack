import array

import requests
import json
from schemas import FunctionHandler, FunctionSchema
from typing import Dict, Any, Callable, Optional, List


class FunctionHandlerArray:
    def __init__(self):
        self._array: List[FunctionHandler] = []

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
        },
    },
    "handler": lambda args: check_google_calendar(args)
})


async def check_google_calendar(args, time_min, time_max):
    events_result = self.google_service.events().list(
        calendarId='primary',
        timeMin=args['time_min'],
        timeMax=time_max,
        singleEvents=True
    ).execute()
    return events_result.get('items', [])


async def create_google_event(self, summary, start, end, email):
    event = {
        'summary': summary,
        'start': {'dateTime': start},
        'end': {'dateTime': end},
        'attendees': [{'email': email}]
    }
    return self.google_service.events().insert(
        calendarId='primary',
        body=event
    ).execute()


async def get_weather(args):
    response = requests.get(
        f"https://api.open-meteo.com/v1/forecast?latitude={args['latitude']}&longitude={args['longitude']}&current=temperature_2m,wind_speed_10m&hourly=temperature_2m,relative_humidity_2m,wind_speed_10m"
    )
    data = response.json()
    current_temp = data.get('current', {}).get('temperature_2m')
    return json.dumps({"temp": current_temp})
