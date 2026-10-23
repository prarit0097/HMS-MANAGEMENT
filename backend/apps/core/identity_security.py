"""Self-only identity services. Lock User -> identity -> challenge/enrollment/code -> audit.

Failure outcomes are returned from atomic blocks, so attempt accounting commits.
Secrets never enter audit or durable session state.
"""
import hashlib
import json
import re
import secrets
import uuid
from datetime import timedelta, datetime, timezone as dt_timezone
import pyotp
from cryptography.fernet import Fernet, MultiFernet, InvalidToken
from django.conf import settings
from django.contrib.auth import get_user_model, login, logout, update_session_auth_hash
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from django.views.decorators.debug import sensitive_variables, sensitive_post_parameters
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from rest_framework.exceptions import APIException, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import IdentitySecurity, IdentityEnrollment, IdentityChallenge, IdentityBackupCode, IdentityNetworkBudget, AuditEvent
from .authorization import current_user


class SecurityError(APIException):
    def __init__(self, code, message, status=401):
        self.status_code = status
        self.default_code = code
        super().__init__(message, code)


def denied(code='mfa_invalid', status=401, retry=None):
    messages = {'mfa_invalid':'Unable to verify these details. Try a fresh code.', 'challenge_expired':'Sign in again to request a new verification.', 'rate_limited':'Too many attempts. Wait and try again.', 'security_state_conflict':'Security settings changed. Reload and try again.'}
    response = Response({'code':code, 'message':messages.get(code,'Unable to verify these details.')}, status=status)
    if retry:
        response['Retry-After'] = str(max(1,min(300,int(retry))))
    return response


def keyring():
    try:
        values = settings.HMS_MFA_ENCRYPTION_KEYS.split(',')
        if not values or any(not value.strip() for value in values):
            raise ValueError()
        return MultiFernet([Fernet(value.strip().encode()) for value in values])
    except (ValueError, TypeError, AttributeError):
        raise SecurityError('security_unavailable','Account security is temporarily unavailable. Contact your administrator.',503)


@sensitive_variables()
def encrypt(secret, user_id, binding, purpose):
    return keyring().encrypt(json.dumps({'v':1,'purpose':purpose,'user':user_id,'binding':str(binding),'secret':secret}).encode()).decode()


@sensitive_variables()
def decrypt(ciphertext, user_id, binding, purpose):
    try:
        value=json.loads(keyring().decrypt(ciphertext.encode()))
        if (value['v'], value['purpose'], value['user'],value['binding']) != (1,purpose,user_id,str(binding)):
            raise ValueError()
        return value['secret']
    except (InvalidToken,ValueError,KeyError,TypeError):
        raise SecurityError('security_unavailable','Account security is temporarily unavailable. Contact your administrator.',503)


def lock_identity(user):
    fresh=get_user_model().objects.select_for_update(no_key=True).get(pk=user.pk)
    state,_=IdentitySecurity.objects.get_or_create(user=fresh)
    state=IdentitySecurity.objects.select_for_update().get(user=fresh)
    return fresh,state


def epoch_valid(user, state=None):
    epoch=state.auth_epoch if state else (IdentitySecurity.objects.filter(user_id=user.pk).values_list('auth_epoch',flat=True).first() or 0)
    captured=getattr(user,'_hms_auth_epoch',None)
    return captured == epoch or (captured is None and epoch == 0)


def require_session(user,state=None):
    if not user.is_authenticated or not user.is_active or not epoch_valid(user,state):
        raise SecurityError('not_authenticated','Your session ended. Sign in again.')


def require_platform(user, state=None):
    require_session(user,state)
    if not settings.HMS_REQUIRE_ADMIN_MFA:
        return
    state=state or IdentitySecurity.objects.filter(user_id=user.pk).first()
    if not state or not state.active_ciphertext:
        raise SecurityError('mfa_enrollment_required','Set up an authenticator in Account security before continuing.',403)
    verified=getattr(user,'_hms_factor_verified_at',None)
    if not isinstance(verified,(int,float)) or not 0 <= timezone.now().timestamp()-verified <= 900:
        raise SecurityError('mfa_step_up_required','Verify your identity in Account security before continuing.',403)


