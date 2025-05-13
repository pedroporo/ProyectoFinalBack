import asyncio
import json
import os

from dotenv import load_dotenv
from openai import OpenAI

from app.users.models import User
from websocket_server.functionHandeler import functions

load_dotenv()
OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
client = OpenAI(api_key=OPENAI_API_KEY)
USER: User = asyncio.run(User(google_id='fd').getByGId())
response = client.responses.create(
    model="gpt-4.1",
    input=[{"role": "user",
            "content": "Puedes agendar una reunion con hugo, el cliente ha dicho que su email es pedroguillferri9@gmail.com y le biene vien mañana a las 12 no hace flata que compruebes la disponibilidad, solo agendala"}],
    tools=functions.to_dict()
)


async def handle_function_call(item: dict):
    # print("Handling function call:", item)
    # fn_def = next((f for f in functions if f['schema']['name'] == item['name']), None)
    fn_def = functions.get_by_name(item.name)
    if not fn_def:
        raise ValueError(f"No handler found for function: {item.name}")

    try:
        args = json.loads(item.arguments)
        # print(f'Args en handle: {args}')
    except json.JSONDecodeError:
        return json.dumps({
            "error": "Invalid JSON arguments for function call."
        })

    try:
        # print("Calling function:", fn_def['schema']['name'], args)
        # print("Calling function")
        # result = await fn_def['handler'](args, self.GOOGLE_CREDS)

        # print(f'Google Creds: {self.GOOGLE_CREDS}')
        result = await fn_def.handler(args, USER)
        return result
    except Exception as err:
        print(f"Error running function {item.name}:", err)
        return json.dumps({
            "error": f"Error running function {item.name}: {str(err)}"
        })


print(asyncio.run(handle_function_call(item=response.output[0])))
