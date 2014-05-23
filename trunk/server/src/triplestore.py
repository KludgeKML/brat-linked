'''
Uploads annotation RDF files to a triplestore.

Author:     Keith M Lawrence    <keith@kludge.co.uk>
Version:    2014-05-23
'''

store_url = 'http://localhost:8000/update/'
store_update_param = 'update'

from os.path import join as path_join

import requests

from document import real_directory
from message import Messager
from rdfIO import get_rdf_parts

def upload_annotation(document, collection, extension):
    directory = collection
    real_dir = real_directory(directory)
    fname = '%s.%s' % (document, extension)
    fpath = path_join(real_dir, fname)

    parts = get_rdf_parts(fpath)
    sparql = ''
    
    for prefix in parts['prefixes']:
        sparql += 'PREFIX ' + prefix + ' '
    sparql += ' INSERT DATA { ' + parts['data'] + ' } '
    
    insertData = { store_update_param: sparql }
    
    response = requests.post(store_url,data=insertData)
    
    if response.status_code == 200:
		Messager.info('Uploaded data to triplestore')
    else:
		Messager.error('Failed to upload to triplestore')

