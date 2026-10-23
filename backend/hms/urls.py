from django.urls import path
from apps.core import api
from apps.core import resource_admin
urlpatterns = [path('api/v1/health/', api.health), path('api/v1/auth/csrf/', api.csrf), path('api/v1/auth/login/', api.Login.as_view()), path('api/v1/auth/logout/', api.Logout.as_view())]
urlpatterns += [path('api/v1/auth/me/', api.me), path('api/v1/branches/', api.branches), path('api/v1/patients/', api.PatientList.as_view()), path('api/v1/patients/<uuid:pk>/', api.PatientDetail.as_view()), path('api/v1/appointments/', api.AppointmentList.as_view()), path('api/v1/appointments/<uuid:pk>/', api.AppointmentDetail.as_view()), path('api/v1/beds/', api.BedList.as_view()), path('api/v1/admissions/', api.AdmissionList.as_view()), path('api/v1/dashboard/', api.dashboard), path('api/v1/platform/summary/', api.platform_summary)]
urlpatterns += [
    path('api/v1/platform/organisations/<uuid:organisation_id>/branches/', resource_admin.ConfigurationBranches.as_view()),
    path('api/v1/platform/organisations/<uuid:organisation_id>/beds/', resource_admin.ConfigurationBeds.as_view()),
    path('api/v1/platform/organisations/<uuid:organisation_id>/beds/<uuid:pk>/', resource_admin.ConfigurationBedDetail.as_view()),
]

from apps.core import staff_access
urlpatterns += [
    path('api/v1/platform/organisations/<str:organisation_id>/staff/', staff_access.StaffList.as_view()),
    path('api/v1/platform/organisations/<str:organisation_id>/staff/branches/', staff_access.StaffBranches.as_view()),
    path('api/v1/platform/organisations/<str:organisation_id>/staff/<int:pk>/', staff_access.StaffDetail.as_view()),
]

from apps.core.identity_security import SecurityView, VerifyMfa
urlpatterns += [path('api/v1/auth/mfa/verify/', VerifyMfa.as_view())]
for route, action in [('', 'status'), ('enrollment/', 'enrollment'), ('enrollment/<uuid:enrollment_id>/confirm/', 'confirm'), ('backup-codes/rotate/', 'rotate'), ('disable/', 'disable'), ('sessions/revoke/', 'revoke'), ('step-up/', 'step-up'), ('password/', 'password')]:
    urlpatterns.append(path('api/v1/auth/security/' + route, SecurityView.as_view(action=action)))
