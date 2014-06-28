'''
Uploads annotation RDF files to a triplestore.

Author:     Keith M Lawrence    <keith@kludge.co.uk>
Version:    2014-05-23
'''

from os.path import join as path_join
from os import environ
from session import get_session

import requests

from document import real_directory
from message import Messager
from rdfIO import get_rdf_parts

def upload_annotation(document, collection):
    '''Uploads an annotation into a triplestore.

    The triplestore endpoint path is specified by environment - it can be
    set in apache with the SetEnv directive, either in a local .htaccess
    file or in the main configuration for the brat directory. It assumes
    that the triplestore implements the 1.1 RESTFUL interface, as for
    example 4Store and Sesame are supposed to, whereby you can PUT to the
    graph to replace it. This function is called from the dispatcher when
    an AJAX 'uploadAnnotation' call comes in.
    '''
    directory = collection
    real_dir = real_directory(directory)
    fname = '%s.%s' % (document, 'ann')
    fpath = path_join(real_dir, fname)
    user = get_session()['user']

    # Get target sparql endpoint from the environment

    if 'TRIPLESTORE_RESTFUL_ENDPOINT' not in environ:
        Messager.error('No Triplestore endpoint set! (Must be set in Apache with SetEnv TRIPLESTORE_RESTFUL_ENDPOINT <url>)')
        return

    endpoint = environ['TRIPLESTORE_RESTFUL_ENDPOINT'] + 'http://contextus.net/user/' + user + '/' + document

    Messager.info('Triplestore RESTFUL Endpoint for this graph: [' + endpoint + ']')

    parts = get_rdf_parts(fpath, document)

    response = requests.put(endpoint, data=parts['data'])

    Message.info(parts['data'])

    if response.status_code == 200:
        Messager.info('Uploaded data to triplestore')
    else:
        Messager.error('Failed to upload to triplestore (Response ' + str(response.status_code) + ' ' + response.reason + ')')

    return {}

