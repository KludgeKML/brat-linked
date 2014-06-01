'''
Uploads annotation RDF files to a triplestore.

Author:     Keith M Lawrence    <keith@kludge.co.uk>
Version:    2014-05-23
'''

store_url = 'http://localhost:8000/update/'
store_update_param = 'update'

from os.path import join as path_join
from session import get_session

import requests

from document import real_directory
from message import Messager
from rdfIO import get_rdf_parts

def upload_annotation(document, collection):
    '''Uploads an annotation into a triplestore.
    
    The triplestore URL is specified by the module's store_url variable,
    and the function assumes that INSERT DATA statements can be sent to 
    that url with a POST http command, using the parameter name supplied 
    in the module's store_update_param variable. This function is called
    from the dispatcher when an AJAX 'uploadAnnotation' call comes in.
    '''
    directory = collection
    real_dir = real_directory(directory)
    fname = '%s.%s' % (document, 'ann')
    fpath = path_join(real_dir, fname)
    user = get_session()['user']

    parts = get_rdf_parts(fpath, document)
    sparql = ''
    
    for prefix in parts['prefixes']:
        sparql += 'PREFIX ' + prefix + ' '
    sparql += ' INSERT DATA { GRAPH ' + user + '{ ' + parts['data'] + ' }} '
    
    insertData = { store_update_param: sparql }
    
    response = requests.post(store_url,data=insertData)
    
    if response.status_code == 200:
		Messager.info('Uploaded data to triplestore')
    else:
		Messager.error('Failed to upload to triplestore (Response ' + response.status_code + ' ' + response.reason + ')')
		
    return {}

