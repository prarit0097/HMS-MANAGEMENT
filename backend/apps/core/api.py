from django.contrib.auth import authenticate, login, logout
from django.middleware.csrf import get_token
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.pagination import LimitOffsetPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView, exception_handler
from rest_framework import generics
from rest_framework.exceptions import ValidationError
from rest_framework.throttling import SimpleRateThrottle
from django.db.models import Q, Prefetch
from django.utils import timezone
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import Branch, Membership, Patient, Appointment, Encounter, Bed, Admission
from .authorization import current_user, permitted_branches
from .serializers import PatientSerializer, AppointmentSerializer, AppointmentChange, BedSerializer, AdmissionSerializer
from . import services

def safe_exception_handler(exc, context):
    response = exception_handler(exc, context)
    if response is not None:
        fields = response.data if isinstance(response.data, dict) and 'detail' not in response.data else None
        code = getattr(exc, 'default_code', 'request_failed')
        response.data = {'code': code, 'message': 'Please check the supplied fields.' if response.status_code == 400 else str(getattr(exc, 'detail', 'Request denied.'))}
        if fields:
            response.data['field_errors'] = fields
    return response

@api_view(['GET'])
@permission_classes([AllowAny])
def health(request):
    return Response({'status': 'ok'})

@api_view(['GET'])
@permission_classes([AllowAny])
def csrf(request):
    get_token(request)
    return Response({'detail': 'CSRF cookie set'})

@method_decorator(csrf_protect, name='dispatch')
class Login(APIView):
    permission_classes = [AllowAny]
    class LoginThrottle(SimpleRateThrottle):
        scope = 'login'
        rate = '10/min'
        def get_cache_key(self, request, view):
            return self.cache_format % {'scope': self.scope, 'ident': getattr(request, 'verified_client_ip', request.META.get('REMOTE_ADDR', 'unknown'))}
    throttle_classes = [LoginThrottle]
    def post(self, request):
        if not isinstance(request.data.get('username'), str) or not isinstance(request.data.get('password'), str) or len(request.data.get('username', '')) > 150 or len(request.data.get('password', '')) > 1024:
            return Response({'code': 'invalid_credentials', 'message': 'Unable to sign in with these details.'}, status=401)
        user = authenticate(request, username=request.data.get('username', ''), password=request.data.get('password', ''))
        if user is None:
            return Response({'code': 'invalid_credentials', 'message': 'Unable to sign in with these details.'}, status=401)
        login(request, user)
        return Response(current_user(user))

@api_view(['POST'])
def sign_out(request):
    logout(request)
    return Response(status=204)

@api_view(['GET'])
def me(request):
    return Response(current_user(request.user))

@api_view(['GET'])
def branches(request):
    ids = Membership.objects.filter(user=request.user).values_list('branch_id', flat=True)
    results = list(Branch.objects.filter(id__in=ids).values('id', 'name', 'code'))
    return Response({'results': results, 'count': len(results)})

def search_query(request):
    query = request.query_params.get('q', '').strip()
    if len(query) > 200:
        raise ValidationError({'q': 'Search must be 200 characters or fewer.'})
    return query

class PatientList(generics.ListCreateAPIView):
    serializer_class = PatientSerializer
    def get_queryset(self):
        action = 'patients.write' if self.request.method == 'POST' else 'patients.read'
        branches = permitted_branches(self.request.user, action, self.request.query_params.get('branch'))
        query = search_query(self.request)
        return Patient.objects.filter(branch_id__in=branches).filter(Q(full_name__icontains=query) | Q(phone__icontains=query) | Q(uhid__icontains=query))
    def perform_create(self, serializer):
        self.get_queryset()
        serializer.instance = services.register_patient(self.request.user, serializer.validated_data)

class PatientDetail(generics.RetrieveUpdateAPIView):
    serializer_class = PatientSerializer
    http_method_names = ['get', 'patch', 'head', 'options']
    def get_queryset(self):
        return Patient.objects.filter(branch_id__in=permitted_branches(self.request.user, 'patients.write' if self.request.method == 'PATCH' else 'patients.read'))
    def perform_update(self, serializer):
        if 'branch' in serializer.validated_data:
            raise ValidationError({'branch': 'The registration branch cannot be changed.'})
        from django.db import transaction
        with transaction.atomic():
            result = serializer.save()
            services.audit(self.request.user, 'patient.changed', result)

