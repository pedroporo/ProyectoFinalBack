import os
import asyncio
from twilio.rest import Client
from dotenv import load_dotenv
import re
from websocket_server.server import Server
load_dotenv()
# Configuration
TWILIO_ACCOUNT_SID = os.getenv('TWILIO_ACCOUNT_SID')
TWILIO_AUTH_TOKEN = os.getenv('TWILIO_AUTH_TOKEN')
PHONE_NUMBER_FROM = os.getenv('TWILIO_NUMBER')
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
raw_domain = os.getenv('DOMAIN', '')
DOMAIN = re.sub(r'(^\w+:|^)\/\/|\/+$', '', raw_domain) # Strip protocols and trailing slashes from DOMAIN
call_id=None
PORT = int(os.getenv('PORT', 8765))
server = Server(PROFILE_ID=2)

if not (TWILIO_ACCOUNT_SID and TWILIO_AUTH_TOKEN and PHONE_NUMBER_FROM and OPENAI_API_KEY):
    raise ValueError('Missing Twilio and/or OpenAI environment variables. Please set them in the .env file.')

# Initialize Twilio client
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


async def check_number_allowed(to):
    try:
        # Saltarse el filtro de llamaddas
        #OVERRIDE_NUMBERS = ['+34653072842','+34678000893','+34642447846']
        #if to in OVERRIDE_NUMBERS:
            #return True
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
async def make_call(phone_number_to_call: str):
    """Make an outbound call."""
    if not phone_number_to_call:
        raise ValueError("Please provide a phone number to call.")

    is_allowed = await check_number_allowed(phone_number_to_call)
    if not is_allowed:
        raise ValueError(f"The number {phone_number_to_call} is not recognized as a valid outgoing number or caller ID.")

    # Ensure compliance with applicable laws and regulations
    # All of the rules of TCPA apply even if a call is made by AI.
    # Do your own diligence for compliance.

    outbound_twiml = (
        f'<?xml version="1.0" encoding="UTF-8"?>'
        f'<Response><Connect><Stream url="wss://{DOMAIN}/media-stream" /></Connect><Pause length="15"/><Hangup/></Response>'
    )

    call = client.calls.create(
        from_=PHONE_NUMBER_FROM,
        to=phone_number_to_call,
        twiml=outbound_twiml,
        record=True,
        machine_detection=True,
        machine_detection_timeout=15,
        time_limit=600,
        timeout=15,

    )
    #print(call.__dict__)
    call_id=call.sid
    server.CALL_ID=call_id
    await log_call_sid(call_id)


async def log_call_sid(call_sid):
    """Log the call SID."""
    print(f"Call started with SID: {call_sid}")


if __name__ == "__main__":
    #phone_number='+34678000893'
    phone_number = '+34653072842'
    #for number in phone_numbers:
        #loop2=asyncio.get_event_loop()
        #loop2.run_until_complete(make_call(number))
    loop = asyncio.get_event_loop()
    loop.run_until_complete(make_call(phone_number))
    server.run()
    #server.CALL_ID=call_id

