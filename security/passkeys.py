"""Administrator passkeys: password plus WebAuthn, with email recovery retained."""
import hashlib
import json
from datetime import timedelta
from urllib.parse import urlsplit
from django.conf import settings
from django.contrib.auth import authenticate
from django.db import transaction, IntegrityError
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import ValidationError, PermissionDenied
from rest_framework.permissions import BasePermission, AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from drf_spectacular.utils import extend_schema
from webauthn import generate_registration_options, generate_authentication_options, verify_registration_response, verify_authentication_response, options_to_json, base64url_to_bytes
from webauthn.helpers import bytes_to_base64url
from webauthn.helpers.exceptions import WebAuthnException
from webauthn.helpers.structs import AuthenticatorSelectionCriteria, UserVerificationRequirement, PublicKeyCredentialDescriptor
from core.authorization import Authorization
from core.capability_service import CapabilityService
from api.throttles import LoginRateThrottle, VerificationRateThrottle, SensitiveActionRateThrottle
from .models import AdministratorPasskey, PasskeyChallenge, ActiveSession
from .services import create_audit_log, create_active_session, record_login, is_account_locked, register_failed_attempt, clear_failed_attempts, terminate_user_sessions
from .utils import get_client_ip


def configuration():
    rp, origins = settings.WEBAUTHN_RP_ID, list(settings.WEBAUTHN_ORIGINS)
    if not rp or not origins or '/' in rp or ':' in rp:
        raise ValidationError("Passkeys are not configured for this deployment. Use email verification.")
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme not in ('https', 'http') or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment
                or not parsed.hostname or not (parsed.hostname == rp or parsed.hostname.endswith('.'+rp))
                or (parsed.scheme == 'http' and (rp != 'localhost' or not settings.DEBUG))):
            raise ValidationError("Passkeys are not configured for this deployment. Use email verification.")
    return rp, origins


def platform_operator(user):
    return CapabilityService.is_platform_operator(user) and bool(CapabilityService.platform_capabilities(user)) and Authorization.can_authenticate(user)


class OwnPasskeyPermission(BasePermission):
    def has_permission(self, request, view):
        return platform_operator(request.user)


class PasskeySummary(serializers.ModelSerializer):
    class Meta:
        model = AdministratorPasskey
        fields = ('id', 'name', 'created_at', 'last_used_at', 'revoked_at')
        read_only_fields = fields


class ManagementRequest(serializers.Serializer):
    password = serializers.CharField(write_only=True, trim_whitespace=False, max_length=256)


class RegisterRequest(ManagementRequest):
    name = serializers.CharField(max_length=80)


class PasskeyLoginRequest(ManagementRequest):
    email = serializers.EmailField()


