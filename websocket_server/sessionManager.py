import os
import json
import base64
import asyncio
from fastapi import WebSocket
from fastapi.websockets import WebSocketDisconnect
import websockets
from dotenv import load_dotenv
from twilio.rest import Client
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
    'input_audio_buffer.speech_started', 'session.created'
]
SHOW_TIMING_MATH = False


class SessionManager:
    def __init__(self,VOICE=None,SYSTEM_MESSAGE=None,CREATIVITY=0.6):
        self.stream_sid = None
        self.latest_media_timestamp = 0
        self.last_assistant_item = None
        self.mark_queue = []
        self.response_start_timestamp_twilio = None
        self.VOICE=VOICE
        self.SYSTEM_MESSAGE=SYSTEM_MESSAGE
        self.CREATIVITY=CREATIVITY
        self.CALL_ID=None
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        #print(f"Voice: {self.VOICE} Instructions: {self.SYSTEM_MESSAGE} Creativity: {self.CREATIVITY}")

    async def initialize_session(self, openai_ws):
        """Inicializa la sesión con OpenAI."""
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
            }
        }
        print('Enviando actualización de sesión:', json.dumps(session_update))
        await openai_ws.send(json.dumps(session_update))
        # La IA habla primero (comentalo si no quieres que eso pase)
        await self.send_initial_conversation_item(openai_ws)

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
        print("Cliente conectado")
        await websocket.accept()

        async with websockets.connect(
                'wss://api.openai.com/v1/realtime?model=gpt-4o-mini-realtime-preview',
                additional_headers={
                    "Authorization": f"Bearer {OPENAI_API_KEY}",
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
                    print(f"Stream iniciado: {self.stream_sid}")
                    self.response_start_timestamp_twilio = None
                    self.latest_media_timestamp = 0
                    self.last_assistant_item = None
                elif data['event'] == 'mark':
                    if self.mark_queue:
                        self.mark_queue.pop(0)
                elif data['event'] == 'stop':
                    print("Cliente detuvo la llamada")
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

                        await self.send_mark(websocket,openai_ws)
                    except Exception as e:
                        print(f"Error processing audio data: {e}")
                if response['type'] == 'input_audio_buffer.speech_started':
                    print("Speech started detected")
                    if self.last_assistant_item:
                        print(f"Interrupting response with id: {self.last_assistant_item}")
                        await self.handle_speech_started_event(websocket,openai_ws)

        except Exception as e:
            print(f"Error al enviar datos a Twilio: {e}")

    async def handle_speech_started_event(self, websocket: WebSocket, openai_ws):
        """Handle interruption when the caller's speech starts."""
        print("Handling speech started event.")
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

    async def send_mark(self,websocket,openai_ws):
        if self.stream_sid:
            mark_event = {
                "event": "mark",
                "streamSid": self.stream_sid,
                "mark": {"name": "responsePart"}
            }
            await websocket.send_json(mark_event)
            self.mark_queue.append('responsePart')
        #await asyncio.gather(self.receive_from_twilio(websocket,openai_ws), self.send_to_twilio(websocket,openai_ws))