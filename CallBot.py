import os
import json
import base64
import asyncio
import argparse
import time

from fastapi import FastAPI, WebSocket, BackgroundTasks
from fastapi.responses import JSONResponse
from fastapi.websockets import WebSocketDisconnect
from twilio.rest import Client
import websockets
class Callbot:
    def __init__(self,TWILIO_ACCOUNT_SID,TWILIO_AUTH_TOKEN,PHONE_NUMBER_FROM,OPENAI_API_KEY,VOICE,instrucciones_chat,telefonoALlamar):
        print('a')

