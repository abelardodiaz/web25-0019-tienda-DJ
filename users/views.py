#file: users/views.py

from django.contrib.auth.views import PasswordChangeView
from django.http import JsonResponse
from django.contrib.auth import update_session_auth_hash
from django.views.decorators.csrf import csrf_protect
from django.utils.decorators import method_decorator
from django.views import View
from django.shortcuts import render, redirect
from django.contrib import messages
from django.contrib.auth import login
from django.urls import reverse
from django.utils import timezone

from .forms import WhatsAppNumberForm, VerifyCodeForm
from .models import CustomUser, WhatsAppVerification
from .utils import generate_verification_code, verification_expiry, send_whatsapp_code
from core.utils import validate_next_url
from .decorators import unauthenticated_user


# -----------------------------
# Registro: elección de método (email / WhatsApp)
# -----------------------------


@unauthenticated_user
def register_choice(request):
    """Muestra una página con botones para elegir Email o WhatsApp."""
    if request.method == "POST":
        method = request.POST.get("auth_method")
        if method == "WA":
            return redirect("users:whatsapp_registration")
        # Fallback: redirigir a un registro por email estándar (no implementado aquí)
        return redirect("login")

    # Guardar página previa: priorizar 'next' si existe, sino el referer
    prev_page = request.GET.get('next') or request.META.get('HTTP_REFERER')
    request.session['redirect_after_register'] = validate_next_url(prev_page, request)
    return render(request, "users/registration_choice.html")


# -----------------------------
# Registro vía WhatsApp: solicitar número y enviar código
# -----------------------------


