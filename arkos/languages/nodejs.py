import os

from arkos import logger
from arkos.utilities import shell


def install(*mods, **kwargs):
    cwd = os.getcwd()
    if "install_path" in kwargs:
        os.chdir(kwargs["install_path"])
    s = shell('npm install %s%s' % (' '.join(x for x in mods), (' --'+' --'.join(x for x in kwargs['opts']) if kwargs.has_key('opts') else '')))
    os.chdir(cwd)
    if s["code"] != 0:
        logger.error('NPM install of %s failed; log output follows:\n%s'%(' '.join(x for x in mods),s["stderr"]))
        raise Exception('NPM install failed, check logs for info')

def remove(*mods):
    s = shell('npm uninstall %s' % ' '.join(x for x in mods), stderr=True)
    if s["code"] != 0:
        logger.error('Failed to remove %s via npm; log output follows:\n%s'%(' '.join(x for x in mods),s["stderr"]))
        raise Exception('Failed to remove %s via npm, check logs for info'%' '.join(x for x in mods))

def install_from_package(path, stat='production', opts={}):
    cwd = os.getcwd()
    os.chdir(path)
    s = shell('npm install %s%s' % (' --'+stat if stat else '', ' --'+' --'.join(x+'='+opts[x] for x in opts) if opts else ''))
    os.chdir(cwd)
    if s["code"] != 0:
        logger.error('NPM install of %s failed; log output follows:\n%s'%(path,s["stderr"]))
        raise Exception('NPM install failed, check logs for info')
