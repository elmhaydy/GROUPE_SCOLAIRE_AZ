from django.db import transaction
from django.db.models import Max
from core.models import TransactionFinance


def assign_receipt_seq_for_batch(batch_token: str) -> int:
    with transaction.atomic():
        last = TransactionFinance.objects.aggregate(m=Max("receipt_seq"))["m"] or 0
        seq = last + 1
        TransactionFinance.objects.filter(batch_token=batch_token, receipt_seq__isnull=True)\
            .update(receipt_seq=seq)
        return seq
