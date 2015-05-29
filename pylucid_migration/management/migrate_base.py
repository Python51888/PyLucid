# coding: utf-8

"""
    Create pages for djangocms-blog
    ~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

    :copyleft: 2015 by the PyLucid team, see AUTHORS for more details.
    :created: 2015 by JensDiemer.de
    :license: GNU GPL v3 or above, see LICENSE for more details.
"""

from __future__ import unicode_literals

import sys
import logging
from optparse import make_option
import datetime
import time
import atexit

from django.contrib.auth.models import User, Group
from django.db import transaction
from django.contrib.sites.models import Site
from django.utils.translation import ugettext as _
from django.utils.translation import activate
from django.conf import settings
from django.core.management.base import BaseCommand

from pylucid_migration.models import DjangoSite
from pylucid_migration.utils import human_duration

MIGRATE_ALL_SITES = "ALL"


def site_option(option, opt, value, parser):
    """
    optparse callback for: --sites
    """
    if not value:
        value = settings.SITE_ID
    else:
        value = value.strip()
        if value.upper() == MIGRATE_ALL_SITES.upper():
            value = MIGRATE_ALL_SITES
        else:
            value = [int(id) for id in value.split(',')]

    setattr(parser.values, option.dest, value)

ESC_CLEAR = "\x1b[K"

class StatusLine(object):
    """
    Simple helper to display process information.
    Will only work under Linux!
    """
    def __init__(self, total_count=None):
        self.total_count=total_count

    def __enter__(self):
        self.start_time = time.time()
        return self

    def write(self, no, txt):
        elapsed = time.time() - self.start_time
        estimated = elapsed / no * self.total_count
        remain = estimated-elapsed

        time_info = human_duration(remain)

        txt = "[%i/%i %s] %s" % (no, self.total_count, time_info, txt)
        print('\r%s%s' % (ESC_CLEAR, txt), end='', flush=True)

    def __exit__(self, exc_type, exc_val, exc_tb):
        print()
        duration = time.time() - self.start_time
        print("process duration: %.2fsec." % duration)


class TeeOutput(object):
    """
    redirect output to logfile and origin stdout
    e.g.:
        sys.stderr = TeeOutput(sys.stderr, self.my_logger.error)
    """
    def __init__(self, origin, logger, level):
        self.origin = origin
        self.logger = logger
        self.level = level

    def write(self, txt):
        txt2 = txt.strip("\r\n")
        if not txt2.startswith(ESC_CLEAR): # don't log status prints
            txt2 = txt2.rstrip() # don't log emtpy lines
            if txt2:
                for line in txt2.splitlines():
                    self.logger.log(self.level, line)

        self.origin.write(txt)
        self.origin.flush()

    def flush(self):
        for handler in self.logger.handlers:
            handler.flush()
        self.origin.flush()



class MigrateBaseCommand(BaseCommand):
    option_list = BaseCommand.option_list + (
        make_option('--inline_script',
            action='store_true',
            dest='inline_script',
            default=False,
            help='Move inline javascript into "html" markup entry.'
        ),
        make_option('--sites', dest="sites", type='string', action='callback',
            callback=site_option, default=None,
            help=(
                "Which SITE_ID should be migrated?"
                " If not set: Only the current settings.SITE_ID will be migrated."
                " Use a comma separated list of SITE_IDs."
                " Use '%s' for all existing sites."
            ) % MIGRATE_ALL_SITES
        ),
        make_option('--site_info',
            action='store_true',
            dest='site_info',
            default=False,
            help='Print a list of all existing sites and quit.'
        ),
        make_option('--no_logfile',
            action='store_true',
            dest='no_logfile',
            default=False,
            help="Don't log into a file: Print all messages to stdout",
        ),
    )

    def _site_info(self):
        self.stdout.write("\nList of old SITE_ID entries:")
        for site in DjangoSite.objects.all():
            self.stdout.write("\tID: %i - name: %r - domain: %r" % (site.pk, site.name, site.domain))

    def _migrate_sites(self, options):
        sites = []

        self.stdout.write("\nMigrate Sites (%s):" % repr(options["sites"]))
        
        if not options["sites"]:
            old_sites = DjangoSite.objects.all().filter(pk=settings.SITE_ID)
        elif options["sites"] == MIGRATE_ALL_SITES:
            old_sites = DjangoSite.objects.all()
        else:
            old_sites = DjangoSite.objects.all().filter(pk__in=options["sites"])

        for site_old in old_sites:
            try:
                site_new = Site.objects.get(pk=site_old.pk)
            except Site.DoesNotExist:
                site_new = Site.objects.create(
                    pk=site_old.pk,
                    domain=site_old.domain,
                    name=site_old.name,
                )
                self.stdout.write("\tNew site %r with ID %i created." % (site_new.name, site_new.id))
            else:
                self.stdout.write("\tSite %r with ID %i exists, ok." % (site_new.name, site_new.id))

            sites.append(site_new)

        return sites

    def _migrate_user(self, options):
        self.stdout.write("\nMigrate users:")
        for user in User.objects.using("legacy").all():
            self.stdout.write("\tUser: %s" % user.username)
            user.pk = None
            user.save(using="default")

    def _migrate_group(self, options):
        self.stdout.write("\nMigrate user group:")
        for group in Group.objects.using("legacy").all():
            self.stdout.write("\tGroup: %s" % group.name)
            group.pk = None
            group.save(using="default")

    def run_from_argv(self, argv):
        sys.stdout.flush()
        sys.stderr.flush()

        self.file_log=logging.getLogger(name="PyLucidMigration")

        if "--no_logfile" in argv:
            # All output to stdout/stderr
            self.file_log.addHandler(logging.StreamHandler())
            return super(MigrateBaseCommand, self).run_from_argv(argv)

        logging.lastResort=None

        self.logfilename="%s-PyLucidMigration.log" % datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M:%S")
        # self.logfilename="%s-PyLucidMigration.log" % datetime.datetime.utcnow().strftime("%Y%m%d-%H:%M")
        # self.logfilename="%s-PyLucidMigration.log" % datetime.datetime.utcnow().strftime("%Y%m%d-%H")
        # self.logfilename="%s-PyLucidMigration.log" % datetime.datetime.utcnow().strftime("%Y%m%d")
        handler = logging.FileHandler(self.logfilename, mode="a", encoding="utf8")
        # handler = logging.FileHandler(self.logfilename, mode="w", encoding="utf8")
        handler.setFormatter(logging.Formatter("%(asctime)s %(levelname)-6s %(message)s"))
        self.file_log.addHandler(handler)

        print("\nLog into %r" % self.logfilename)
        self.file_log.debug("_"*79)
        self.file_log.debug("Start logging for: %r" % " ".join(sys.argv))

        sys.stderr = TeeOutput(sys.stderr, self.file_log, level=logging.ERROR)
        sys.stdout = TeeOutput(sys.stdout, self.file_log, level=logging.INFO)

        try:
            super(MigrateBaseCommand, self).run_from_argv(argv)
        except Exception:
            import traceback
            traceback.print_exc()

        self.goodbye()

    def handle(self, *args, **options):
        if options["site_info"]:
            self._site_info()
            sys.exit()

        # print("print ok?!?")
        # sys.stderr.write("stderr write test!")
        # raise RuntimeError("Test file logging!")

        self.sites = self._migrate_sites(options)

        self._migrate_user(options)
        self._migrate_group(options)

        # TODO: Migrate User-Profile data

    def goodbye(self):
        sys.stdout.flush()
        sys.stderr.flush()
        print("\nPlease look into log file: %r" % self.logfilename)
        logging.shutdown()