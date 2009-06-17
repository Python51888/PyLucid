# coding:utf-8

"""
    PyLucid shortcuts
    ~~~~~~~~~~~~~~~~~
    
    render_pylucid_response() - Similar to django.shortcuts.render_to_response, can be used in
        PyLucid plugin "ajax+normal response" views.

    Last commit info:
    ~~~~~~~~~~~~~~~~~
    $LastChangedDate: $
    $Rev: $
    $Author: $

    :copyleft: 2009 by the PyLucid team, see AUTHORS for more details.
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

import warnings

from django import http
from django.conf import settings
from django.contrib.auth.models import User
from django.shortcuts import render_to_response
from django.template.loader import render_to_string

from django_tools.middlewares import ThreadLocal


def render_pylucid_response(request, template_name, context, **kwargs):
    """
    Similar to django.shortcuts.render_to_response.
    
    If it's a ajax request: insert extra head content and return a HttpResponse object.
    This will be send directly back to the client.
    
    If it's not a ajax request: render the plugin template and return it as a String: So it
    will be replace the cms page content in the global template. The complete page would be
    rendered.
    """
    response_content = render_to_string(template_name, context, **kwargs)
    
    if request.is_ajax():
        #if settings.DEBUG: print "make ajax response..."
            
        # Get the extrahead storage (pylucid.system.extrahead.ExtraHead)
        extrahead = request.PYLUCID.extrahead

        # Get the extra head content as a string
        extra_head_content = extrahead.get()
        
        # insert the extra head content into the response content
        # Note: In a ajax view the {% extrahead %} block would normaly not rendered into
        # the response content. Because the view returns a HttpResponse object, so all
        # other processing skip and all PyLucid context middleware (in the global template)
        # would not rendered.
        response_content = extra_head_content + "\n" + response_content
        
        http_response_kwargs = {'mimetype': kwargs.pop('mimetype', None)}
        return http.HttpResponse(response_content, **http_response_kwargs)
    else:
        # Non-Ajax request: the string content would be replace the page content.
        # The {% extrahead %} content would be inserted into the globale template with
        # the PyLucid context middleware pylucid_plugin.extrahead.context_middleware
        return response_content






def user_message_or_warn(msg):
    """ Display a message with user.message_set.create if available or use warnings.warn """
    user = ThreadLocal.get_current_user()
    if user and isinstance(user, User):
        user.message_set.create(message=msg)
    else:
        warnings.warn(msg)


def page_msg_or_warn(msg):
    """ Display a message with request.page_msg if available or use warnings.warn """
    request = ThreadLocal.get_current_request()
    if request:
        request.page_msg(msg)
    else:
        warnings.warn(msg)