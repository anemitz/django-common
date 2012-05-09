from django import forms
from django.contrib.auth.models import User
from django.utils.translation import ugettext as _
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.forms import AuthenticationForm as AuthAuthenticationForm


class RequiredNullBooleanField(forms.NullBooleanField):
    widget = forms.RadioSelect(choices=[(True, "Yes"), (False, "No")])
    
    def clean(self, value):
        value = super(RequiredNullBooleanField, self).clean(value)
        if value is None:
            raise forms.ValidationError("This field is required.")
        return value


class OptionalPasswordChangeForm(PasswordChangeForm):
    def __init__(self, *args, **kwargs):
        super(OptionalPasswordChangeForm, self).__init__(*args, **kwargs)
        
        if not self.data.get('old_password', None) and \
           not self.data.get('new_password1', None) and \
           not self.data.get('new_password2'):

            self.fields['old_password'].required = False
            self.fields['new_password1'].required = False
            self.fields['new_password2'].required = False
            self.clean_old_password = lambda : None
            self.new_password2 = lambda : None
            self.save = lambda : self.user


class AuthenticationForm(AuthAuthenticationForm):
    username = forms.CharField(label=_("E-mail address"), max_length=254)


class RequestForm(forms.Form):
    def __init__(self, request, *args, **kwargs):
        self.request = request
        super(RequestForm, self).__init__(*args, **kwargs)


class ChangeEmailForm(forms.ModelForm):
    email = forms.EmailField(required=True)

    class Meta:
        model = User
        fields = ('email',)

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop('user', None)
        super(ChangeEmailForm, self).__init__(*args, **kwargs)

    def clean_email(self):
        email = self.cleaned_data.get('email')
        existing_users = list(User.objects.filter(email=email))
        if existing_users and existing_users[0] != self.instance:
            raise forms.ValidationError(_('A user with this email address already exists. Please choose a different one.'))
        return email
