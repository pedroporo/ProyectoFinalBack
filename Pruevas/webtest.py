import base64
import json
import os
import logging
from dotenv import load_dotenv
load_dotenv()
import websocket
import time

from flask import Flask,render_template
from flask_sockets import Sockets

app = Flask(__name__)
sockets = Sockets(app)
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

VOICE='alloy'
SYSTEM_MESSAGE='Eres un asistente de IA servicial y jovial, a quien le encanta charlar sobre cualquier tema que interese al usuario y siempre está dispuesto a ofrecerle información. Te encantan los chistes de papá, los chistes de búhos y los rickrolls, sutilmente. Mantén siempre una actitud positiva, pero incluye un chiste cuando sea necesario.'
HTTP_SERVER_PORT = 8765

LOG_EVENT_TYPES = [
    'response.content.done',
    'rate_limits.updated',
    'response.done',
    'input_audio_buffer.committed',
    'input_audio_buffer.speech_stopped',
    'input_audio_buffer.speech_started',
    'session.created'
]
def log(msg, *args):
    print(f"Media WS: ", msg, *args)


@app.route('/twiml', methods=['POST'])
def return_twiml():
    print("POST TwiML")
    return render_template('streams.xml')

@sockets.route('/media')
def echo(ws):
    app.logger.info("Connection accepted")
    openAIWS=websocket.WebSocketApp(
    "wss://api.openai.com/v1/realtime?model=gpt-4o-realtime-preview-2024-12-17",
        header=[
            "Authorization: Bearer " + OPENAI_API_KEY,
            "OpenAI-Beta: realtime=v1"
        ],
    )
    streamSid = None
    def send_session_update():
        session_update = {
            'type': 'session.update',
            'session': {
                'turn_detection': {'type': 'server_vad'},
                'input_audio_format': 'g711_ulaw',
                'output_audio_format': 'g711_ulaw',
                'voice': VOICE,
                'instructions': SYSTEM_MESSAGE,
                'modalities': ["text", "audio"],
                'temperature': 0.8,
            }
        }
        print('Sending session update:', json.dumps(session_update))
        openAIWS.send(json.dumps(session_update))



    def on_open():
        print('Connected to the OpenAI Realtime API')
        time.sleep(0.25)  # Ensure connection stability, send after .25 seconds
        send_session_update()

    def on_message(data):
        try:
            response = json.loads(data)
            if response['type'] in LOG_EVENT_TYPES:
                print(f'Received event: {response["type"]}', response)
            if response['type'] == 'session.updated':
                print('Session updated successfully:', response)
            if response['type'] == 'response.audio.delta' and 'delta' in response:
                audio_delta = {
                    'event': 'media',
                    'streamSid': streamSid,
                    'media': {'payload': base64.b64encode(base64.b64decode(response['delta'])).decode('utf-8')}
                }
                ws.send(json.dumps(audio_delta))
        except Exception as error:
            print('Error processing OpenAI message:', error, 'Raw message:', data)
    def on_close():
        print('Disconnected from the OpenAI Realtime API')
    def on_error(error):
        print('Error in the OpenAI WebSocket:', error)
    # Assuming openAiWs is an instance of a WebSocket or similar
    openAIWS.on_open = on_open
    openAIWS.on_message=on_message
    openAIWS.on_close=on_close
    openAIWS.on_error=on_error
    # A lot of messages will be sent rapidly. We'll stop showing after the first one.
    has_seen_media = False
    message_count = 0
    while not ws.closed:
        message = ws.receive()
        if message is None:
            app.logger.info("No message received...")
            continue

        # Messages are a JSON encoded string
        data = json.loads(message)

        # Using the event type you can determine what type of message you are receiving
        if data['event'] == "connected":
            streamSid=data['sid']
            app.logger.info("Connected Message received: {}".format(message))
        if data['event'] == "start":
            app.logger.info("Start Message received: {}".format(message))
        if data['event'] == "media":
            if openAIWS.keep_running:
                if not has_seen_media:
                    app.logger.info("Media message: {}".format(message))
                    payload = data['media']['payload']
                    audioAppend = {
                        'type': 'input_audio_buffer.append',
                        'audio': data.media.payload
                    }
                    openAIWS.send(json.dumps(audioAppend))
                    app.logger.info("Payload is: {}".format(payload))
                    chunk = base64.b64decode(payload)
                    app.logger.info("That's {} bytes".format(len(chunk)))
                    app.logger.info("Additional media messages from WebSocket are being suppressed....")
                    has_seen_media = True
        if data['event'] == "closed":
            app.logger.info("Closed Message received: {}".format(message))
            openAIWS.close()
            break
        message_count += 1

    app.logger.info("Connection closed. Received a total of {} messages".format(message_count))


if __name__ == '__main__':
    app.logger.setLevel(logging.DEBUG)
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler

    server = pywsgi.WSGIServer(('', HTTP_SERVER_PORT), app, handler_class=WebSocketHandler)
    print("Server listening on: http://localhost:" + str(HTTP_SERVER_PORT))
    server.serve_forever()