@method_decorator(unauthenticated_user, name='dispatch')
class WhatsAppRegistrationView(View):
    """View para REGISTRO por WhatsApp (crea nuevo usuario si no existe)."""
    template_name = "users/whatsapp_registration.html"

    def get(self, request):
        # Preservar parámetro next explícitamente
        next_param = request.GET.get('next', '')
        if next_param:
            request.session['redirect_after_register'] = validate_next_url(next_param, request)
        elif 'redirect_after_register' not in request.session:
            referer = request.META.get('HTTP_REFERER', '')
            request.session['redirect_after_register'] = validate_next_url(referer, request)
        
        form = WhatsAppNumberForm() # Añadir esta línea
        context = {
            'form': form,  # Formulario esencial
            'next_param': next_param
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Preservar next si viene en POST
        next_param = request.POST.get('next', '')
        if next_param:
            request.session['redirect_after_register'] = validate_next_url(next_param, request)
        # Flag para acción: registro (crear si no existe)
        request.session['whatsapp_action'] = 'register'
        form = WhatsAppNumberForm(request.POST, require_unique=True)
        if not form.is_valid():
            duplicate = form.has_error("phone", code="duplicate")
            return render(request, self.template_name, {"form": form, "duplicate": duplicate})

        number = form.cleaned_data["whatsapp_number"]

        # Generar código y guardarlo
        code = generate_verification_code()
        expires = verification_expiry()

        WhatsAppVerification.objects.update_or_create(
            number=number,
            defaults={"code": code, "expires_at": expires, "attempts": 0, "resend_count": 0},
        )

        # Enviar código
        try:
            send_whatsapp_code(number, code)
        except Exception as e:
            messages.error(request, f"Error enviando el código: {e}")
            return render(request, self.template_name, {"form": form})

        # Guardamos el número en sesión para usarlo en la verificación
        request.session["wa_number"] = number
        messages.success(request, "Código enviado. Revisa tu WhatsApp")
        return redirect("users:verify_whatsapp_code")


# -----------------------------
# Login vía WhatsApp: solicitar número (solo si existe) y enviar código
# -----------------------------


@method_decorator(unauthenticated_user, name='dispatch')
class WhatsAppLoginView(WhatsAppRegistrationView):
    """View para LOGIN por WhatsApp (solo si el número ya existe)."""

    def get(self, request):
        # Preservar parámetro next explícitamente
        next_param = request.GET.get('next', '')
        if next_param:
            request.session['redirect_after_register'] = validate_next_url(next_param, request)
        elif 'redirect_after_register' not in request.session:
            referer = request.META.get('HTTP_REFERER', '')
            request.session['redirect_after_register'] = validate_next_url(referer, request)
        
        form = WhatsAppNumberForm() # Añadir esta línea
        context = {
            'form': form,  # Formulario esencial
            'next_param': next_param
        }
        return render(request, self.template_name, context)

    def post(self, request):
        # Flag para acción: login (no crear nuevo)
        request.session['whatsapp_action'] = 'login'
        form = WhatsAppNumberForm(request.POST, require_unique=False)
        if not form.is_valid():
            not_registered = form.has_error("phone", code="not_registered")
            return render(request, self.template_name, {"form": form, "not_registered": not_registered})

        number = form.cleaned_data["whatsapp_number"]

        # Proceder con envío de código (como en registro)
        code = generate_verification_code()
        expires = verification_expiry()

        WhatsAppVerification.objects.update_or_create(
            number=number,
            defaults={"code": code, "expires_at": expires, "attempts": 0, "resend_count": 0},
        )

        try:
            send_whatsapp_code(number, code)
        except Exception as e:
            messages.error(request, f"Error enviando el código: {e}")
            return render(request, self.template_name, {"form": form})

        request.session["wa_number"] = number
        messages.success(request, "Código enviado. Revisa tu WhatsApp")
        return redirect("users:verify_whatsapp_code")


# -----------------------------
# Verificar código y crear usuario
# -----------------------------


@method_decorator(unauthenticated_user, name='dispatch')
class VerifyWhatsAppCodeView(View):
    """Verificación común para login/register, basada en flag de sesión."""
    template_name = "users/verify_code.html"

    MAX_ATTEMPTS = 2  # Solo un intento restante tras error

    def get(self, request):
        if not request.session.get("wa_number"):
            return redirect("users:whatsapp_registration")

        number = request.session["wa_number"]

        # Si viene ?resend=1 y el temporizador ha expirado, generar y enviar nuevo código
        if request.GET.get("resend") == "1":
            try:
                # Forzar nuevo envío incluso si está bloqueado
                record, created = WhatsAppVerification.objects.get_or_create(number=number)
                record.resend_count += 1
                record.code = generate_verification_code()
                record.created_at = timezone.now()
                record.expires_at = verification_expiry()
                record.attempts = 0  # Resetear intentos
                record.save()
                
                try:
                    send_whatsapp_code(number, record.code)
                    messages.success(request, "Nuevo código enviado. Revisa tu WhatsApp")
                except Exception as e:
                    messages.error(request, f"Error enviando el código: {e}")
            except Exception as e:
                messages.error(request, f"Error inesperado: {e}")
            return redirect("users:verify_whatsapp_code")

        try:
            record = WhatsAppVerification.objects.get(number=number)
        except WhatsAppVerification.DoesNotExist:
            return redirect("users:whatsapp_registration")

        # Cooldown dinámico basado en resend_count
        if record.resend_count == 0:
            cooldown_seconds = 120
        elif record.resend_count == 1:
            cooldown_seconds = 600  # 120 * 5
        else:
            cooldown_seconds = 1800  # 120 * 15
        seconds_left = max(0, int((record.created_at + timezone.timedelta(seconds=cooldown_seconds) - timezone.now()).total_seconds()))
        form = VerifyCodeForm()
        locked = record.attempts >= self.MAX_ATTEMPTS
        return render(
            request,
            self.template_name,
            {
                "form": form,
                "seconds_left": seconds_left,
                "attempts_left": max(0, self.MAX_ATTEMPTS - record.attempts),
                "locked": locked,
                "whatsapp_action": request.session.get('whatsapp_action', 'register')  # Asegurar que se pasa
            },
        )

    def post(self, request):
        number = request.session.get("wa_number")
        if not number:
            return redirect("users:whatsapp_registration")

        form = VerifyCodeForm(request.POST)
        if not form.is_valid():
            return render(request, self.template_name, {"form": form})

        code = form.cleaned_data["verification_code"]

        try:
            record = WhatsAppVerification.objects.get(number=number)
        except WhatsAppVerification.DoesNotExist:
            messages.error(request, "No se encontró solicitud de verificación para este número")
            return redirect("users:whatsapp_registration")

        if record.is_expired():
            messages.error(request, "El código ha expirado. Solicita uno nuevo.")
            record.delete()
            return redirect("users:whatsapp_registration")

        if record.code != code:
            record.attempts += 1
            record.save(update_fields=["attempts"])
            attempts_left = max(0, self.MAX_ATTEMPTS - record.attempts)
            locked = attempts_left == 0
            
            # Limpiar el campo de código
            form = VerifyCodeForm()  # Formulario vacío
            
            context = {
                "form": form,  # Ahora vacío
                "seconds_left": max(0, int((record.created_at + timezone.timedelta(seconds=120) - timezone.now()).total_seconds())),
                "attempts_left": attempts_left,
                "locked": locked,
                "wrong_code": True,
            }
            return render(request, self.template_name, context)

        action = request.session.get('whatsapp_action', 'register')

        # Código correcto: manejar según acción
        try:
            user = CustomUser.objects.get(whatsapp_number=number)
        except CustomUser.DoesNotExist:
            if action == 'login':
                messages.error(request, "Número no registrado. Por favor regístrate primero.")
                record.delete()
                return redirect(reverse('login'))
            # Para register: crear nuevo
            user = CustomUser.objects.create_user(
                whatsapp_number=number,
                username=number,
                auth_method=CustomUser.AUTH_WHATSAPP,
                whatsapp_verified=True,
            )
        else:
            # Existe: actualizar si necesario
            if not user.whatsapp_verified:
                user.whatsapp_verified = True
                user.save(update_fields=["whatsapp_verified"])

        user.backend = 'core.backends.WhatsAppOrEmailBackend'
        login(request, user)

        # Mensaje personalizado con últimos 4 dígitos
        last_four = number[-4:] if number else 'XXXX'
        messages.success(request, f"Usuario con (****{last_four}) inició sesión correctamente.")

        # Redirección mejorada
        redirect_to = request.session.pop('redirect_after_register', None)
        safe_redirect = validate_next_url(redirect_to, request)
        return redirect(safe_redirect or '/')


@method_decorator(csrf_protect, name='dispatch')
class CustomPasswordChangeView(PasswordChangeView):
    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if form.is_valid():
            form.save()
            # Mantener la sesión activa después de cambiar contraseña
            update_session_auth_hash(request, form.user)
            return JsonResponse({
                'success': True,
                'message': 'Contraseña cambiada exitosamente'
            })
        else:
            return JsonResponse({
                'success': False,
                'errors': form.errors.get_json_data()
            }, status=400)

    def form_invalid(self, form):
        return JsonResponse({
            'success': False,
            'errors': form.errors.get_json_data()
        }, status=400)
    

    