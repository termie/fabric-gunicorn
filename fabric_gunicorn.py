# vim: tabstop=4 shiftwidth=4 softtabstop=4

# fabric-gunicorn
# Copyright: (c) 2012 Christoph Heer <Christoph.Heer@googlemail.com>
# License: BSD, see LICENSE for more details.

import time

from fabric.api import cd
from fabric.api import env
from fabric.api import run
from fabric.api import sudo
from fabric.api import task
from fabric.context_managers import hide
from fabric.utils import abort
from fabric.utils import puts


def _set_env_defaults():
    env.setdefault('gunicorn_remote_workdir', '~')
    env.setdefault('gunicorn_pidpath',
                   env.gunicorn_remote_workdir + '/gunicorn.pid')
    env.setdefault('gunicorn_bind', '127.0.0.1:8000')
    env.setdefault('gunicorn_works', 1)
    env.setdefault('gunicorn_user', None)
    env.setdefault('gunicorn_group', None)
    env.setdefault('gunicorn_worker_class', 'egg:gunicorn#sync')
    env.setdefault('gunicorn_mode', None)
    env.setdefault('gunicorn_wsgi_app', None)
    env.setdefault('gunicorn_pythonpath', None)
    env.setdefault('gunicorn_django_settings', None)
    env.setdefault('gunicorn_paster_config', None)


_set_env_defaults()


def running():
    return sudo('ls ' + env.gunicorn_pidpath, quiet=True).succeeded


def running_workers():
    count = None
    with hide('running', 'stdout', 'stderr'):
        count = sudo('ps -e -o ppid | grep `cat %s` | wc -l' %
                     env.gunicorn_pidpath)
    return count


@task
def status():
    """Show the current status of your gunicorn process"""
    if running():
        puts('gunicorn is running.')
        puts('active workers: %s' % running_workers())
    else:
        puts('gunicorn is not running.')


@task
def start():
    """Start the gunicorn process"""
    if running():
        puts('gunicorn is already running.')
        return

    mode = env.get('gunicorn_mode')
    if not mode:
        if env.get('gunicorn_paster_config'):
            mode = 'paster'
        elif env.get('gunicorn_django_settings'):
            mode = 'django'
        else:
            mode = 'wsgi'

    if mode == 'wsgi' and not env.gunicorn_wsgi_app:
        abort('env.gunicorn_wsgi_app is not defined.')

    if mode == 'django' and not env.gunicorn_django_settings:
        abort('env.gunicorn_django_settings is not defined.')

    if mode == 'paster' and not env.gunicorn_paster_config:
        abort('env.gunicorn_paster_config is not defined.')


    with cd(env.gunicorn_remote_workdir):
        #prefix = []
        #if 'virtualenv_dir' in env:
        #    prefix.append('source %s/bin/activate' % env.virtualenv_dir)
        #
        #prefix_string = ' && '.join(prefix)
        #if len(prefix_string) > 0:
        #    prefix_string += ' && '

        options = [
            '--daemon',
            '--error-logfile %s/error.log' % env.gunicorn_remote_workdir,
            '--pid %s' % env.gunicorn_pidpath,
            '--bind %s' % env.gunicorn_bind,
        ]

        for option in ('pythonpath', 'user', 'group', 'workers',
                       'worker-class'):
            attr = getattr(env, 'gunicorn_%s' % option.replace('-', '_'))
            if attr:
                options.append('--%s %s' % (option, attr))

        options_string = ' '.join(options)

        # we need to sudo if we're going to run as a specific user
        if env.gunicorn_user:
            runner = sudo
        else:
            runner = run

        # actually run the stuff
        if mode == 'paster':
            runner('gunicorn_paster %s %s'
                   % (options_string, env.gunicorn_paster_config))
        elif mode == 'django':
            runner('gunicorn_django %s %s'
                   % (options_string, env.gunicorn_django_settings), pty=False)
        elif mode == 'wsgi':
            runner('gunicorn %s %s'
                   % (options_string, env.gunicorn_wsgi_app))

        if running():
            puts('gunicorn started.')
        else:
            abort('gunicorn was not started.')


@task
def stop():
    """Stop the Gunicorn process"""
    if not running():
        puts('gunicorn is not running!')
        return

    sudo('kill `cat %s`' % (env.gunicorn_pidpath))

    for i in range(0, 5):
        puts('.', end='', show_prefix=i == 0)

        if running():
            time.sleep(1)
        else:
            puts('', show_prefix=False)
            puts('gunicorn was stopped.')
            break
    else:
        puts('gunicorn was not stopped')
        return


@task
def restart():
    """Restart hard the Gunicorn process"""
    stop()
    start()


@task
def reload():
    """Gracefully reload the Gunicorn process and the wsgi application"""
    if not running():
        puts('gunicorn is not running.')
        return
    puts('Reloading gunicorn...')
    run('kill -HUP `cat %s`' % (env.gunicorn_pidpath))


@task
def add_worker():
    """Increase the number of your Gunicorn workers"""
    if not running():
        puts('gunicorn is not running!')
        return

    puts('Increasing number of workers...')
    run('kill -TTIN `cat %s`' % (env.gunicorn_pidpath))
    puts('Active workers: %s' % running_workers())


@task
def remove_worker():
    """Decrease the number of your Gunicorn workers"""
    if not running():
        puts('gunicorn is not running!')
        return

    puts('Decreasing number of workers...')
    run('kill -TTOU `cat %s`' % (env.gunicorn_pidpath))
    puts('Active workers: %s' % running_workers())
