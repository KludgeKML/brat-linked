#!/usr/bin/env python

import json
import os
import re
import requests
import sys

try:
    from config import DATA_DIR
except ImportError:
    import os.path
    from sys import path as sys_path
    # Guessing that we might be in the brat tools/ directory ...
    sys_path.append(os.path.join(os.path.dirname(__file__), '..'))
    sys_path.append(os.path.join(os.path.dirname(__file__), '../server/src'))
    from config import DATA_DIR
    from normdb import get_norm_type_by_id, data_by_id, get_linked_global_entity

# Recursively upload a directory of .ann files to the triplestore

def upload_annotations ( endpoint, directory ):
    for dir_path, dirs, files in os.walk(directory):
        for dir in dirs:
            upload_annotations(endpoint, os.path.join(dir_path, dir))
        for file in files:
            document, extension = os.path.splitext(file)
            path, user = os.path.split(dir_path)
            if extension == '.ann':
                rdf_data, data_exists = convert_to_rdf(os.path.join(dir_path, file), document, user)
                if data_exists:
                    namespace_info = load_namespace_info()
                    full_endpoint = endpoint + \
                        namespace_info['base_url'] + 'user/' + user + '/' + document
                    print("uploading to " + full_endpoint)
                    print(rdf_data)
                    upload_annotation(full_endpoint, rdf_data)

def upload_annotation ( endpoint, rdf_data ):
    headers = {'content-type' : 'application/x-turtle'}
    response = requests.put(endpoint, headers=headers, data=rdf_data)

    if response.status_code != 201 and response.status_code != 200:
        print ('Failed to upload to triplestore (Response ' +
            str(response.status_code) + ' ' + response.reason + ')')

def load_namespace_info():
    '''Reads namespace variables from JSON file.

    Ultimately this file will be cached from a site specified in
    an environment variable. For now, it's just on disk.
    '''

    fpath = os.path.join(DATA_DIR, 'Narrative', 'ontomedia-data.json')
    namespace_file = open(fpath, 'r')
    namespace_info = json.load(namespace_file)
    namespace_file.close()

    return namespace_info

def convert_to_rdf(fpath, document, user):
    '''Returns a turtle file of the annotations.

    The annotations to the current file, as well as the prefixes required
    to insert them into a graph, are returned as a file. This function is
    designed to be called from the dispatcher.
    '''

    parts = get_rdf_parts(fpath, document, user)
    rdf = ''

    for prefix in parts['prefixes']:
        rdf += '@prefix ' + prefix + '.\n'
    rdf += '\n' + parts['data']
    data_exists = False
    if len(parts['data']) > 0:
        data_exists = True

    return rdf, data_exists


def get_rdf_parts(fpath, document, user):

    parts = {'prefixes': [], 'data': ''}

    namespace_info = load_namespace_info()

    doc_name = document.rpartition('/')[2]

    namespace = namespace_info['base_namespace'] + user + '/' + doc_name + '/'

    for prefix, url in namespace_info['namespaces'].items():
        parts['prefixes'].append(prefix + ': <' + url + '>')

    with open(fpath) as txt_file:
        entity_data = {}
        global_data = {}
        global_links = {}
        default_context_uri = ''