class AppointmentList(generics.ListCreateAPIView):
    serializer_class = AppointmentSerializer
    def get_queryset(self):
        branches = permitted_branches(self.request.user, 'appointments.write' if self.request.method == 'POST' else 'appointments.read', self.request.query_params.get('branch'))
        queryset = Appointment.objects.filter(branch_id__in=branches).select_related('patient')
        date = self.request.query_params.get('date')
        if date:
            from datetime import date as Date
            try:
                date = Date.fromisoformat(date)
            except ValueError:
                raise ValidationError({'date': 'Enter a date in YYYY-MM-DD format.'})
            queryset = queryset.filter(scheduled_at__date=date)
        query = search_query(self.request)
        return queryset.filter(Q(patient__full_name__icontains=query) | Q(doctor_name__icontains=query))
    def perform_create(self, serializer):
        self.get_queryset()
        serializer.instance = services.create_appointment(self.request.user, serializer.validated_data)

class AppointmentDetail(APIView):
    def patch(self, request, pk):
        change = AppointmentChange(data=request.data)
        change.is_valid(raise_exception=True)
        return Response(AppointmentSerializer(services.change_appointment(request.user, pk, change.validated_data)).data)

class BedList(generics.ListAPIView):
    serializer_class = BedSerializer
    def get_queryset(self):
        branches = permitted_branches(self.request.user, 'beds.read', self.request.query_params.get('branch'))
        return Bed.objects.filter(branch_id__in=branches).prefetch_related(Prefetch('admissions', queryset=Admission.objects.filter(status='active').select_related('patient')))

class AdmissionList(generics.ListCreateAPIView):
    serializer_class = AdmissionSerializer
    def get_queryset(self):
        branches = permitted_branches(self.request.user, 'admissions.write' if self.request.method == 'POST' else 'admissions.read', self.request.query_params.get('branch'))
        return Admission.objects.filter(branch_id__in=branches).select_related('patient', 'bed')
    def perform_create(self, serializer):
        self.get_queryset()
        serializer.instance = services.allocate_bed(self.request.user, serializer.validated_data)

@api_view(['GET'])
def dashboard(request):
    branches = permitted_branches(request.user, 'dashboard.read', request.query_params.get('branch'))
    today = timezone.localdate()
    return Response({'patients_total': Patient.objects.filter(branch_id__in=branches).count(), 'opd_today': Encounter.objects.filter(appointment__branch_id__in=branches, checked_in_at__date=today).count(), 'active_admissions': Admission.objects.filter(branch_id__in=branches, status='active').count(), 'available_beds': Bed.objects.filter(branch_id__in=branches, status='available').count(), 'appointments_today': Appointment.objects.filter(branch_id__in=branches, scheduled_at__date=today).count(), 'therapy_pending': None})

@api_view(['GET'])
def platform_summary(request):
    branches = permitted_branches(request.user, 'platform.read')
    organisation = Branch.objects.filter(id__in=branches).select_related('organisation').first().organisation
    scoped = Branch.objects.filter(organisation=organisation)
    staff = get_user_model().objects.filter(memberships__branch__in=scoped).distinct()
    return Response({'organisation': {'id': str(organisation.id), 'name': organisation.name}, 'branches_count': scoped.count(), 'staff_count': staff.count(), 'active_staff_count': staff.filter(is_active=True).count(), 'security': {'ip_mode': 'allowlist_only' if settings.HMS_IP_ALLOWLIST_ONLY else 'allow_authenticated'}, 'modules': [{'name': name, 'status': state} for name, state in [('Reception', 'foundation'), ('Admissions', 'foundation'), ('Clinical signing', 'planned'), ('Pharmacy', 'planned'), ('Accounts', 'planned'), ('MCP', 'planned'), ('Backups', 'planned')]]})