class ProofRequest(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    credential = serializers.JSONField()

    def validate_credential(self, value):
        if not isinstance(value, dict) or len(json.dumps(value)) > 20000:
            raise serializers.ValidationError("Invalid passkey response.")
        return value


class OptionsResponse(serializers.Serializer):
    challenge_id = serializers.UUIDField()
    options = serializers.DictField()


class TokenResponse(serializers.Serializer):
    access = serializers.CharField()
    refresh = serializers.CharField()


class PasskeyMessageResponse(serializers.Serializer):
    detail = serializers.CharField()


class ListResponse(serializers.Serializer):
    enabled = serializers.BooleanField()
    can_enroll = serializers.BooleanField()
    passkeys = PasskeySummary(many=True)


def payload(request, serializer):
    data = serializer(data=request.data)
    data.is_valid(raise_exception=True)
    return data.validated_data


def fresh_session(request):
    token = request.auth
    sid = token.get('sid') if token is not None else None
    return ActiveSession.objects.filter(pk=sid, user=request.user, is_active=True, expires_at__gt=timezone.now(),
        mfa_verified_at__gt=timezone.now()-timedelta(minutes=15)).first() if sid else None


def management(request):
    session = fresh_session(request)
    if not session:
        raise PermissionDenied("Sign in again with email verification or a passkey before managing passkeys.")
    if is_account_locked(request.user.email, get_client_ip(request)):
        raise PermissionDenied("Sign-in is temporarily unavailable. Try again later.")
    if not request.user.check_password(request.data.get('password', '')):
        register_failed_attempt(request.user.email, get_client_ip(request), reason="Passkey management password failed")
        return None
    return session


def reject_embedded_ceremony(credential):
    client_data = json.loads(base64url_to_bytes(credential['response']['clientDataJSON']))
    if not isinstance(client_data, dict) or client_data.get('crossOrigin', False) is not False or 'topOrigin' in client_data:
        raise ValueError('Use the administrator site directly, not an embedded frame.')


def digest(user):
    return hashlib.sha256(user.password.encode()).hexdigest()


def issue(user, purpose, challenge, **extra):
    user.__class__.objects.select_for_update().get(pk=user.pk)
    PasskeyChallenge.objects.filter(user=user, purpose=purpose, consumed_at__isnull=True).update(consumed_at=timezone.now())
    return PasskeyChallenge.objects.create(user=user, purpose=purpose, challenge=challenge,
        password_digest=digest(user), expires_at=timezone.now()+timedelta(minutes=3), **extra)


def take(values, purpose, user=None):
    query = PasskeyChallenge.objects.select_for_update().select_related('user').filter(pk=values['challenge_id'], purpose=purpose)
    if user is not None:
        query = query.filter(user=user)
    challenge = query.first()
    if not challenge or challenge.consumed_at or challenge.expires_at <= timezone.now() or not platform_operator(challenge.user) or challenge.password_digest != digest(challenge.user):
        raise ValidationError("This passkey request expired. Start again.")
    challenge.consumed_at = timezone.now()
    challenge.save(update_fields=('consumed_at',))
    return challenge


class OwnPasskeys(APIView):
    permission_classes = (OwnPasskeyPermission,)

    @extend_schema(responses=ListResponse)
    def get(self, request):
        try:
            configuration()
            enabled = True
        except ValidationError:
            enabled = False
        return Response({'enabled': enabled, 'can_enroll': bool(fresh_session(request)),
            'passkeys': PasskeySummary(AdministratorPasskey.objects.filter(user=request.user, revoked_at__isnull=True).order_by('-created_at'), many=True).data})


class RegistrationOptions(APIView):
    permission_classes = (OwnPasskeyPermission,)
    throttle_classes = (SensitiveActionRateThrottle,)

    @extend_schema(request=RegisterRequest, responses=OptionsResponse)
    @transaction.atomic
    def post(self, request):
        values = payload(request, RegisterRequest)
        session = management(request)
        if session is None:
            return Response({'detail': 'Your password could not be verified.'}, status=400)
        rp, _ = configuration()
        if AdministratorPasskey.objects.filter(user=request.user, revoked_at__isnull=True).count() >= 10:
            raise ValidationError("Remove an unused passkey before adding another.")
        options = generate_registration_options(rp_id=rp, rp_name='SmartBiz', user_id=request.user.pk.bytes, user_name=request.user.email,
            authenticator_selection=AuthenticatorSelectionCriteria(user_verification=UserVerificationRequirement.REQUIRED),
            exclude_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(key.credential_id)) for key in AdministratorPasskey.objects.filter(user=request.user)])
        challenge = issue(request.user, 'REGISTER', options.challenge, session=session, name=values['name'])
        return Response({'challenge_id': str(challenge.pk), 'options': json.loads(options_to_json(options))})


class RegistrationVerify(APIView):
    permission_classes = (OwnPasskeyPermission,)
    throttle_classes = (SensitiveActionRateThrottle,)

    @extend_schema(request=ProofRequest, responses={201: PasskeySummary})
    @transaction.atomic
    def post(self, request):
        values = payload(request, ProofRequest)
        session = fresh_session(request)
        challenge = take(values, 'REGISTER', request.user)
        if not session or challenge.session_id != session.pk:
            return Response({'detail': 'Sign in again before adding a passkey.'}, status=403)
        if AdministratorPasskey.objects.filter(user=request.user, revoked_at__isnull=True).count() >= 10:
            return Response({'detail': 'Remove an unused passkey before adding another.'}, status=400)
        rp, origins = configuration()
        try:
            reject_embedded_ceremony(values['credential'])
            verified = verify_registration_response(credential=values['credential'], expected_challenge=bytes(challenge.challenge), expected_rp_id=rp, expected_origin=origins, require_user_verification=True)
            with transaction.atomic():
                key = AdministratorPasskey.objects.create(user=request.user, name=challenge.name, credential_id=bytes_to_base64url(verified.credential_id), public_key=verified.credential_public_key, sign_count=verified.sign_count)
        except (WebAuthnException, ValueError, IntegrityError, TypeError, AttributeError, KeyError):
            return Response({'detail': 'The passkey could not be verified. Start again.'}, status=400)
        create_audit_log(user=request.user, request=request, action='ADMINISTRATOR_PASSKEY_ADDED', severity='WARNING', obj=key, description='Administrator added a passkey.')
        return Response(PasskeySummary(key).data, status=201)


