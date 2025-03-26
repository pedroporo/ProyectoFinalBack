import os
import phonenumbers
import time
import uuid
from twilio.rest import Client
from dotenv import load_dotenv
load_dotenv()

# environment variables
TWILIO_NUMBER = os.environ.get("TWILIO_NUMBER")

# constants
TWIMLET = "https://twimlets.com/echo?Twiml=%3CResponse%3E%0A%20%20%3CDial%3E%3CConference%3E{{name}}%3C%2FConference%3E%3C%2FDial%3E%0A%3C%2FResponse%3E&"

# instantiate Slack & Twilio clients
twilio_client = Client()


def call_command(phone_numbers_list_as_string):
    """
        Validates a string of phone numbers, delimited by spaces, then
        dials everyone into a single call if they are all valid.
    """
    # generate random ID for this conference call
    conference_name = str(uuid.uuid4())
    # split phone numbers by spaces
    phone_numbers = phone_numbers_list_as_string.split(" ")
    # make sure at least 2 phone numbers are specified
    if len(phone_numbers) > 1:
        # check that phone numbers are in a valid format
        are_numbers_valid, response = validate_phone_numbers(phone_numbers)
        if are_numbers_valid:
            # all phone numbers are valid, so let's dial them together
            for phone_number in phone_numbers:
                twilio_client.calls.create(to=phone_number,
                                           from_=TWILIO_NUMBER,
                                           url=TWIMLET.replace('{{name}}',
                                           conference_name))
            response = "calling: " + phone_numbers_list_as_string
    else:
        response = "the *call* command requires at least 2 phone numbers"
    return response


def validate_phone_numbers(phone_numbers):
    """
        Uses the python-phonenumbers library to make sure each phone number
        is in a valid format.
    """
    invalid_response = " is not a valid phone number format. Please " + \
                       "correct the number and retry. No calls have yet " + \
                       "been dialed."
    for phone_number in phone_numbers:
        try:
            validate_phone_number = phonenumbers.parse(phone_number)
            if not phonenumbers.is_valid_number(validate_phone_number):
                return False, phone_number + invalid_response
        except:
            return False, phone_number + invalid_response
    return True, None




if __name__ == "__main__":
    READ_WEBSOCKET_DELAY = 1 # 1 second delay between reading from firehose
    while True:
        print("CallBot connected and running!")
        time.sleep(READ_WEBSOCKET_DELAY)


