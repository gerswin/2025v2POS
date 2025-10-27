from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.http import HttpResponseRedirect
from django.views.decorators.csrf import csrf_protect
from django.views.decorators.cache import never_cache

from .forms import WebLoginForm


@csrf_protect
@never_cache
def web_login(request):
    """Vista de login para interfaces web."""
    
    # Si ya está autenticado, redirigir al dashboard
    if request.user.is_authenticated:
        return redirect('events:dashboard')
    
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        
        if username and password:
            user = authenticate(request, username=username, password=password)
            if user is not None:
                if user.is_active:
                    login(request, user)
                    
                    # Mensaje de bienvenida
                    if user.tenant:
                        messages.success(
                            request, 
                            f'¡Bienvenido {user.first_name}! Has iniciado sesión en {user.tenant.name}.'
                        )
                    else:
                        messages.success(
                            request, 
                            f'¡Bienvenido {user.first_name}! Has iniciado sesión como administrador del sistema.'
                        )
                    
                    # Redirigir a la página solicitada o al dashboard
                    next_url = request.GET.get('next', reverse('events:dashboard'))
                    return HttpResponseRedirect(next_url)
                else:
                    messages.error(request, 'Tu cuenta está desactivada.')
            else:
                messages.error(request, 'Usuario o contraseña incorrectos.')
        else:
            messages.error(request, 'Por favor ingresa usuario y contraseña.')
    
    form = WebLoginForm()
    context = {
        'form': form,
        'next': request.GET.get('next', ''),
    }
    
    return render(request, 'authentication/login.html', context)


@login_required
def web_logout(request):
    """Vista de logout para interfaces web."""
    
    user_name = request.user.first_name or request.user.username
    logout(request)
    
    messages.success(request, f'¡Hasta luego {user_name}! Has cerrado sesión exitosamente.')
    return redirect('auth:login')


@login_required
def web_profile(request):
    """Vista de perfil de usuario para interfaces web."""
    
    context = {
        'user': request.user,
    }
    
    return render(request, 'authentication/profile.html', context)