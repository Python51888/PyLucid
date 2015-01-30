import os
import sys
import shutil

import click
import random


SRC_PROJECT_NAME="example_project"


def _check_activated_virtualenv():
    """precheck if we in a activated virtualenv, but should never happen ;)"""
    if not hasattr(sys, 'real_prefix'):
        click.echo("", err=True)
        click.echo("Error: It seems that we are not running in a activated virtualenv!", err=True)
        click.echo("", err=True)
        click.echo("Please activate your environment first, e.g:", err=True)
        click.echo("\t...my_env$ source bin/activate", err=True)
        click.echo("", err=True)
        click.Abort()
    else:
        click.echo("Activated virtualenv detected: %r (%s)" % (sys.prefix, sys.executable))


def _check_destination(dest, remove):
    if not dest:
        raise click.BadParameter("Path needed!", err=True)

    dest = os.path.normpath(os.path.abspath(os.path.expanduser(dest)))

    if os.path.isdir(dest):
        if remove:
            click.confirm("Delete %r before copy?" % dest, abort=True)
            click.echo("remove tree %r" % dest)
            shutil.rmtree(dest)
        else:
            raise click.BadParameter("ERROR: Destination %r exist!" % dest, err=True)

    return dest


def _copytree(dest):
    src_base = os.path.abspath(os.path.dirname(__file__))
    src = os.path.join(src_base, "page_instance_template")
    click.echo("copytree %r to %r" % (src, dest))
    shutil.copytree(src, dest)


def _patch_shebang(dest, *filepath):
    filepath = os.path.join(dest, *filepath)
    click.echo("Update shebang in %r" % filepath)

    with open(filepath, "r+") as f:
        content = f.read()
        f.seek(0)

        new_content=content.replace("#!/usr/bin/env python", "#!%s" % sys.executable)

        if new_content == content:
            click.echo("WARNING: Shebang not updated in %r!" % filepath, err=True)
        else:
            f.write(new_content)

def _mass_replace(replace_dict, files):
    for filepath in files:
        click.echo("Update filecontent %r" % filepath)
        with open(filepath, "r+") as f:
            content = f.read()

            old_content = content
            for old, new in replace_dict.items():
                if old not in content:
                    click.echo("WARNING: String %r not found!" % old, err=True)
                else:
                    content=content.replace(old, new)

            if content == old_content:
                click.echo("WARNING: File content not changed?!?", err=True)
            else:
                f.seek(0)
                f.truncate()
                f.write(content)



def _rename_project(dest, name):
    src = os.path.join(dest, SRC_PROJECT_NAME)
    dst = os.path.join(dest, name)
    click.echo("Rename %r to %r" % (src, dst))
    os.rename(src, dst)



@click.command()
@click.option("dest", '--dest', type=click.Path(),
    prompt="The destionation path for new page instance (You can use --dest=...)",
    help="Destination path for new page instance."
)
@click.option("name", '--name',
    prompt="The name of you project (You can use --name=...)",
    help="Project name (No whitespace!)"
)
@click.option("--remove", is_flag=True,
    help="Delete **all** existing files in destination before copy?",
)
def cli(dest, name, remove):
    _check_activated_virtualenv()

    click.echo("Create page instance here: %r" % dest)
    dest = _check_destination(dest, remove)

    _copytree(dest)

    _rename_project(dest, name)

    _mass_replace(
        {
            "#!/usr/bin/env python": "#!%s" % sys.executable,
            SRC_PROJECT_NAME: name,
        },
        [
            os.path.join(dest, "manage.py"),
            os.path.join(dest, name, "wsgi.py"),
        ]
    )

    secret_key = ''.join(
        [random.choice('abcdefghijklmnopqrstuvwxyz0123456789!@#$%^&*(-_=+)') for i in range(64)]
    )
    _mass_replace(
        {
            SRC_PROJECT_NAME: name,
            'SECRET_KEY = ""': 'SECRET_KEY = "%s"' % secret_key,
        },
        [
            os.path.join(dest, name, "settings.py"),
        ]
    )

    click.echo("Page instance created here: %r" % dest)
    click.echo("Please change settings,templates etc. for you needs!")