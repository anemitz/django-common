import re
import csv
import json
import datetime
from decimal import Decimal

from django.conf import settings
from django.template import loader
from django.core.cache import cache
from django.core.urlresolvers import reverse
from django.contrib.sites.models import Site
from django.core.mail import mail_admins, EmailMultiAlternatives


"""
Wrapper around csv reader that ignores non utf-8 chars and strips the record
"""
class CsvReader(object):
    def __init__(self, file_name, delimiter=','):
        self.reader = csv.reader(open(file_name, 'rbU'), delimiter=delimiter)
 
    def __iter__(self):
        return self

    def next(self):
        row = self.reader.next()       
        row = [el.decode('utf8', errors='ignore').replace('\"', '').strip() for el in row]
        return row


def mail_exception(subject=None, context=None, vars=True):
    import traceback, sys

    exc_info = sys.exc_info()

    if not subject:
        subject = exc_info[1].__class__.__name__

    message = ''

    if context:
        message += 'Context:\n\n'
        try:
            message += '\n'.join(['%s: %s' % (k, v) for k, v in context.iteritems()])
        except:
            message += 'Error reporting context.'
        message += '\n\n\n\n'


    if vars:
        tb = exc_info[2]
        stack = []

        while tb:
            stack.append(tb.tb_frame)
            tb = tb.tb_next

        message = "Locals by frame, innermost last:\n"

        for frame in stack:
            message += "\nFrame %s in %s at line %s\n" % (frame.f_code.co_name,
                                                 frame.f_code.co_filename,
                                                 frame.f_lineno)
            for key, value in frame.f_locals.items():
                message += "\t%16s = " % key
                # We have to be careful not to cause a new error in our error
                # printer! Calling repr() on an unknown object could cause an
                # error we don't want.
                try:
                    message += '%s\n' % repr(value)
                except:
                    message += "<ERROR WHILE PRINTING VALUE>\n"


    message += '\n\n\n%s\n' % (
            '\n'.join(traceback.format_exception(*exc_info)),
        )

    if settings.DEBUG:
        print subject
        print
        print message
    else:
        mail_admins(subject, message, fail_silently=True)


def utctoday():
    now = datetime.datetime.utcnow()
    today = datetime.date(*now.timetuple()[:3])
    return today


def localtoday():
    import pytz
    from django_tz.global_tz import get_timezone

    tz = get_timezone()
    local_now = tz.normalize(pytz.utc.localize(datetime.datetime.utcnow()).astimezone(tz))
    local_today = datetime.date(*local_now.timetuple()[:3])
    return local_today


def ellipsize(s, length):
    if not s:
        return ''
    if len(s) <= length:
        return s
    else:
        return s[:length-3] + '...'


def use_ssl():
    if hasattr(settings, 'USE_SSL'):
        return settings.USE_SSL
    return False


# Like reverse(), but returns an full URL 
def full_reverse(*args, **kwargs):
    domain = kwargs.pop('rewrite_domain', None)
    ssl = kwargs.pop('use_ssl', use_ssl())
    return 'http%s://%s%s' % (
        ssl and 's' or '',
        domain or Site.objects.get_current().domain,
        reverse(*args, **kwargs)
    )


def full_url(url):
    return 'http%s://%s%s' % (
        use_ssl() and 's' or '',
        Site.objects.get_current().domain,
        url
    )


def full_url_context(request):
    return {
        'STATIC_URL': full_url(settings.STATIC_URL),
        'MEDIA_URL': full_url(settings.MEDIA_URL),
        'BASE_URL': 'http%s://%s' % (use_ssl() and 's' or '', Site.objects.get_current().domain),
    }


def date_range(start, end):
    len = (end-start).days
    dates = [start+datetime.timedelta(days=n) for n in range(len+1)]
    return dates


# returns a tuple (n, obj) where n means:
#     0: nothing changed
#     1: updated object
#     2: created object
def create_or_update(model_class, filter_attrs, attrs, create_attrs={}, update_attrs={}):
    rows = model_class.objects.filter(**filter_attrs)
    if rows:
        updated = rows.exclude(**attrs).update(**dict(attrs, **update_attrs))
        if updated:
            return 1, rows[0]
        else:
            return 0, rows[0]
    else:
        attrs.update(filter_attrs)
        attrs.update(create_attrs)
        obj = model_class.objects.create(**attrs)
        return 2, obj


# SQL
def sql(cursor, sql):
    def dict_factory(cursor, row):
        d = {}
        for idx, col in enumerate(cursor.description):
            d[col[0]] = row[idx]
        return d

    cursor.execute(sql)
    rows = [dict_factory(cursor, row) for row in cursor.fetchall()]
    return rows


def render_html_email(name, context):
    import pynliner

    subject = loader.render_to_string('%s.subj.txt' % name, context).strip()
    text_body = loader.render_to_string('%s.body.txt' % name, context)
    html_body = loader.render_to_string('%s.body.html' % name, context)

    css_body = loader.render_to_string(['%s.css' % name])

    # convert to inline-css
    html_body = pynliner.Pynliner().from_string(html_body).with_cssString(css_body).run()

    return subject, text_body, html_body


# JSON
class Encoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return str(obj)
        if isinstance(obj, datetime.datetime):
            return str(obj).split('.')[0]
        if isinstance(obj, datetime.date):
            return str(obj)
        return obj


def format_us_phone_number(value):
    phone = parse(value, 'US')
    formatted = format_number(phone, PhoneNumberFormat.E164)
    if phone.extension:
        formatted += 'x%s' % phone.extension
    return formatted

