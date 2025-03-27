import os
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

# Find your Account SID and Auth Token at twilio.com/console
# and set the environment variables. See http://twil.io/secure
account_sid = os.environ.get("TWILIO_ACCOUNT_SID")
auth_token = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")

client = Client(account_sid, auth_token)

call = client.calls.create(
    from_=TWILIO_NUMBER,
    to="+34653072842",
    #url="http://demo.twilio.com/docs/voice.xml",
    twiml="<Response><Start><Stream url='wss://localhost:8765/media'></Stream></Start></Response>",
)

print(call)