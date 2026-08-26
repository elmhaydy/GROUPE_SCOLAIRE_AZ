from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from core.services.sms_dispatcher import update_status_from_webhook


@csrf_exempt
def sms_webhook(request):
    """
    Webhook réception provider (bulkSMS / Twilio).
    Attend params standards:
    - message_id / sms_id
    - status (delivered, failed, sent, undelivered)
    - error (optionnel)
    """
    msg_id = request.POST.get("message_id") or request.POST.get("sms_id") or ""
    status = request.POST.get("status") or ""
    error = request.POST.get("error") or request.POST.get("error_message") or ""

    update_status_from_webhook(msg_id, status, error)
    # provider peut exiger "200 OK" simple
    return HttpResponse("OK")