class RevokePasskey(APIView):
    permission_classes = (OwnPasskeyPermission,)
    throttle_classes = (SensitiveActionRateThrottle,)

    @extend_schema(request=ManagementRequest, responses=PasskeyMessageResponse)
    @transaction.atomic
    def post(self, request, pk):
        payload(request, ManagementRequest)
        if management(request) is None:
            return Response({'detail': 'Your password could not be verified.'}, status=400)
        from rest_framework.generics import get_object_or_404
        key = get_object_or_404(AdministratorPasskey.objects.select_for_update(), pk=pk, user=request.user, revoked_at__isnull=True)
        key.revoked_at = timezone.now()
        key.save(update_fields=('revoked_at',))
        PasskeyChallenge.objects.filter(user=request.user, consumed_at__isnull=True).update(consumed_at=timezone.now())
        terminate_user_sessions(request.user, actor=request.user, reason='SECURITY', note='Administrator passkey removed', request=request)
        create_audit_log(user=request.user, request=request, action='ADMINISTRATOR_PASSKEY_REMOVED', severity='WARNING', obj=key, description='Administrator removed a passkey and ended their sessions.')
        return Response({'detail': 'Passkey removed. Sign in again.'})


class LoginOptions(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (LoginRateThrottle,)

    @extend_schema(request=PasskeyLoginRequest, responses=OptionsResponse)
    @transaction.atomic
    def post(self, request):
        values = payload(request, PasskeyLoginRequest)
        ip = get_client_ip(request)
        email = values['email'].strip().lower()
        if is_account_locked(email, ip):
            raise ValidationError('Unable to use this sign-in method. Try later or use email verification.')
        user = authenticate(request=request, email=email, password=values['password'])
        if not user or not platform_operator(user):
            register_failed_attempt(email, ip)
            return Response({'detail': 'Unable to use this sign-in method. Check your details or use email verification.'}, status=400)
        keys = AdministratorPasskey.objects.filter(user=user, revoked_at__isnull=True)
        if not keys.exists():
            return Response({'detail': 'No passkey is available. Use email verification, then add one in Platform navigation > My passkeys.'}, status=400)
        rp, _ = configuration()
        options = generate_authentication_options(rp_id=rp, user_verification=UserVerificationRequirement.REQUIRED,
            allow_credentials=[PublicKeyCredentialDescriptor(id=base64url_to_bytes(key.credential_id)) for key in keys])
        challenge = issue(user, 'LOGIN', options.challenge)
        return Response({'challenge_id': str(challenge.pk), 'options': json.loads(options_to_json(options))})


class LoginVerify(APIView):
    permission_classes = (AllowAny,)
    authentication_classes = ()
    throttle_classes = (VerificationRateThrottle,)

    @extend_schema(request=ProofRequest, responses=TokenResponse)
    @transaction.atomic
    def post(self, request):
        values = payload(request, ProofRequest)
        challenge = take(values, 'LOGIN')
        user = challenge.user
        ip = get_client_ip(request)
        if is_account_locked(user.email, ip):
            return Response({'detail': 'Sign-in is temporarily unavailable. Try again later.'}, status=400)
        rp, origins = configuration()
        try:
            reject_embedded_ceremony(values['credential'])
            raw_id = values['credential'].get('id', '')
            key = AdministratorPasskey.objects.select_for_update().get(user=user, credential_id=raw_id, revoked_at__isnull=True)
            verified = verify_authentication_response(credential=values['credential'], expected_challenge=bytes(challenge.challenge), expected_rp_id=rp, expected_origin=origins,
                credential_public_key=bytes(key.public_key), credential_current_sign_count=key.sign_count, require_user_verification=True)
            user_handle = values['credential'].get('response', {}).get('userHandle')
            if user_handle and base64url_to_bytes(user_handle) != user.pk.bytes:
                raise ValueError('Wrong account')
        except (WebAuthnException, ValueError, AdministratorPasskey.DoesNotExist, TypeError, AttributeError, KeyError):
            register_failed_attempt(user.email, ip, reason='Passkey verification failed')
            create_audit_log(user=user, request=request, action='ADMINISTRATOR_PASSKEY_LOGIN', status='FAILED', description='Passkey verification failed.')
            return Response({'detail': 'The passkey could not be verified. Start again or use email verification.'}, status=400)
        key.sign_count = verified.new_sign_count
        key.last_used_at = timezone.now()
        key.save(update_fields=('sign_count', 'last_used_at'))
        clear_failed_attempts(user.email, ip)
        refresh = RefreshToken.for_user(user)
        session = create_active_session(request, user, refresh['jti'], mfa_verified=True)
        refresh['sid'] = str(session.pk)
        record_login(request, user, session=session)
        create_audit_log(user=user, request=request, action='ADMINISTRATOR_PASSKEY_LOGIN', description='Administrator signed in with password and verified passkey.')
        return Response({'access': str(refresh.access_token), 'refresh': str(refresh)})
