from django import forms

class UploadFileForm(forms.Form):
    file = forms.FileField(required=True)
    admin_pin = forms.CharField(required=True, max_length=10, widget=forms.PasswordInput)

class SimpleSearchForm(forms.Form):
    name = forms.CharField(required=True, label='Korean or English name')

class ApplyPasswordForm(forms.Form):
    record_password = forms.CharField(required=True, max_length=10, widget=forms.PasswordInput, label='4-digit password')
