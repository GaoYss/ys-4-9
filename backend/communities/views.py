from decimal import Decimal, InvalidOperation

from django.db.models import Count
from django.shortcuts import get_object_or_404
from rest_framework import status, viewsets
from rest_framework.decorators import action, api_view
from rest_framework.response import Response

from .models import Bill, Building, FeeType, Payment, PrepaidAccount, PrepaidTransaction, Reminder, Room
from .serializers import (
    BillSerializer,
    BuildingDetailSerializer,
    BuildingSerializer,
    FeeTypeSerializer,
    PaymentSerializer,
    PrepaidAccountSerializer,
    PrepaidTransactionSerializer,
    ReminderSerializer,
    RoomSerializer,
)
from .services import create_overdue_reminders, dashboard_stats, generate_bills, pay_bill, recharge_prepaid


class BuildingViewSet(viewsets.ModelViewSet):
    queryset = Building.objects.annotate(room_count=Count("rooms")).all()
    serializer_class = BuildingSerializer

    def get_serializer_class(self):
        if self.action == "retrieve":
            return BuildingDetailSerializer
        return BuildingSerializer


class RoomViewSet(viewsets.ModelViewSet):
    queryset = Room.objects.select_related("building").all()
    serializer_class = RoomSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        building = self.request.query_params.get("building")
        if building:
            queryset = queryset.filter(building_id=building)
        return queryset


class FeeTypeViewSet(viewsets.ModelViewSet):
    queryset = FeeType.objects.all()
    serializer_class = FeeTypeSerializer


class BillViewSet(viewsets.ModelViewSet):
    queryset = Bill.objects.select_related("room", "room__building", "fee_type").all()
    serializer_class = BillSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        status_filter = self.request.query_params.get("status")
        period = self.request.query_params.get("period")
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if period:
            queryset = queryset.filter(period=period)
        return queryset

    @action(detail=False, methods=["post"])
    def generate(self, request):
        fee_type_id = request.data.get("fee_type")
        period = request.data.get("period")
        due_date = request.data.get("due_date")
        room_ids = request.data.get("room_ids")
        if not all([fee_type_id, period, due_date]):
            return Response({"detail": "fee_type、period、due_date 为必填项"}, status=status.HTTP_400_BAD_REQUEST)

        created, skipped = generate_bills(fee_type_id, period, due_date, room_ids)
        return Response(
            {
                "created": BillSerializer(created, many=True).data,
                "created_count": len(created),
                "skipped_count": skipped,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["post"])
    def pay(self, request, pk=None):
        bill = self.get_object()
        try:
            payment, prepaid_deduct = pay_bill(
                bill,
                request.data.get("method", Payment.WECHAT),
                request.data.get("payer", ""),
                request.data.get("use_prepaid", True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        data = PaymentSerializer(payment).data
        data["prepaid_deduct"] = str(prepaid_deduct)
        return Response(data, status=status.HTTP_201_CREATED)


class PaymentViewSet(viewsets.ModelViewSet):
    queryset = Payment.objects.select_related("bill", "bill__room", "bill__room__building", "bill__fee_type").all()
    serializer_class = PaymentSerializer

    def create(self, request, *args, **kwargs):
        bill = get_object_or_404(Bill.objects.select_related("room"), pk=request.data.get("bill"))
        try:
            payment, prepaid_deduct = pay_bill(
                bill,
                request.data.get("method", Payment.WECHAT),
                request.data.get("payer", ""),
                request.data.get("use_prepaid", True),
            )
        except ValueError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        data = self.get_serializer(payment).data
        data["prepaid_deduct"] = str(prepaid_deduct)
        return Response(data, status=status.HTTP_201_CREATED)


class ReminderViewSet(viewsets.ModelViewSet):
    queryset = Reminder.objects.select_related("bill", "bill__room", "bill__room__building", "bill__fee_type").all()
    serializer_class = ReminderSerializer

    @action(detail=False, methods=["post"])
    def create_overdue(self, request):
        reminders = create_overdue_reminders(request.data.get("channel", Reminder.SMS))
        return Response(
            {"created_count": len(reminders), "created": ReminderSerializer(reminders, many=True).data},
            status=status.HTTP_201_CREATED,
        )


class PrepaidAccountViewSet(viewsets.ModelViewSet):
    queryset = PrepaidAccount.objects.select_related("room", "room__building").all()
    serializer_class = PrepaidAccountSerializer

    @action(detail=True, methods=["post"])
    def recharge(self, request, pk=None):
        account = self.get_object()
        amount = request.data.get("amount")
        remark = request.data.get("remark", "")
        if amount is None:
            return Response({"detail": "amount 为必填项"}, status=status.HTTP_400_BAD_REQUEST)
        try:
            amount = Decimal(str(amount))
            account, txn = recharge_prepaid(account.room_id, amount, remark)
        except (ValueError, InvalidOperation) as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        return Response(
            {
                "account": PrepaidAccountSerializer(account).data,
                "transaction": PrepaidTransactionSerializer(txn).data,
            },
            status=status.HTTP_201_CREATED,
        )

    @action(detail=True, methods=["get"])
    def transactions(self, request, pk=None):
        account = self.get_object()
        txns = account.transactions.select_related("bill").all()
        return Response(PrepaidTransactionSerializer(txns, many=True).data)


class PrepaidTransactionViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = PrepaidTransaction.objects.select_related("account", "account__room", "account__room__building", "bill").all()
    serializer_class = PrepaidTransactionSerializer


@api_view(["GET"])
def dashboard(request):
    stats = dashboard_stats()
    recent = BillSerializer(stats.pop("recent_bills"), many=True).data
    return Response({**stats, "recent_bills": recent})
