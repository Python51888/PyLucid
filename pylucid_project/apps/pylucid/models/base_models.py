# coding: utf-8

"""
    PyLucid models
    ~~~~~~~~~~~~~~

    Last commit info:
    ~~~~~~~~~~~~~~~~~
    $LastChangedDate: $
    $Rev: $
    $Author: $

    :copyleft: 2009 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

import datetime

from django.db import models
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
from django.utils.translation import ugettext_lazy as _
from django.contrib.sites.managers import CurrentSiteManager

# http://code.google.com/p/django-tools/
from django_tools.middlewares import ThreadLocal

from pylucid_project.utils import form_utils
from pylucid.shortcuts import failsafe_message
from pylucid_plugins import update_journal


TAG_INPUT_HELP_URL = \
"http://google.com/search?q=cache:django-tagging.googlecode.com/files/tagging-0.2-overview.html#tag-input"



class BaseModel(models.Model):
    def get_absolute_url(self):
        raise NotImplementedError
    get_absolute_url.short_description = _('absolute url')

    def get_site(self):
        raise NotImplementedError
    get_site.short_description = _('on site')

    def get_absolute_uri(self):
        """ returned the complete absolute URI (with the domain/host part) """
        request = ThreadLocal.get_current_request()
        is_secure = request.is_secure()
        if is_secure:
            protocol = "https://"
        else:
            protocol = "http://"
        site = self.get_site()
        domain = site.domain
        absolute_url = self.get_absolute_url()
        return protocol + domain + absolute_url
    get_absolute_uri.short_description = _('absolute uri')

    class Meta:
        abstract = True



class BaseModelManager(models.Manager):
    def easy_create(self, cleaned_form_data, extra={}):
        """
        Creating a new model instance with cleaned form data witch can hold more data than for
        this model needed.
        """
        keys = self.model._meta.get_all_field_names()
        model_kwargs = form_utils.make_kwargs(cleaned_form_data, keys)
        model_kwargs.update(extra)
        model_instance = self.model(**model_kwargs)
        model_instance.save()
        return model_instance







class AutoSiteM2M(models.Model):
    """
    Add site and on_site to model, and add at least the current site in save method.
    """
    sites = models.ManyToManyField(Site)
    on_site = CurrentSiteManager('sites')

    def save(self, *args, **kwargs):
        """ Automatic current site, if not exist. """
        if self.pk == None:
            # instance needs to have a primary key value before a many-to-many relationship can be used.
            super(AutoSiteM2M, self).save(*args, **kwargs)

        if self.sites.count() == 0:
            site = Site.objects.get_current()
            if settings.DEBUG:
                failsafe_message("Automatic add site '%s' to %r" % (site.name, self))
            self.sites.add(site)

        super(AutoSiteM2M, self).save(*args, **kwargs)

    def site_info(self):
        """ for admin.ModelAdmin list_display """
        sites = self.sites.all()
        return ", ".join([site.name for site in sites])
    site_info.short_description = _('on sites')
    site_info.allow_tags = False

    class Meta:
        abstract = True


class UpdateInfoBaseModel(models.Model):
    """
    Base model with update info attributes, used by many models.
    The createby and lastupdateby ForeignKey would be automaticly updated. This needs the 
    request object as the first argument in the save method.
    
    We don't use auto_now_add and auto_now, because we want datetime.utcnow() and not datetime.now()!
    """
    objects = models.Manager()

    createtime = models.DateTimeField(default=datetime.datetime.utcnow,
        help_text="Create time (datetime is UTC)"
    )
    lastupdatetime = models.DateTimeField(help_text="Time of the last change. (datetime is UTC)")

    createby = models.ForeignKey(User, editable=False, related_name="%(class)s_createby",
        null=True, blank=True, # <- If the model used outsite a real request (e.g. unittest, db shell)
        help_text="User how create this entry.")
    lastupdateby = models.ForeignKey(User, editable=False, related_name="%(class)s_lastupdateby",
        null=True, blank=True, # <- If the model used outsite a real request (e.g. unittest, db shell)
        help_text="User as last edit this entry.")

    def save(self, *args, **kwargs):
        """
        Automatic update createby and lastupdateby attributes with the request object witch must be
        the first argument.
        """
        current_user = ThreadLocal.get_current_user()

        if current_user and isinstance(current_user, User):
            if self.pk == None or kwargs.get("force_insert", False): # New model entry
                self.createby = current_user
            self.lastupdateby = current_user

        self.lastupdatetime = datetime.datetime.utcnow()

        return super(UpdateInfoBaseModel, self).save(*args, **kwargs)

    class Meta:
        abstract = True