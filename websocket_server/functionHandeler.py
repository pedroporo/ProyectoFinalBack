import json
from typing import Optional, List

import requests
from dotenv import load_dotenv
from fastapi.encoders import jsonable_encoder
from twilio.rest import Client

from app.users.routers import get_google_creds
from websocket_server.Services.Google import get_calendar_service
from websocket_server.schemas import FunctionHandler, FunctionSchema

load_dotenv()

# import logging

# logging.basicConfig(level=logging.DEBUG)


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

    def append(self, item: FunctionHandler):
        self._array.append(item)

    def get_by_name(self, name: str) -> Optional[FunctionHandler]:
        return next((f for f in self._array if f.schema.name == name), None)

    def get_all(self) -> List[FunctionHandler]:
        return self._array


functions = FunctionHandlerArray()




async def check_google_calendar(args, user,callDB):
    creds = await get_google_creds(user=user)
    google_service = get_calendar_service(creds.access_token)

    events_result = google_service.events().list(
        calendarId='primary',
        timeMin=args['time_min'],
        timeMax=args['time_max'],
        singleEvents=True
    ).execute()
    # print(events_result.get('items', []))
    return events_result.get('items', [])


async def create_google_event(args, user,callDB):
    creds = await get_google_creds(user=user)
    # print(f'Google creds in fun create: {creds.to_dict()}')
    google_service = get_calendar_service(creds.access_token)
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


async def send_email(args, user,callDB):
    # from app.users.models import User
    # user: User = await User(google_id=USER_GID).getByGId()+
    # print(f'Usera Gid: {user_gid}')
    # user = await User(google_id=user_gid).getByGId()
    # test = json.loads(args)
    # print(f'Args email: {args}')
    # print(f'User email: {user.to_dict()}')
    # print(f'Google creds in fun: {creds}')
    call=json.loads(callDB)
    print(call)
    print(call["contact_name"])
    print(call["phone_number"])
    contactInfo=(f'\nNombre del contacto: {call["contact_name"]}'
                 f'\nNumero del telefono del contacto de la llamada: {call["phone_number"]}')
    import smtplib
    from email.mime.text import MIMEText
    # smtpObj = smtplib.SMTP(host, port)
    recivers = user.config_user['mail_settings']['MAIL_RECIVERS']
    mail_username = user.config_user['mail_settings']['MAIL_USERNAME']
    mail_password = user.config_user['mail_settings']['MAIL_PASSWORD']
    mail_port = user.config_user['mail_settings']['MAIL_PORT']
    mail_host = user.config_user['mail_settings']['MAIL_HOST']
    try:
        msg = MIMEText(args['body']+contactInfo)
        msg['Subject'] = args['subject']
        msg['From'] = mail_username
        msg['To'] = ', '.join(recivers)
        with smtplib.SMTP_SSL(mail_host, mail_port) as smtp_server:
            smtp_server.login(mail_username, mail_password)
            smtp_server.sendmail(mail_username, recivers, msg.as_string())
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


async def stop_call(args, user,callDB):
    client = Client(user.config_user['credentials']['TWILIO_ACCOUNT_SID'],
                    user.config_user['credentials']['TWILIO_AUTH_TOKEN'])
    client.calls(args['call_id']).update(
        status="completed"
    )
    return json.dumps({"success": f"La llamada a sido finalizada correctamente"})


functions.append(FunctionHandler(
    schema=FunctionSchema(
        name="create_google_event",
        description="Crea un evento en el calendario de Google con los detalles proporcionados (título, fecha/hora de inicio y fin, correo del cliente). Utilizar solo si el cliente ha confirmado que desea agendar una reunión.",
        # description="Crea un evento en el calendario de Google. Antes de crear el evento, verifica con el cliente que la dirección de correo electrónico proporcionada sea correcta. Una vez confirmado, crea el evento con los detalles proporcionados (título, fecha/hora de inicio y fin, correo del cliente). Usar solo después de la confirmación del cliente.",
        parameters={
            "type": "object",
            "properties": {
                "summary": {"type": "string"},
                "start": {"type": "string", "format": "date-time"},
                "end": {"type": "string", "format": "date-time"},
                "email": {"type": "string",
                          "description": "Este es el correo electronico del cliente, debes confirmar que sea correcto."}
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
        description="Verifica disponibilidad en el calendario antes de crear un nuevo evento. Debe usarse siempre antes de intentar agendar una reunión para asegurar que no haya conflictos de horario.",
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
        description="Envía un correo electrónico de confirmación. Si la reunión se agendó, notifica al encargado que la cita está confirmada e incluye los detalles (fecha, hora, enlace, etc.). Si el cliente no quiere agendar reunión pero desea ser contactado, envía un correo informando al encargado que se le contactará pronto y, si es posible, incluye información relevante de la conversación.",
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
functions.append(FunctionHandler(
    schema=FunctionSchema(
        name="stop_call",
        description="Finaliza una llamada activa automáticamente cuando se detecta que la conversación ha terminado (por ejemplo, si el usuario dice 'adiós', indica que no necesita más ayuda, o si no hay interacción por ninguna de las partes durante al menos 15 segundos). Esta función cuelga la llamada de forma segura y devuelve una confirmación de que la llamada ha sido finalizada correctamente.",
        parameters={
            "type": "object",
            "properties": {
            },
            "required": [
            ],
            "additionalProperties": False,
        }
    ),
    handler=stop_call
))