def lock_platform(user):
    fresh,state=lock_identity(user)
    if not fresh.is_active:
        raise SecurityError('not_authenticated','Your session ended. Sign in again.')
    require_platform(user,state)
    return state


def stamp(request, epoch, verified=None):
    request.session.cycle_key()
    request.session['auth_epoch']=epoch
    if verified is not None:
        request.session['factor_verified_at']=verified
    request.user._hms_auth_epoch=epoch
    request.user._hms_factor_verified_at=request.session.get('factor_verified_at')


def session_hash(request):
    if not request.session.session_key:
        request.session.create()
    return hashlib.sha256(request.session.session_key.encode()).hexdigest()


def network_budget(request):
    # Middleware has already enforced and normalised the trusted proxy policy.
    ip=getattr(request,'verified_client_ip',None)
    if ip is None:
        raise SecurityError('network_denied','Access is not available from this network.',403)
    hashed=hashlib.sha256(ip.encode()).hexdigest()
    now=timezone.now()
    with transaction.atomic():
        row,_=IdentityNetworkBudget.objects.get_or_create(ip_hash=hashed,defaults={'started_at':now})
        row=IdentityNetworkBudget.objects.select_for_update().get(pk=hashed)
        elapsed=(now-row.started_at).total_seconds()
        if elapsed >= 60:
            row.started_at=now;row.attempts=0
        if row.attempts>=10:
            return denied('rate_limited',429,60-elapsed)
        row.attempts+=1;row.save()
    return None


def limit(state,challenge=None):
    now=timezone.now()
    if state.failure_started and now-state.failure_started>=timedelta(minutes=5):
        state.failure_started=None;state.failure_count=0
    if state.failure_count>=5:
        return denied('rate_limited',429,300-(now-state.failure_started).total_seconds())
    if challenge and challenge.attempts>=5:
        return denied('rate_limited',429,300)
    return None


def failed(state,challenge=None):
    if not state.failure_started:
        state.failure_started=timezone.now()
    state.failure_count+=1;state.save()
    if challenge:
        challenge.attempts+=1;challenge.save(update_fields=['attempts'])
    return denied()


@sensitive_variables()
def factor(state, method, code):
    # Decrypt even for recovery proof: unavailable encryption cannot be bypassed.
    secret=decrypt(state.active_ciphertext,state.user_id,state.device_id,'active')
    if method=='totp' and isinstance(code,str) and re.fullmatch(r'[0-9]{6}',code):
        current=int(timezone.now().timestamp())//30
        matches=[step for step in range(current-1,current+2) if secrets.compare_digest(pyotp.TOTP(secret).at(step*30),code)]
        if matches and max(matches)>state.last_totp_step:
            state.last_totp_step=max(matches);return True
    elif method=='backup_code' and isinstance(code,str):
        normal=code.strip().lower()
        if re.fullmatch(r'[a-f0-9]{8}-[a-f0-9]{32}',normal):
            row=IdentityBackupCode.objects.select_for_update().filter(user_id=state.user_id,prefix=normal[:8]).first()
            if row and check_password(normal,row.password_hash):
                row.delete();return True
    return False


@sensitive_variables()
def proof(user,state,data,required=False):
    if not user.check_password(data.get('current_password','')):
        return False
    if state.active_ciphertext:
        return factor(state,data.get('method'),data.get('code'))
    return not required


def audit(user,action,method=None):
    AuditEvent.objects.create(actor=user,action='security.'+action,object_id=str(user.pk),details={'method':method} if method else {})


def status_data(request,state=None):
    state=state or IdentitySecurity.objects.filter(user_id=request.user.pk).first()
    verified=request.session.get('factor_verified_at')
    return {'enabled':bool(state and state.active_ciphertext),'backup_codes_remaining':IdentityBackupCode.objects.filter(user_id=request.user.pk).count(),'version':state.version if state else 0,'session_factor_verified_at':datetime.fromtimestamp(verified,dt_timezone.utc).isoformat() if verified else None,'privileged_mfa_required':settings.HMS_REQUIRE_ADMIN_MFA}


@sensitive_variables()
def replace_codes(user):
    IdentityBackupCode.objects.filter(user=user).delete()
    codes=[secrets.token_hex(4)+'-'+secrets.token_hex(16) for _ in range(10)]
    IdentityBackupCode.objects.bulk_create([IdentityBackupCode(user=user,prefix=code[:8],password_hash=make_password(code)) for code in codes])
    return codes


