# setup/views.py
from django import forms
from django.contrib.auth import get_user_model
from django.shortcuts import render, redirect
from products.models import SyscomCredential

class SetupForm(forms.Form):
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput)
    client_id = forms.CharField(label='Syscom Client ID')
    client_secret = forms.CharField(label='Syscom Client Secret')

def welcome(request):
    if request.method == 'POST':
        form = SetupForm(request.POST)
        if form.is_valid():
            User = get_user_model()
            User.objects.create_superuser(
                username=form.cleaned_data['email'],
                email=form.cleaned_data['email'],
                password=form.cleaned_data['password'],
                role='ADMIN',
            )
            SyscomCredential.objects.create(
                client_id=form.cleaned_data['client_id'],
                client_secret=form.cleaned_data['client_secret'],
            )
            return redirect('login')
    else:
        form = SetupForm()
    return render(request, 'setup/welcome.html', {'form': form})
