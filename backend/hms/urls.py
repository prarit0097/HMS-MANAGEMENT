from django.urls import path
from apps.core import api
from apps.core import resource_admin
urlpatterns = [path('api/v1/health/', api.health), path('api/v1/auth/csrf/', api.csrf), path('api/v1/auth/login/', api.Login.as_view()), path('api/v1/auth/logout/', api.sign_out)]
urlpatterns += [path('api/v1/auth/me/', api.me), path('api/v1/branches/', api.branches), path('api/v1/patients/', api.PatientList.as_view()), path('api/v1/patients/<uuid:pk>/', api.PatientDetail.as_view()), path('api/v1/appointments/', api.AppointmentList.as_view()), path('api/v1/appointments/<uuid:pk>/', api.AppointmentDetail.as_view()), path('api/v1/beds/', api.BedList.as_view()), path('api/v1/admissions/', api.AdmissionList.as_view()), path('api/v1/dashboard/', api.dashboard), path('api/v1/platform/summary/', api.platform_summary)]
urlpatterns += [
    path('api/v1/platform/organisations/<uuid:organisation_id>/branches/', resource_admin.ConfigurationBranches.as_view()),
    path('api/v1/platform/organisations/<uuid:organisation_id>/beds/', resource_admin.ConfigurationBeds.as_view()),
    path('api/v1/platform/organisations/<uuid:organisation_id>/beds/<uuid:pk>/', resource_admin.ConfigurationBedDetail.as_view()),
]
