from django.urls import include, path
from rest_framework.routers import DefaultRouter

from .views import BillViewSet, BuildingViewSet, FeeTypeViewSet, PaymentViewSet, PrepaidAccountViewSet, PrepaidTransactionViewSet, ReminderViewSet, RoomViewSet, dashboard

router = DefaultRouter()
router.register("buildings", BuildingViewSet)
router.register("rooms", RoomViewSet)
router.register("fee-types", FeeTypeViewSet)
router.register("bills", BillViewSet)
router.register("payments", PaymentViewSet)
router.register("reminders", ReminderViewSet)
router.register("prepaid-accounts", PrepaidAccountViewSet)
router.register("prepaid-transactions", PrepaidTransactionViewSet)

urlpatterns = [
    path("dashboard/", dashboard, name="dashboard"),
    path("", include(router.urls)),
]
