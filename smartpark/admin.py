from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from django.utils import timezone
from .models import CustomUser, VehicleEntry, Cars


@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    add_form = UserCreationForm
    form = UserChangeForm
    model = CustomUser
    list_display = ("username", "email", "role", "is_staff", "is_active")
    list_filter = ("is_staff", "is_active", "role")

    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (
            "Personal info",
            {"fields": ("first_name", "last_name", "email", "image", "role")},
        ),
        (
            "Permissions",
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                    "groups",
                    "user_permissions",
                )
            },
        ),
        ("Important dates", {"fields": ("last_login", "date_joined")}),
    )

    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "username",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "email",
                    "image",
                    "role",
                    "is_staff",
                    "is_active",
                ),
            },
        ),
    )

    search_fields = ("username", "email")
    ordering = ("username",)


@admin.register(VehicleEntry)
class VehicleEntryAdmin(admin.ModelAdmin):
    list_display = [
        "uuid",
        "number_plate",
        "entry_time",
        "exit_time",
        "duration_display",
        "total_amount",
        "is_paid",
        "status_display",
    ]
    list_filter = [
        ("entry_time"),
        ("exit_time"),
        "is_paid",
    ]
    search_fields = ["uuid", "number_plate", "total_amount"]
    date_hierarchy = "entry_time"
    ordering = ["-entry_time"]
    list_editable = ["is_paid"]
    actions = [
        "action_mark_as_paid",
        "action_mark_as_unpaid",
        "action_set_exit_now",
    ]

    # Show non-editable uuid on the form/detail page
    readonly_fields = ["uuid"]

    @admin.display(description="Holat", ordering="exit_time")
    def status_display(self, obj: VehicleEntry) -> str:
        return "Ichkarida" if obj.exit_time is None else "Chiqib ketgan"

    @admin.display(description="Davomiyligi")
    def duration_display(self, obj: VehicleEntry) -> str:
        if obj.exit_time and obj.entry_time:
            delta = obj.exit_time - obj.entry_time
            minutes = int(delta.total_seconds() // 60)
            if minutes < 60:
                return f"{minutes} daqiqa"
            hours = minutes // 60
            rem = minutes % 60
            return f"{hours} soat {rem} daqiqa" if rem else f"{hours} soat"
        return "-"

    @admin.action(description="Tanlanganlarni to'langan deb belgilash")
    def action_mark_as_paid(self, request, queryset):
        updated = queryset.update(is_paid=True)
        self.message_user(request, f"{updated} ta yozuv to'langan qilindi")

    @admin.action(description="Tanlanganlarni to'lanmagan deb belgilash")
    def action_mark_as_unpaid(self, request, queryset):
        updated = queryset.update(is_paid=False)
        self.message_user(request, f"{updated} ta yozuv to'lanmagan qilindi")

    @admin.action(
        description="Tanlanganlarga hozirgi vaqtni chiqish vaqti sifatida qo'yish"
    )
    def action_set_exit_now(self, request, queryset):
        now = timezone.now()
        updated = queryset.filter(exit_time__isnull=True).update(exit_time=now)
        self.message_user(request, f"{updated} ta yozuvga chiqish vaqti qo'yildi")


@admin.register(Cars)
class CarsAdmin(admin.ModelAdmin):
    list_display = [
        "number_plate",
        "position",
        "is_free",
        "is_special_taxi",
        "is_blocked",
    ]
    list_filter = ["is_free", "is_special_taxi", "is_blocked"]
    search_fields = ["number_plate", "position"]
    ordering = ["number_plate"]
    list_editable = ["is_free", "is_special_taxi", "is_blocked"]


# Admin UI titles
admin.site.site_header = "Smart AutoPark Admin"
admin.site.site_title = "Smart AutoPark"
admin.site.index_title = "Boshqaruv paneli"
