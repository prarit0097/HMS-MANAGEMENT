from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import NotFound, PermissionDenied
from .models import Patient, Appointment, Admission, Bed, Branch
from .authorization import branch_ids

class ConcealedRelatedField(serializers.PrimaryKeyRelatedField):
    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except serializers.ValidationError:
            raise NotFound('Record not found.')

class ScopedBranchField(ConcealedRelatedField):
    def to_internal_value(self, data):
        try:
            return super().to_internal_value(data)
        except NotFound:
            raise PermissionDenied('You do not have access to this branch.')

class StrictSerializer(serializers.ModelSerializer):
    capability = None
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get('request')
        if request is not None and self.capability:
            ids = branch_ids(request.user, self.capability)
            for field, model in [('patient', Patient), ('bed', Bed)]:
                if field in self.fields and not self.fields[field].read_only:
                    self.fields[field] = ConcealedRelatedField(queryset=model.objects.filter(branch_id__in=ids))
            if 'branch' in self.fields and not self.fields['branch'].read_only:
                self.fields['branch'] = ScopedBranchField(queryset=Branch.objects.filter(id__in=ids))
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        read_only = {key for key in data if key in self.fields and self.fields[key].read_only}
        if unknown or read_only:
            raise serializers.ValidationError({key: 'This field cannot be changed.' for key in unknown | read_only})
        return super().to_internal_value(data)

class PatientSerializer(StrictSerializer):
    capability = 'patients.write'
    def to_internal_value(self, data):
        if self.instance is not None and 'branch' in data:
            raise serializers.ValidationError({'branch': 'The registration branch cannot be changed.'})
        return super().to_internal_value(data)
    class Meta:
        model = Patient
        fields = ['id', 'uhid', 'full_name', 'phone', 'date_of_birth', 'age', 'gender', 'city', 'created_at', 'branch']
        read_only_fields = ['id', 'uhid', 'created_at']
    def validate(self, attrs):
        if attrs.get('date_of_birth') and attrs['date_of_birth'] > timezone.localdate():
            raise serializers.ValidationError({'date_of_birth': 'Date of birth cannot be in the future.'})
        if attrs.get('age') is not None and attrs['age'] > 130:
            raise serializers.ValidationError({'age': 'Enter an age from 0 to 130.'})
        return attrs

class AppointmentSerializer(StrictSerializer):
    capability = 'appointments.write'
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    class Meta:
        model = Appointment
        fields = ['id', 'patient', 'patient_name', 'branch', 'doctor_name', 'scheduled_at', 'reason', 'status', 'version']
        read_only_fields = ['id', 'version', 'status']

class AppointmentChange(serializers.Serializer):
    expected_version = serializers.IntegerField(min_value=1)
    scheduled_at = serializers.DateTimeField(required=False)
    doctor_name = serializers.CharField(max_length=160, required=False)
    reason = serializers.CharField(max_length=500, required=False, allow_blank=True)
    status = serializers.ChoiceField(choices=Appointment.STATUSES, required=False)
    def to_internal_value(self, data):
        unknown = set(data) - set(self.fields)
        if unknown:
            raise serializers.ValidationError({key: 'This field cannot be changed.' for key in unknown})
        return super().to_internal_value(data)

class AdmissionSerializer(StrictSerializer):
    capability = 'admissions.write'
    patient_name = serializers.CharField(source='patient.full_name', read_only=True)
    bed_number = serializers.CharField(source='bed.number', read_only=True)
    class Meta:
        model = Admission
        fields = ['id', 'patient', 'patient_name', 'bed', 'bed_number', 'branch', 'treating_doctor', 'reason', 'status', 'version', 'admitted_at']
        read_only_fields = ['id', 'branch', 'status', 'version', 'admitted_at']

class BedSerializer(serializers.ModelSerializer):
    patient_name = serializers.SerializerMethodField()
    admission_id = serializers.SerializerMethodField()
    class Meta:
        model = Bed
        fields = ['id', 'number', 'room_number', 'category', 'status', 'patient_name', 'admission_id', 'branch']
    def get_patient_name(self, obj):
        active = [a for a in obj.admissions.all() if a.status == 'active']
        return active[0].patient.full_name if active else None
    def get_admission_id(self, obj):
        active = [a for a in obj.admissions.all() if a.status == 'active']
        return str(active[0].id) if active else None