#        for line in txt_file:
#            chunks = re.split(r'\s+', line.strip())
#
#            for global_class, global_property in namespace_info['global_classes'].items():
#
#                if chunks[1] == global_class and not(global_class in context_data):
#                    global_data[chunks[0]] = "<" + namespace + chunks[0] + ">"
#
#                if chunks[1] == global_property:
#                    arg1 = chunks[2].split(":")[1]
#                    arg2 = chunks[3].split(":")[1]
#
#                    rel = {global_property:arg2}
#
#                    global_links[arg1] = [rel]
#
#                if chunks[1] == "Default" and chunks[2] in global_data:
#                    default_context_uri = "<" + namespace + chunks[2] + ">"
#
#        if default_context_uri == '' and len(global_data) == 1:
#            default_context_uri = global_data.values()[0]


        for line in txt_file:

            chunks = re.split(r'\s+', line.strip())

            if line[0] == 'E':

                event = chunks[1]

                event_id = event.split(':')[1]
                event_type = event.split(':')[0]

                parts['data'] += "<" + namespace + event_id + ">\n\ta "

                if lookup(event_type, namespace_info) != False:
                    parts['data'] += lookup(event_type, namespace_info) + ";\n"

                for chunk in chunks[2:]:
                    if ':' in chunk and lookup(chunk.split(':')[0], namespace_info) != False:
                        parts['data'] += "\t" + lookup(chunk.split(':')[0], namespace_info) + " <" + namespace + chunk.split(':')[1] + ">;\n"
                    elif ':' in chunk:
                        parts['data'] += "\t" + get_long_rdf(chunk.split(':')[0], namespace_info, namespace + chunk.split(':')[1]) + ";\n"

                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'

            elif line[0] == 'N':

                normalised = chunks[3].split(':', 1)[1]
                dbname = chunks[3].split(':', 1)[0]

                if get_norm_type_by_id(dbname, normalised) == 'global':
                    # If link is directly to global entity then need to create local entity for sameAs
                    # and the link to global entity with shadow-of relationship

                    entity_name = normalised.split('/')[-1]

                    parts['data'] += "<" + namespace + entity_name + "> ome:shadow-of <" + normalised + ">.\n\n"

                    parts['data'] += "<" + namespace + chunks[2] + "> owl:sameAs <" + namespace + entity_name + ">;\n"

                    if normalised not in entity_data:
                        entity_data[normalised] = data_by_id(dbname, normalised)

                else:

                    parts['data'] += "<" + namespace + chunks[2] + "> owl:sameAs <" + normalised + ">"
                    # Check if local entity is linked to global entity - if so add in shadow-of relationship

                    global_id = get_linked_global_entity(dbname, normalised)

                    if len(global_id) < 1:
                        parts['data'] += ";\n\n"
                    else:
                        parts['data'] += ".\n\n"

                        for uid in global_id:
                            parts['data'] += "<" + normalised + "> ome:shadow-of <" + uid + ">;\n"

                        if uid not in entity_data:
                            entity_data[uid] = data_by_id(dbname, uid)

                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'


            elif line[0] == 'R':

                parts['data'] += "<" + namespace + chunks[2].split(":")[1] + "> "

                if lookup(chunks[1], namespace_info) != False:
                    parts['data'] += lookup(chunks[1], namespace_info) + " " + "<" + namespace + chunks[3].split(":")[1] + ">;\n"
                else:
                    parts['data'] += get_long_rdf(chunks[1], namespace_info,'', chunks[3].split(":")[1], namespace)

                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'

            elif line[0] == 'T':
                line_string = " ".join(chunks[4:])

                parts['data'] += "<" + namespace + chunks[0] + ">\n\ta "
                if lookup(chunks[1], namespace_info) != False:
                    parts['data'] += lookup(chunks[1], namespace_info)


                if line_string.strip() != '':
                    line_string = line_string.replace('"', '\\"')
                    parts['data'] += " ;\n"
                    parts['data'] += '\tcnt:chars "' + line_string.strip() + '" .\n\n'
                else:
                    parts['data'] += " .\n\n"


            elif line[0] == 'A' and len(chunks) > 3:

                get_lookup = lookup(chunks[1], namespace_info)

                if (get_lookup == chunks[1]):
                    get_lookup = 'a ' + lookup(chunks[3], namespace_info)
                elif (get_lookup == False):
                    get_lookup = get_long_rdf(chunks[1], namespace_info, chunks[3:])
                else:
                    get_lookup = 'a ' + get_lookup


                parts['data'] += "<" + namespace + chunks[2] + ">\n\t " + get_lookup + ";\n"
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'

        if len(entity_data) > 0:

            #for row in entity_data:
            for key, value in entity_data.iteritems():

                parts['data'] += "<" + key + ">\n"

                for data in value:
                    for data_tuple in data:
                        if data_tuple[0] == 'Name':
                            parts['data'] += '\trdfs:label "' + data_tuple[1] + '";\n'
                        elif data_tuple[0] == 'Category':
                            parts['data'] += '\ta ' + lookup(data_tuple[1], namespace_info) + ' .\n\n'

    return parts


def lookup(annotation, namespace_info):

    #conversion = {}

    #if annotation in conversion:
    #    annotation = conversion[annotation]

    annotation = re.sub(r'[^a-zA-Z_-]+', '', annotation)

    if annotation in namespace_info['namespaces']:
        return namespace_info['namespaces'][annotation]
    elif annotation in namespace_info['category_map']:
        return namespace_info['category_map'][annotation] + ":" + annotation
    elif annotation in namespace_info['relationship_map']:
        return namespace_info['relationship_map'][annotation] + ":" + annotation
    elif annotation in namespace_info['extended_rdf_map']:
        return False
    elif annotation in namespace_info['string_literals']:
        return False
    elif annotation in namespace_info['class_literals']:
        return False

    return annotation


def get_long_rdf(annotation, namespace_info, annotation_value = '', entity = '', namespace = ''):
    ent = ''
    if entity == '' and hasattr(annotation_value, 'lower'):
        ent = annotation_value.strip()
    elif entity == '':
        ent = (' '.join(annotation_value)).strip()
    elif re.sub(r'[^a-zA-Z_-]+', '', entity) in namespace_info['category_map']:
        stripped_entity = re.sub(r'[^a-zA-Z_-]+', '', entity)
        ent = namespace_info['category_map'][stripped_entity] + ":" + stripped_entity
    else:
        ent = "<" + namespace + re.sub(r'[^a-zA-Z0-9_-]+', '', entity) + ">"


    annotation = re.sub(r'[^a-zA-Z_-]+', '', annotation)

    if annotation in namespace_info['extended_rdf_map']:
        raw = namespace_info['extended_rdf_map'][annotation]
        return raw.replace('{1}', ent)
    elif annotation in namespace_info['string_literals']:
        raw = namespace_info['string_literals'][annotation]
        return raw.replace('{1}', ent)
    elif annotation in namespace_info['class_literals']:
        raw = namespace_info['class_literals'][annotation]
        filtered_ent = re.sub(r'[^a-zA-Z0-9_ -]+', '', ent)
        camelcase_ent = filtered_ent.title()
        return raw.replace('{1}', camelcase_ent.replace(' ', ''))

    return annotation + " " + ent


def main(argv=None):
    if argv is None:
        argv = sys.argv

    if len(argv) < 3:
        print >> sys.stderr, 'Usage:', argv[0], 'TRIPLESTORE_ENDPOINT DIRECTORY'
        return 1

    upload_annotations(argv[1], argv[2])

    return 0

if __name__ == '__main__':
    sys.exit(main(sys.argv))