def bump(state):
    state.auth_epoch+=1;state.version+=1;state.latest_challenge=None
    state.save()
    IdentityChallenge.objects.filter(user_id=state.user_id,consumed=False).update(consumed=True)
    IdentityEnrollment.objects.filter(user_id=state.user_id,consumed=False).update(consumed=True)


def strict(data,fields,required):
    if not isinstance(data,dict):
        raise ValidationError({'non_field_errors':'Send a JSON object with named fields.'})
    unknown=set(data)-set(fields)
    if unknown:
        raise ValidationError({field:'This field cannot be changed.' for field in unknown})
    missing=set(required)-set(data)
    if missing:
        raise ValidationError({field:'This field is required.' for field in missing})
    for field,value in data.items():
        maximum=1024 if field in {'current_password','password'} else 150 if field=='username' else 128 if field=='new_password' else 80
        if not isinstance(value,str) or len(value)>maximum:
            raise ValidationError({field:'Enter a valid text value.'})
    if 'method' in data and data['method'] not in {'totp','backup_code'}:
        raise ValidationError({'method':'Choose authenticator or recovery code.'})
    if 'scope' in data and data['scope'] not in {'others','all'}:
        raise ValidationError({'scope':'Choose other sessions or all sessions.'})


@method_decorator(sensitive_post_parameters(), name='dispatch')
class SecurityView(APIView):
    action='status'
    @sensitive_variables()
    def get(self,request):
        if self.action!='status':
            return Response(status=405)
        return Response(status_data(request))

    @sensitive_variables()
    def post(self,request,enrollment_id=None):
        action=self.action
        if action=='status':
            return Response(status=405)
        fields={'current_password','method','code'}
        required={'current_password'}
        if action=='confirm':fields={'code'};required={'code'}
        if action=='revoke':fields|={'scope'};required|={'scope'}
        if action=='password':fields|={'new_password'};required|={'new_password'}
        if action in {'rotate','disable','step-up'}:required|={'method','code'}
        strict(request.data,fields,required)
        budget=network_budget(request)
        if budget is not None:return budget
        with transaction.atomic():
            user,state=lock_identity(request.user)
            if not user.is_active:
                raise SecurityError('not_authenticated','Your session ended. Sign in again.')
            require_session(request.user,state)
            blocked=limit(state)
            if blocked is not None:return blocked
            if action=='confirm':
                pending=IdentityEnrollment.objects.select_for_update().filter(pk=enrollment_id,user=user).first()
                if not pending or pending.consumed or pending.auth_epoch!=state.auth_epoch or pending.expires_at<=timezone.now() or pending.session_hash!=session_hash(request):
                    return denied('security_state_conflict',409)
                secret=decrypt(pending.ciphertext,user.pk,pending.pk,'enrollment')
                code=request.data['code']; now=int(timezone.now().timestamp())//30
                matches=[step for step in range(now-1,now+2) if re.fullmatch(r'[0-9]{6}',code) and secrets.compare_digest(pyotp.TOTP(secret).at(step*30),code)]
                if not matches:return failed(state)
                state.device_id=pending.pk;state.active_ciphertext=encrypt(secret,user.pk,pending.pk,'active');state.last_totp_step=max(matches)
                state.failure_count=0;state.failure_started=None
                bump(state);codes=replace_codes(user);audit(user,'enrolled')
                stamp(request,state.auth_epoch,timezone.now().timestamp())
                return Response({'security':status_data(request,state),'backup_codes':codes})
            if state.active_ciphertext:
                decrypt(state.active_ciphertext,user.pk,state.device_id,'active')
            if not proof(user,state,request.data,required=action in {'rotate','disable','step-up'}):
                return failed(state)
            state.failure_count=0;state.failure_started=None;state.save()
            verified=timezone.now().timestamp()
            if action=='enrollment':
                secret=pyotp.random_base32(length=32); binding=uuid.uuid4()
                cipher=encrypt(secret,user.pk,binding,'enrollment')
                IdentityEnrollment.objects.filter(user=user,session_hash=session_hash(request),consumed=False).update(consumed=True)
                pending=IdentityEnrollment.objects.create(id=binding,user=user,session_hash=session_hash(request),ciphertext=cipher,auth_epoch=state.auth_epoch,expires_at=timezone.now()+timedelta(minutes=10))
                audit(user,'enrollment_started')
                return Response({'enrollment_id':str(binding),'secret':secret,'otpauth_uri':pyotp.TOTP(secret).provisioning_uri(user.username,issuer_name='HMS'),'expires_at':pending.expires_at.isoformat()},status=201)
            if action=='step-up':
                stamp(request,state.auth_epoch,verified);audit(user,'step_up',request.data['method'])
                return Response({'verified_at':timezone.now().isoformat(),'expires_at':(timezone.now()+timedelta(minutes=15)).isoformat()})
            if action=='password':
                password=request.data['new_password']
                if not 12<=len(password)<=128:raise ValidationError({'new_password':'Use 12 to 128 characters.'})
                try:validate_password(password,user=user)
                except DjangoValidationError as exc:raise ValidationError({'new_password':exc.messages})
                user.set_password(password);user.save(update_fields=['password'])
                update_session_auth_hash(request,user)
            if action=='disable':
                state.active_ciphertext='';state.device_id=None;state.last_totp_step=-1
                IdentityBackupCode.objects.filter(user=user).delete()
                request.session.pop('factor_verified_at',None)
            bump(state);audit(user,action,request.data.get('method'))
            stamp(request,state.auth_epoch,verified if state.active_ciphertext else None)
            if action=='rotate':return Response({'security':status_data(request,state),'backup_codes':replace_codes(user)})
            if action=='disable':return Response(status_data(request,state))
            if action=='revoke' and request.data['scope']=='all':logout(request)
            return Response(status=204)


