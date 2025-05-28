import asyncio
import base64
import json
import os

import websockets
from dotenv import load_dotenv
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client

from app.users.models import User
from .functionHandeler import functions

# import logging

# logging.basicConfig(level=logging.DEBUG)

load_dotenv()
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
if not (OPENAI_API_KEY):
    raise ValueError('Missing OpenAI environment variable. Please set them in the .env file.')
LOG_EVENT_TYPES = [
    'error', 'response.content.done', 'rate_limits.updated', 'response.done',
    'input_audio_buffer.committed', 'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started', 'session.created', 'response.function_call', 'response.create',
    'conversation.item.create', 'response.function_call_arguments.done',
]
SHOW_TIMING_MATH = False


class SessionManager:
    def __init__(self, VOICE=None, SYSTEM_MESSAGE=None, GOOGLE_CREDS=None, USER=None, CREATIVITY=0.6):
        self.stream_sid = None
        self.latest_media_timestamp = 0
        self.last_assistant_item = None
        self.mark_queue = []
        self.response_start_timestamp_twilio = None
        self.VOICE = VOICE
        self.SYSTEM_MESSAGE = SYSTEM_MESSAGE
        self.CREATIVITY = CREATIVITY
        self.CALL_ID = None
        self.GOOGLE_CREDS = GOOGLE_CREDS
        self.USER = User(**json.loads(USER or "d"))
        self.client = Client(self.USER.config_user['credentials']['TWILIO_ACCOUNT_SID'],
                             self.USER.config_user['credentials']['TWILIO_AUTH_TOKEN'])
        self.callDB=None
        # print(f"Voice: {self.VOICE} Instructions: {self.SYSTEM_MESSAGE} Creativity: {self.CREATIVITY}")
    def setSession(self, VOICE=None, SYSTEM_MESSAGE=None, GOOGLE_CREDS=None, USER=None, CREATIVITY=0.6,CALL=None):
        self.VOICE = VOICE
        self.SYSTEM_MESSAGE = SYSTEM_MESSAGE
        self.GOOGLE_CREDS = GOOGLE_CREDS
        self.USER = User(**json.loads(USER))
        self.client = Client(self.USER.config_user['credentials']['TWILIO_ACCOUNT_SID'],
                             self.USER.config_user['credentials']['TWILIO_AUTH_TOKEN'])
        self.CREATIVITY = CREATIVITY
        self.callDB=CALL

    async def initialize_session(self, openai_ws):
        """Inicializa la sesión con OpenAI."""
        print(f'Functions: {functions.to_dict()}')
        session_update = {
            "type": "session.update",
            "session": {
                "turn_detection": {"type": "server_vad"},
                "input_audio_format": "g711_ulaw",
                "output_audio_format": "g711_ulaw",
                "voice": self.VOICE,
                "instructions": self.SYSTEM_MESSAGE,
                "modalities": ["text", "audio"],
                "temperature": 1,
                "tools": functions.to_dict(),
            }
        }
        # print('Enviando actualización de sesión:', json.dumps(session_update))
        await openai_ws.send(json.dumps(session_update))
        # La IA habla primero (comentalo si no quieres que eso pase)
        await self.send_initial_conversation_item(openai_ws)

    async def handle_function_call(self, item: dict):
        # print("Handling function call:", item)
        # fn_def = next((f for f in functions if f['schema']['name'] == item['name']), None)
        fn_def = functions.get_by_name(item['name'])
        if not fn_def:
            raise ValueError(f"No handler found for function: {item['name']}")

        try:
            args = json.loads(item['arguments'])
            args['call_id'] = self.CALL_ID
            print(f'Args en handle: {args}')
        except json.JSONDecodeError:
            return json.dumps({
                "error": "Invalid JSON arguments for function call."
            })

        try:
            # print("Calling function:", fn_def['schema']['name'], args)
            # print("Calling function")
            # result = await fn_def['handler'](args, self.GOOGLE_CREDS)

            # print(f'Google Creds: {self.GOOGLE_CREDS}')
            result = await fn_def.handler(args, self.USER,self.callDB)
            return result
        except Exception as err:
            print(f"Error running function {item['name']}:", err)
            return json.dumps({
                "error": f"Error running function {item['name']}: {str(err)}"
            })

    async def send_initial_conversation_item(self, openai_ws):
        """Envía el mensaje inicial para que la IA hable primero."""
        initial_conversation_item = {
            "type": "conversation.item.create",
            "item": {
                "type": "message",
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": (
                            "Salude al usuario con '¡Hola! Soy un asistente de voz de IA con tecnología de "
                            "Twilio y la API en tiempo real de OpenAI. Puedes pedirme datos, chistes o "
                            "Cualquier cosa que puedas imaginar. ¿Cómo puedo ayudarte?'"
                        )
                    }
                ]
            }
        }
        await openai_ws.send(json.dumps(initial_conversation_item))
        await openai_ws.send(json.dumps({"type": "response.create"}))

    async def handle_media_stream(self, websocket: WebSocket):
        """Gestiona las conexiones WebSocket entre Twilio y OpenAI."""
        # print("Cliente conectado")
        await websocket.accept()

        async with websockets.connect(
                'wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview',
                additional_headers={
                    "Authorization": f"Bearer {self.USER.config_user['credentials']['OPENAI_API_KEY']}",
                    "OpenAI-Beta": "realtime=v1"
                }
        ) as openai_ws:
            await self.initialize_session(openai_ws)

            # Ejecutar tareas para enviar y recibir datos simultáneamente
            await asyncio.gather(
                self.receive_from_twilio(websocket, openai_ws),
                self.send_to_twilio(websocket, openai_ws)
            )

    async def receive_from_twilio(self, websocket: WebSocket, openai_ws):
        """Recibe datos de audio desde Twilio y los envía a OpenAI."""
        try:
            async for message in websocket.iter_text():
                data = json.loads(message)

                if data['event'] == 'media' and openai_ws.state.OPEN:
                    self.latest_media_timestamp = int(data['media']['timestamp'])
                    audio_append = {
                        "type": "input_audio_buffer.append",
                        "audio": data['media']['payload']
                    }
                    await openai_ws.send(json.dumps(audio_append))

                elif data['event'] == 'start':
                    self.stream_sid = data['start']['streamSid']
                    self.CALL_ID = data['start']['callSid']
                    # print(f"Stream iniciado: {self.stream_sid}")
                    # print(f"Stream callSid: {self.CALL_ID}")
                    # self.client.calls.get(self.CALL_ID)
                    self.response_start_timestamp_twilio = None
                    self.latest_media_timestamp = 0
                    self.last_assistant_item = None
                elif data['event'] == 'mark':
                    if self.mark_queue:
                        self.mark_queue.pop(0)
                elif data['event'] == 'stop':
                    print("Cliente detuvo la llamada")
                    if self.mark_queue:
                        self.mark_queue.pop(0)
                    await openai_ws.close()

        except WebSocketDisconnect:
            print("Cliente desconectado.")
            if openai_ws.state.OPEN:
                await openai_ws.close()

    async def send_to_twilio(self, websocket: WebSocket, openai_ws):
        """Recibe eventos de OpenAI y envía audio a Twilio."""
        try:
            async for message in openai_ws:
                response = json.loads(message)
                if response['type'] in LOG_EVENT_TYPES:
                    print(f"Received event: {response['type']}", response)

                if response['type'] == 'session.updated':
                    print("Session updated successfully:", response)

                if response['type'] == 'response.audio.delta' and response.get('delta'):
                    try:
                        audio_payload = base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')
                        audio_delta = {
                            "event": "media",
                            "streamSid": self.stream_sid,
                            "media": {"payload": audio_payload}
                        }
                        await websocket.send_json(audio_delta)
                        if self.response_start_timestamp_twilio is None:
                            self.response_start_timestamp_twilio = self.latest_media_timestamp
                            if SHOW_TIMING_MATH:
                                print(
                                    f"Setting start timestamp for new response: {self.response_start_timestamp_twilio}ms")

                            # Update last_assistant_item safely
                        if response.get('item_id'):
                            self.last_assistant_item = response['item_id']

                        await self.send_mark(websocket, openai_ws)
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                if response['type'] == 'response.function_call' or response[
                    'type'] == 'response.function_call_arguments.done':
                    # print(f'Intentando llamar funciones', response)
                    # print(f'Args: {response["arguments"]}')
                    # print(f'Function Id: {response["item_id"]}')
                    results = await self.handle_function_call(response)
                    # print(f'Resultados de la funcion: {results}')
                    # if results == [] or results == None:
                    #    results = "No hay nada"

                    # Envía los resultados de vuelta a OpenAI
                    await openai_ws.send(json.dumps({
                        "type": "conversation.item.create",
                        "item": {
                            "type": "function_call_output",
                            "call_id": response['call_id'],
                            # "content": json.dumps(results),
                            "output": json.dumps(results),
                        }
                    }))
                    await openai_ws.send(json.dumps({"type": "response.create"}))

                if response['type'] == 'input_audio_buffer.speech_started':
                    # print("Speech started detected")
                    if self.last_assistant_item:
                        # print(f"Interrupting response with id: {self.last_assistant_item}")
                        await self.handle_speech_started_event(websocket, openai_ws)

        except Exception as e:
            print(f"Error al enviar datos a Twilio: {e}")

    async def handle_speech_started_event(self, websocket: WebSocket, openai_ws):
        """Handle interruption when the caller's speech starts."""
        # print("Handling speech started event.")
        if self.mark_queue and self.response_start_timestamp_twilio is not None:
            elapsed_time = self.latest_media_timestamp - self.response_start_timestamp_twilio
            if SHOW_TIMING_MATH:
                print(
                    f"Calculating elapsed time for truncation: {self.latest_media_timestamp} - {self.response_start_timestamp_twilio} = {elapsed_time}ms")

            if self.last_assistant_item:
                if SHOW_TIMING_MATH:
                    print(f"Truncating item with ID: {self.last_assistant_item}, Truncated at: {elapsed_time}ms")

                truncate_event = {
                    "type": "conversation.item.truncate",
                    "item_id": self.last_assistant_item,
                    "content_index": 0,
                    "audio_end_ms": elapsed_time
                }
                await openai_ws.send(json.dumps(truncate_event))

            await websocket.send_json({
                "event": "clear",
                "streamSid": self.stream_sid
            })

            self.mark_queue.clear()
            self.last_assistant_item = None
            self.response_start_timestamp_twilio = None

    async def send_mark(self, websocket, openai_ws):
        if self.stream_sid:
            mark_event = {
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {"name": "responsePart"}
            }
            await websocket.send_json(mark_event)
            self.mark_queue.append('responsePart')
        # await asyncio.gather(self.receive_from_twilio(websocket,openai_ws), self.send_to_twilio(websocket,openai_ws))
