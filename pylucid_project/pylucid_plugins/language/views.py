# coding: utf-8

"""
    PyLucid language tools
    ~~~~~~~~~~~~~~~~~~~~~~

    Last commit info:
    ~~~~~~~~~~~~~~~~~
    $LastChangedDate: $
    $Rev: $
    $Author: JensDiemer $

    :copyleft: 2009 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.p

"""

__version__ = "$Rev:$"

from django.conf import settings
from django.template import RequestContext
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect
from django.shortcuts import render_to_response

from pylucid_project.apps.pylucid.system import i18n
from pylucid_project.apps.pylucid.models import PageMeta, Language
from pylucid_project.apps.pylucid.decorators import render_to

from language.preference_forms import LanguagePrefForm

RESET_KEY = "reset"

def _can_reset():
    # Get preferences
    pref_form = LanguagePrefForm()
    pref_data = pref_form.get_preferences()
    return pref_data["add_reset_link"] or settings.DEBUG or settings.PYLUCID.I18N_DEBUG

@render_to("language/language_selector.html")
def lucidTag(request):
    """ insert language selector list into page """
    existing_languages = Language.objects.all_accessible(request.user)
    if len(existing_languages) < 2:
        # Don't insert the language selector, if there only exist one language ;)
        if request.user.is_superuser:
            # Display a superuser a information (only one time per session)
            key = "useless_language_plugin"
            if key not in request.session:
                request.page_msg(
                    "It's useless to insert lucidtag language into this site!"
                    "For better performance you can remove this tag."
                )
                request.session[key] = True
        return

    current_language = request.PYLUCID.language_entry
    current_pagetree = request.PYLUCID.pagetree
    absolute_url = current_pagetree.get_absolute_url()
    current_url = absolute_url.strip("/") # For {% url ... %}

    context = {
        "current_language": current_language,
        "current_url": current_url,
        "existing_languages": existing_languages,
        "add_reset_link": _can_reset(),
        "reset_key": RESET_KEY,
    }
    return context



def http_get_view(request):
    """
    Switch the client favored language and save it for every later requests.
    """
#    if settings.DEBUG or settings.PYLUCID.I18N_DEBUG:
#        request.page_msg("Switch the client favored language.")

    user = request.user

    raw_lang_code = request.GET.get("language", False)
    if not raw_lang_code:
        if settings.DEBUG or settings.PYLUCID.I18N_DEBUG:
            request.page_msg.error("No language code!")
        return

    if raw_lang_code == RESET_KEY:
        # We should reset the current saved language data
        if not _can_reset():
            if settings.DEBUG or settings.PYLUCID.I18N_DEBUG:
                request.page_msg.error("Error: i18n reset is off!")
            return
        return i18n.reset_language_settings(request)

    if len(raw_lang_code) != 2:
        if settings.DEBUG or settings.PYLUCID.I18N_DEBUG:
            request.page_msg.error("Language code length != 2 !")
        return

    if raw_lang_code == request.PYLUCID.language_entry.code:
        # Use the current lang entry and save it
        lang_entry = request.PYLUCID.language_entry
        if settings.DEBUG or settings.PYLUCID.I18N_DEBUG:
            request.page_msg.error("Save current lang entry.")
    else:
        existing_languages = Language.objects.all_accessible(user)
        try:
            lang_entry = existing_languages.get(code=raw_lang_code)
        except Language.DoesNotExist, err:
            if settings.DEBUG or settings.PYLUCID.I18N_DEBUG:
                request.page_msg.error("Wrong lang code in get parameter: %s" % err)
            return

    i18n.activate_language(request, lang_entry, save=True)

    current_pagemeta = request.PYLUCID.pagemeta
    if current_pagemeta.language == lang_entry:
        if settings.PYLUCID.I18N_DEBUG:
            request.page_msg.error("Current page is in right language. No redirect needed.")
        return

    pagetree = request.PYLUCID.pagetree
    try:
        pagemeta = PageMeta.objects.get(pagetree=pagetree, language=lang_entry)
    except PageMeta.DoesNotExist, err:
        if settings.PYLUCID.I18N_DEBUG:
            request.page_msg.error("PageMeta doesn't exist in lang %r. So no redirect needed." % lang_entry)
        return

    # change only the lang code in the url:
    new_url = i18n.change_url(request, new_lang_code=pagemeta.language.code, save_get_parameter=False)

    # redirect, so the new selected language would be used
    return HttpResponseRedirect(new_url)
