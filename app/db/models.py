from django.db import models
import os
import asyncio
from twilio.rest import Client
from dotenv import load_dotenv
import re
import time
load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain)  # Strip protocols and trailing slashes from DOMAIN

class Agent(models.Model):
    VOICE_OPTIONS = {
        1: "alloy",
        2: "ash",
        3: "ballad",
        4: "coral",
        5: "echo",
        6: "sage",
        7: "shimmer",
        8: "verse",
    }
    name=models.CharField(max_length=30)
    voice=models.IntegerField(max_length=1,choices=VOICE_OPTIONS)
    descripccion=models.CharField()
    instrucciones=models.CharField()
    empezar_ia=models.BooleanField(default=False)
    velozidadVoz=models.FloatField()
    creatividadVoz=models.FloatField()
    silenceCloseCall=models.IntegerField()
    callMaxDuration=models.IntegerField()


    if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
        raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

    # Initialize Twilio client


    async def check_number_allowed(self,to):
        try:
            # Saltarse el filtro de llamaddas
            # OVERRIDE_NUMBERS = ['+34653072842','+34678000893','+34642447846']
            # if to in OVERRIDE_NUMBERS:
            # return True
            return True
            incoming_numbers = client.incoming_phone_numbers.list(phone_number=to)
            if incoming_numbers:
                return True

            outgoing_caller_ids = client.outgoing_caller_ids.list(phone_number=to)
            if outgoing_caller_ids:
                return True

            return False
        except Exception as e:
            print(f"Error checking phone number: {e}")
            return False

    async def make_call(self, phone_number_to_call: str):
    #async def make_call(self,phone_number_to_call: str):
        """Make an outbound call."""
        #if not phone_number_to_call:
        #    raise ValueError("Please provide a phone number to call.")

        #is_allowed = await self.check_number_allowed(phone_number_to_call)
        #if not is_allowed:
        #    raise ValueError(
        #        f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

        # Ensure compliance with applicable laws and regulations
        # All of the rules of TCPA apply even if a call is made by AI.
        # Do your own diligence for compliance.

        outbound_twiml = (
            f'<?xml version="1.0" encoding="UTF-8"?>'
            f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect></Response>'
        )
        self.client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        call = self.client.calls.create(
            from_=PHONE_NUMBER_FROM,
            to=phone_number_to_call,
            twiml=outbound_twiml,
            record=True,
            machine_detection=True,
            machine_detection_timeout=15,
            time_limit=100,
            timeout=15,
            status_callback=f"https://{DOMAIN}/events",
            status_callback_event=["initiated", "answered"],
            status_callback_method="POST",

        )

        call_id = call.sid
        await self.log_call_sid(call_id)

    def esperar_a_que_finalice(self,call_sid):
        while True:
            llamada = self.client.calls(call_sid).fetch()
            print(f"Estado actual de la llamada {call_sid}: {llamada.status}")
            if llamada.status in ['completed', 'failed', 'busy', 'no-answer']:
                # La llamada ha finalizado (o no pudo completarse)
                break
            time.sleep(5)  # Espera 5 segundos antes de volver a verificar
    async def log_call_sid(self,call_sid):
        """Log the call SID."""
        print(f"Call started with SID: {call_sid}")





