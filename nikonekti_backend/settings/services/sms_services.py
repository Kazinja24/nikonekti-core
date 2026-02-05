import africastalking
from django.conf import settings

africastalking.initialize(
    settings.AFRICASTALKING_USERNAME,
    settings.AFRICASTALKING_API_KEY
)

sms = africastalking.SMS


def send_sms(phone, message):
    try:
        response = sms.send(message, [phone], settings.AFRICASTALKING_SENDER_ID)
        return response
    except Exception as e:
        print("SMS Error:", e)
        return None
