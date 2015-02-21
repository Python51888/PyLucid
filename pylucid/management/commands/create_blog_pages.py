# coding: utf-8

"""
    Create pages for djangocms-blog
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2015 by the PyLucid team, see AUTHORS for more details.
    :created: 2015 by JensDiemer.de
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from django.utils.translation import ugettext as _
from django.utils.translation import activate
from django.conf import settings

from django.core.management.base import BaseCommand

from cms.models import Placeholder
from cms.api import create_page, create_title, add_plugin

from cms.utils.i18n import get_language_list, get_default_language


class Command(BaseCommand):
    help = 'Create pages for djangocms-blog'

    def handle(self, *args, **options):
        default_language= get_default_language()
        languages = get_language_list()

        activate(default_language)

        blog_digest_page = create_page(
            title=_("blog"),
            slug="blog",
            template='sidebar_left.html',
            language=settings.LANGUAGE_CODE,
            in_navigation=True,
        )

        blog_detail_app = create_page(
            title=_("blog detail"),
            template='fullwidth.html',
            language=settings.LANGUAGE_CODE,
            apphook="BlogApp",
            apphook_namespace="djangocms_blog",
            in_navigation=False,
            parent=blog_digest_page,
        )

        for language in languages:
            self.stdout.write("Create blog pages in languages: %r" % language)
            activate(language)

            if language != default_language:
                create_title(language=language, title=_("blog"), page=blog_digest_page)
                create_title(language=language, title=_("blog detail"), page=blog_detail_app)

            placeholder_content = Placeholder.objects.create(slot="content")
            placeholder_content.save()
            blog_digest_page.placeholders.add(placeholder_content)

            add_plugin(placeholder_content, "BlogLatestEntriesPlugin", language=language)

            placeholder_sidebar = Placeholder.objects.create(slot="sidebar")
            placeholder_sidebar.save()
            blog_digest_page.placeholders.add(placeholder_sidebar)

            add_plugin(placeholder_sidebar, "BlogArchivePlugin", language=language)
            add_plugin(placeholder_sidebar, "BlogAuthorPostsPlugin", language=language)
            add_plugin(placeholder_sidebar, "BlogCategoryPlugin", language=language)
            add_plugin(placeholder_sidebar, "BlogTagsPlugin", language=language)

            blog_digest_page.publish(language)
            blog_detail_app.publish(language)