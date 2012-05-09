import datetime

from django.db import models
from django.db.models.fields import EmailField
from django.contrib.localflavor.us.us_states import STATE_CHOICES

from common import fields as common_fields


"""
Monkey patch django's EmailField to default to max_length of 254
"""
def email_field_init(self, *args, **kwargs):
    kwargs['max_length'] = kwargs.get('max_length', 254)
    self._original__init__(*args, **kwargs)
EmailField._original__init__ = EmailField.__init__
EmailField.__init__ = email_field_init


"""
Soft-delete management through an is_active flag on any model
"""
class ActiveManager(models.Manager):
    def get_query_set(self):
        return super(ActiveManager, self).get_query_set().filter(is_active=True)


"""
Abstract model used as the basis for most application level models
"""
class Base(models.Model):
    date_created = models.DateTimeField(blank=True, editable=False)
    date_updated = models.DateTimeField(blank=True, editable=False)

    class Meta:
        abstract = True
        ordering = ('-date_created',)

    def __init__(self, *args, **kwargs):
        super(Base, self).__init__(*args, **kwargs)
        self._original_values = self.__dict__.copy()

    def save(self, *args, **kwargs):
        if not kwargs.pop('skip_validation', False):
            self.full_clean() 

        if kwargs.pop('update_timestamps', True):
            now = datetime.datetime.utcnow()
            if not self.pk and not self.date_created:
                self.date_created = now
            self.date_updated = now
        super(Base, self).save(*args, **kwargs)

        self._original_values = self.__dict__.copy()

    """Determine if an attribute has changed since the last save()"""
    def has_changed(self, field):
        if not self.pk:
            return False
        return getattr(self, field) != self._original_values[field]

