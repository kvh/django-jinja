"""
Using Jinja2 with Django 1.2
Based on: http://djangosnippets.org/snippets/2063/

To use:
  * Add this template loader to settings: `TEMPLATE_LOADERS`
  * Add template dirs to settings: `JINJA2_TEMPLATE_DIRS`

If in template debug mode - we fire the template rendered signal, which allows
debugging the context with the debug toolbar.  Viewing source currently doesnt
work.

If you want {% url %} or {% csrf_token %} support I recommend grabbing them
from Coffin (http://github.com/dcramer/coffin/blob/master/coffin/template/defaulttags.py)
Note for namespaced urls you have to use quotes eg:
  {% url account:login %} => {% url "account:login" %}
"""
import jinja2

from django.template.loader import BaseLoader
from django.template import TemplateDoesNotExist, Origin
from django.core import urlresolvers
from django.conf import settings
from django_jinja_extensions import update_querystring
from hamlish_jinja import HamlishExtension
from webassets import Environment as AssetsEnvironment

class Template(jinja2.Template):
    def render(self, context):
        # flatten the Django Context into a single dictionary.
        context_dict = {}
        for d in context.dicts:
            context_dict.update(d)

        if settings.TEMPLATE_DEBUG:
            from django.test import signals
            self.origin = Origin(self.filename)
            signals.template_rendered.send(sender=self, template=self, context=context)

        return super(Template, self).render(context_dict)

def guess_autoescape(template_name):
    if template_name is None or '.' not in template_name:
        return False
    ext = template_name.rsplit('.', 1)[1]
    return ext in ('html', 'htm', 'xml', 'haml')

auto_escape = guess_autoescape if settings.TEMPLATE_AUTOESCAPE else lambda x:False

class Loader(BaseLoader):
    """
    A file system loader for Jinja2.

    Requires the following setting `JINJA2_TEMPLATE_DIRS`
    """
    is_usable = True
    exts = (
            'django_jinja_extensions.URLExtension',
            'django_jinja_extensions.CsrfTokenExtension',
            'django_jinja_extensions.MarkdownExtension',
            HamlishExtension,
        )
    exts += settings.JINJA2_EXTENSIONS
    # Set up the jinja env and load any extensions you may have
    env = jinja2.Environment(
        autoescape=auto_escape,
        loader=jinja2.FileSystemLoader(settings.JINJA2_TEMPLATE_DIRS),
        extensions=exts
    )
    env.filters['update_querystring'] = update_querystring
    env.template_class = Template
    env.assets_environment = AssetsEnvironment(settings.ASSETS_ROOT,
            settings.ASSETS_URL)
    # These are available to all templates.
    env.globals['url_for'] = urlresolvers.reverse
    env.globals['MEDIA_URL'] = settings.MEDIA_URL
    env.globals['STATIC_URL'] = settings.STATIC_URL
    
    def load_template(self, template_name, template_dirs=None):
        try:
            template = self.env.get_template(template_name)
            return template, template.filename
        except jinja2.TemplateNotFound:
            raise TemplateDoesNotExist(template_name)
