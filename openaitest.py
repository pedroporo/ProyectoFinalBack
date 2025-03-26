import os
from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()
OPENAI_API_KEY=os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)

instructions="Talk like a pirate"
rolIa="developer"
completion = client.chat.completions.create(
    model="gpt-4o",

    messages=[
        {
            "role": rolIa,
            "content": instructions
        },
        {
            "role": "user",
            "content": "Write a one-sentence bedtime story about a unicorn."
        }
    ]
)

print(completion.choices[0].message.content)

#Pillar modelos disponibles
modelos=client.models.list()
for modelo in modelos:
    print(modelo)



#audio_file = open("/path/to/file/speech.mp3", "rb")
#transcription = client.audio.transcriptions.create(
#  model="whisper-1",
#  file=audio_file,
#  response_format="text",
#  prompt="ZyntriQix, Digique Plus, CynapseFive, VortiQore V8, EchoNix Array, OrbitalLink Seven, DigiFractal Matrix, PULSE, RAPT, B.R.I.C.K., Q.U.A.R.T.Z., F.L.I.N.T."
#)

#print(transcription.text)

#https://platform.openai.com/docs/api-reference/realtime

#https://platform.openai.com/docs/guides/realtime?connection-example=python