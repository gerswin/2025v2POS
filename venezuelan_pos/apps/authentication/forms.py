from django import forms
from django.contrib.auth import authenticate
from django.core.exceptions import ValidationError


class WebLoginForm(forms.Form):
    """Formulario de login para interfaces web."""
    
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Usuario',
            'autofocus': True,
        }),
        label='Usuario'
    )
    
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control form-control-lg',
            'placeholder': 'Contraseña',
        }),
        label='Contraseña'
    )
    
    remember_me = forms.BooleanField(
        required=False,
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
        }),
        label='Recordarme'
    )
    
    def clean(self):
        """Validar credenciales."""
        cleaned_data = super().clean()
        username = cleaned_data.get('username')
        password = cleaned_data.get('password')
        
        if username and password:
            # Verificar que las credenciales sean válidas
            user = authenticate(username=username, password=password)
            if user is None:
                raise ValidationError('Usuario o contraseña incorrectos.')
            
            if not user.is_active:
                raise ValidationError('Esta cuenta está desactivada.')
        
        return cleaned_data