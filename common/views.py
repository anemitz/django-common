import json

from django.views.generic import FormView
from django.contrib.auth.models import User
from django.utils.decorators import method_decorator
from django.contrib.auth.decorators import login_required
from django.views.generic.base import TemplateResponseMixin
from django.views.generic.edit import FormMixin, ProcessFormView
from django.http import HttpResponse, Http404, HttpResponseRedirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_backends, SESSION_KEY, BACKEND_SESSION_KEY


class MultipleFormsMixin(FormMixin):
    """
    A mixin that provides a way to show and handle several forms in a
    request.
    """
    form_classes = {} # set the form classes as a mapping

    def get_form_classes(self):
        return self.form_classes

    def get_forms(self, form_classes):
        return dict([(key, klass(**self.get_form_kwargs())) \
            for key, klass in form_classes.items()])

    def forms_valid(self, forms):
        return super(MultipleFormsMixin, self).form_valid(forms)

    def forms_invalid(self, forms):
        return self.render_to_response(self.get_context_data(forms=forms))


class ProcessMultipleFormsView(ProcessFormView):
    """
    A mixin that processes multiple forms on POST. Every form must be
    valid.
    """
    def get(self, request, *args, **kwargs):
        form_classes = self.get_form_classes()
        forms = self.get_forms(form_classes)
        return self.render_to_response(self.get_context_data(forms=forms))

    def post(self, request, *args, **kwargs):
        form_classes = self.get_form_classes()
        forms = self.get_forms(form_classes)
        if all([form.is_valid() for form in forms.values()]):
            return self.forms_valid(forms)
        else:
            return self.forms_invalid(forms)


class BaseMultipleFormsView(MultipleFormsMixin, ProcessMultipleFormsView):
    """
    A base view for displaying several forms.
    """


class MultipleFormsView(TemplateResponseMixin, BaseMultipleFormsView):
    """
    A view for displaying several forms, and rendering a template response.
    """


class JSONResponseMixin(object):
    def render_to_response(self, context):
        "Returns a JSON response containing 'context' as payload"
        return self.get_json_response(self.convert_context_to_json(context))

    def get_json_response(self, content, **httpresponse_kwargs):
        "Construct an `HttpResponse` object."
        return HttpResponse(content,
                                 content_type='application/json',
                                 **httpresponse_kwargs)

    def convert_context_to_json(self, context):
        "Convert the context dictionary into a JSON object"
        # Note: This is *EXTREMELY* naive; in reality, you'll need
        # to do much more complex handling to ensure that arbitrary
        # objects -- such as Django model instances or querysets
        # -- can be serialized as JSON.
        return json.dumps(context)


class JSONFormView(JSONResponseMixin, FormView):
    pass


class LoginRequiredMixin(object):
    @method_decorator(login_required)
    def dispatch(self, *args, **kwargs):
        return super(LoginRequiredMixin, self).dispatch(*args, **kwargs)


"""
Swap sessions with another user.  Nicely added to the django user admin
"""
@staff_member_required
def su(request, user_id):
    if not request.user.is_superuser:
        raise Http404
    try:
        try:
            id = int(user_id)
            user = User.objects.get(pk=user_id)
        except ValueError:
            if '@' in user_id:
                user = User.objects.get(email=user_id)
            else:
                user = User.objects.get(username=user_id)

        # In lieu of a call to authenticate()
        backend = get_backends()[0]
        user.backend = "%s.%s" % (backend.__module__, backend.__class__.__name__)

        request.session.clear()
        request.session[SESSION_KEY] = user.id
        request.session[BACKEND_SESSION_KEY] = user.backend

    except User.DoesNotExist:
        pass

    return HttpResponseRedirect('/')

