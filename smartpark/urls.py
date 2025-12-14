# urls.py
from django.urls import path
from .views import (
    receive_entry,
    receive_exit,
    LoginView,
    LogoutView,
    HomeView,
    get_statistics,
    get_vehicle_entries,
    mark_as_paid,
    add_car,
    block_car,
    get_unpaid_entries,
    get_receipt,
    FreePlateNumberView,
    DeleteFreePlateView,
    CarsManagementView,
    create_car,
    update_car,
    delete_car,
    upload_license,
    UnpaidEntriesView,
    export_entries_xls,
    delete_final_20_days_entries,
    DetailedEntriesView,
    get_detailed_entries,
    print_detailed_stats_receipt,
    list_printers,
    process_uuid_payment,
    get_uuid_info,
    entry_check,
    MarkErrorView,
)
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.views.generic import RedirectView

from .view_unikassa import SaleSend

urlpatterns = (
    [
        path("", RedirectView.as_view(url="home/", permanent=True)),
        path("receive-entry/", receive_entry),
        path("receive-exit/", receive_exit),
        path("accounts/login/", LoginView.as_view(), name="login"),
        path("accounts/logout/", LogoutView.as_view(), name="logout"),
        path("home/", HomeView.as_view(), name="home"),
        # Cars management
        path("cars/", CarsManagementView.as_view(), name="cars_management"),
        path("api/cars/create/", create_car, name="create_car"),
        path("api/cars/<int:car_id>/update/", update_car, name="update_car"),
        path("api/cars/<int:car_id>/delete/", delete_car, name="delete_car"),
        path("api/cars/upload-license/", upload_license, name="upload_license"),
        # New API endpoints
        path("api/statistics/", get_statistics, name="get_statistics"),
        path("api/vehicle-entries/", get_vehicle_entries, name="get_vehicle_entries"),
        path("api/mark-paid/", mark_as_paid, name="mark_as_paid"),
        path("api/add-car/", add_car, name="add_car"),
        path("api/block-car/", block_car, name="block_car"),
        path("api/unpaid-entries/", get_unpaid_entries, name="get_unpaid_entries"),
        path("api/receipt/", get_receipt, name="get_receipt"),
        path("export/xls/", export_entries_xls, name="export_entries_xls"),
        path(
            "free-plate-number/",
            FreePlateNumberView.as_view(),
            name="free_plate_number",
        ),
        path(
            "delete-free-plate/<int:pk>/",
            DeleteFreePlateView.as_view(),
            name="delete_free_plate",
        ),
        path("unpaid-entries/", UnpaidEntriesView.as_view(), name="unpaid_entries"),
        path(
            "detailed-entries/", DetailedEntriesView.as_view(), name="detailed_entries"
        ),
      
        path(
            "api/detailed-entries/", get_detailed_entries, name="get_detailed_entries"
        ),
        path(
            "api/detailed-entries/print-stats/",
            print_detailed_stats_receipt,
            name="print_detailed_stats_receipt",
        ),
        path("api/printers/", list_printers, name="list_printers"),
        path("api/uuid-info/", get_uuid_info, name="get_uuid_info"),
        path("api/uuid-payment/", process_uuid_payment, name="process_uuid_payment"),
        path(
            "delete-final-20-days-entries/",
            delete_final_20_days_entries,
            name="delete_final_20_days_entries",
        ),
        path("api/entry_check/", entry_check, name="entry_check"),
        path("mark_error/", MarkErrorView.as_view(), name="mark_error"),
        # UNIKASSA
        path("api/send/sale/", SaleSend.as_view(), name="send_sale"),
    ]
    + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    + staticfiles_urlpatterns()
)
