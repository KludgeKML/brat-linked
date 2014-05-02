'''
Serves annotation related files for downloads.

Author:     Pontus Stenetorp    <pontus stenetorp se>
Version:    2011-10-03
'''

from __future__ import with_statement

from os import close as os_close, remove
from os.path import join as path_join, dirname, basename, normpath
from tempfile import mkstemp

from document import real_directory
from annotation import open_textfile
from common import NoPrintJSONError
from subprocess import Popen

from rdfIO import convert_to_rdf

try:
    from cStringIO import StringIO
except ImportError:
    from StringIO import StringIO

def download_file(document, collection, extension):
    directory = collection
    real_dir = real_directory(directory)
    fname = '%s.%s' % (document, extension)
    fpath = path_join(real_dir, fname)

    hdrs = [('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Disposition',
                'inline; filename=%s' % fname)]
    with open_textfile(fpath, 'r') as txt_file:
        data = txt_file.read().encode('utf-8')
    raise NoPrintJSONError(hdrs, data)
    
def download_rdf(document, collection, extension):
    directory = collection
    real_dir = real_directory(directory)
    fname = '%s.%s' % (document, extension)
    fpath = path_join(real_dir, fname)

    hdrs = [('Content-Type', 'text/plain; charset=utf-8'),
            ('Content-Disposition',
                'inline; filename=%s' % fname)]
    #with open_textfile(fpath, 'r') as txt_file:
    #   data = txt_file.read().encode('utf-8')
    
    data = convert_to_rdf(fpath)
    raise NoPrintJSONError(hdrs, data)    

def find_in_directory_tree(directory, filename):
    # TODO: DRY; partial dup of projectconfig.py:__read_first_in_directory_tree
    try:
        from config import BASE_DIR
    except ImportError:
        BASE_DIR = "/"
    from os.path import split, join, exists

    depth = 0
    directory, BASE_DIR = normpath(directory), normpath(BASE_DIR)
    while BASE_DIR in directory:
        if exists(join(directory, filename)):
            return (directory, depth)
        directory = split(directory)[0]
        depth += 1
    return (None, None)

def download_collection(collection, include_conf=False):
    directory = collection
    real_dir = real_directory(directory)
    dir_name = basename(dirname(real_dir))
    fname = '%s.%s' % (dir_name, 'tar.gz')

    confs = ['annotation.conf', 'visual.conf', 'tools.conf',
             'kb_shortcuts.conf']

    try:
        include_conf = int(include_conf)
    except ValueError:
        pass

    tmp_file_path = None
    try:
        tmp_file_fh, tmp_file_path = mkstemp()
        os_close(tmp_file_fh)

        tar_cmd_split = ['tar', '--exclude=.stats_cache']
        conf_names = []
        if not include_conf:
            tar_cmd_split.extend(['--exclude=%s' % c for c in confs])
        else:
            # also include configs from parent directories.
            for cname in confs:
                cdir, depth = find_in_directory_tree(real_dir, cname)
                if depth is not None and depth > 0:
                    relpath = path_join(dir_name, *['..' for _ in range(depth)])
                    conf_names.append(path_join(relpath, cname))
            if conf_names:
                # replace pathname components ending in ".." with target
                # directory name so that .confs in parent directories appear
                # in the target directory in the tar.
                tar_cmd_split.extend(['--absolute-names', '--transform',
                                      's|.*\\.\\.|%s|' %dir_name])

        tar_cmd_split.extend(['-c', '-z', '-f', tmp_file_path, dir_name])
        tar_cmd_split.extend(conf_names)
        tar_p = Popen(tar_cmd_split, cwd=path_join(real_dir, '..'))
        tar_p.wait()

        hdrs = [('Content-Type', 'application/octet-stream'), #'application/x-tgz'),
                ('Content-Disposition', 'inline; filename=%s' % fname)]
        with open(tmp_file_path, 'rb') as tmp_file:
            tar_data = tmp_file.read()

        raise NoPrintJSONError(hdrs, tar_data)
    finally:
        if tmp_file_path is not None:
            remove(tmp_file_path)