@sensitive_variables()
def begin_login(request,user):
    # A valid password replaces any former full or partial session.
    logout(request)
    request.session.create()
    with transaction.atomic():
        user,state=lock_identity(user)
        if not user.is_active or not user.check_password(request.data.get('password','')):
            return denied('invalid_credentials')
        if state.active_ciphertext:
            decrypt(state.active_ciphertext,user.pk,state.device_id,'active')
            challenge=IdentityChallenge.objects.create(user=user,session_hash=session_hash(request),auth_epoch=state.auth_epoch,expires_at=timezone.now()+timedelta(minutes=5))
            state.latest_challenge=challenge.pk;state.save(update_fields=['latest_challenge'])
            request.session['mfa_challenge']=str(challenge.pk)
            return Response({'code':'mfa_required','methods':['totp','backup_code'],'expires_at':challenge.expires_at.isoformat()},status=202)
        login(request,user);stamp(request,state.auth_epoch)
        return Response(current_user(user))


@method_decorator(csrf_protect,name='dispatch')
@method_decorator(sensitive_post_parameters(),name='dispatch')
class VerifyMfa(APIView):
    permission_classes=[AllowAny]
    authentication_classes=[]
    @sensitive_variables()
    def post(self,request):
        strict(request.data,{'method','code'},{'method','code'})
        challenge_id=request.session.get('mfa_challenge')
        if not challenge_id:return denied('challenge_expired')
        candidate=IdentityChallenge.objects.filter(pk=challenge_id).first()
        if not candidate:return denied('challenge_expired')
        budget=network_budget(request)
        if budget is not None:return budget
        with transaction.atomic():
            user,state=lock_identity(candidate.user)
            challenge=IdentityChallenge.objects.select_for_update().get(pk=candidate.pk)
            if not user.is_active or challenge.consumed or state.latest_challenge!=challenge.pk or challenge.auth_epoch!=state.auth_epoch or challenge.expires_at<=timezone.now() or challenge.session_hash!=session_hash(request):
                return denied('challenge_expired')
            blocked=limit(state,challenge)
            if blocked is not None:return blocked
            if not factor(state,request.data['method'],request.data['code']):return failed(state,challenge)
            challenge.consumed=True;challenge.save(update_fields=['consumed'])
            state.failure_count=0;state.failure_started=None;state.save()
            audit(user,'login_verified',request.data['method'])
            login(request,user,backend='django.contrib.auth.backends.ModelBackend')
            request.session.pop('mfa_challenge',None)
            stamp(request,state.auth_epoch,timezone.now().timestamp())
            return Response(current_user(user))
