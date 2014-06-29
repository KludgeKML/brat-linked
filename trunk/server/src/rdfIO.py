#!/usr/bin/env python

import re
import json

from os.path import join as path_join

from annotation import open_textfile
from config import DATA_DIR
from document import real_directory
from session import get_session
from normdb import get_norm_type_by_id, get_linked_global_entity, get_linked_local_entity, data_by_id

def load_namespace_info():
    '''Reads namespace variables from JSON file.

    Ultimately this file will be cached from a site specified in 
    an environment variable. For now, it's just on disk.
    '''

    data_dir = real_directory(directory, DATA_DIR)
    fpath = path_join(data_dir, 'Narrative', 'ontomedia-data.json')
    namespace_file = open(fpath, 'r')
    namespace_info = json.load(namespace_file)
    namespace_file.close()

    return namespace_info


def convert_to_rdf(fpath, document):
    '''Returns a turtle file of the annotations.
    
    The annotations to the current file, as well as the prefixes required
    to insert them into a graph, are returned as a file. This function is
    designed to be called from the dispatcher.
    '''
    parts = get_rdf_parts(fpath, document);
    rdf = ''

    for prefix in parts['prefixes']:
        rdf += '@prefix ' + prefix + '.\n'
    rdf += '\n' + parts['data']

    return rdf


def get_rdf_parts(fpath, document):
    
    user = get_session()['user']
    parts = { 'prefixes': [], 'data': '' }

    namespace_info = load_namespace_info()
    
    namespace = namespace_info['base_namespace'] + user + '/' + document + '/'
    
    for prefix, url in namespace_info['namespaces'].items():
        parts['prefixes'].append(prefix + ': <' + url + '>')

    with open(fpath) as txt_file:
        for line in txt_file:

            chunks = re.split(r'\s+', line)
            
            if line[0] == 'E':
        
                Event = chunks[1]
            
                EventID = Event.split(':')[1]
                EventType = Event.split(':')[0]
            
                parts['data'] += "<" + namespace + EventID + ">\n\ta "
                
                if lookup(EventType, namespace_info) != False:
                    parts['data'] += lookup(EventType, namespace_info) + ";\n"
            
                for chunk in chunks[2:]:
                    if ':' in chunk:
                        parts['data'] += "\t" + lookup(chunk.split(':')[0], namespace_info) + " <" + namespace + chunk.split(':')[1] + ">;\n"
                
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'
                
            elif line[0] == 'N': 
                
                normalised = chunks[3].split(':', 1)[1]
                dbname = chunks[3].split(':', 1)[0]
                
                entity_data = []
                
                if get_norm_type_by_id(dbname, normalised) == 'global':
                    # If link is directly to global entity then need to create local entity for sameAs
                    # and the link to global entity with shadow-of relationship
                    
                    entity_name = normalised.split('/')[-1]
                
                    parts['data'] += "<" + namespace + chunks[2] + "> owl:sameAs <" + namespace + entity_name + ">;\n"
                    parts['data'] += "<" + namespace + entity_name + "> ome:shadow-of <" + normalised + ">;\n"
                    
                    entity_data.append({normalised:data_by_id(dbname, normalised)})
                
                else:
                
                    parts['data'] += "<" + namespace + chunks[2] + "> owl:sameAs <" + normalised + ">;\n"
                    # Check if local entity is linked to global entity - if so add in shadow-of relationship
                    
                    global_id = get_linked_global_entity(dbname, normalised)
                    
                    for uid in global_id:
                        parts['data'] += "<" + normalised + "> ome:shadow-of <" + uid + ">;\n"
                        entity_data.append({uid:data_by_id(dbname, uid)})
                
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'
                
                
                if len(entity_data) > 0:
                
                    for row in entity_data:
                        for key, value in row.iteritems():
                    
                            parts['data'] += "<" + key + ">\n"
                        
                            for data in value:
                                for tuple in data:
                                    if tuple[0] == 'Name':
                                        parts['data'] += '\trdfs:label "' + tuple[1] + '";\n'
                                    elif tuple[0] == 'Category':
                                        parts['data'] += '\ta ' + lookup(tuple[1], namespace_info) + ' .\n\n'
                
           
            elif line[0] == 'R':
                
                parts['data'] += "<" + namespace + chunks[2].split(":")[1] + "> "
                    
                if lookup(chunks[1], namespace_info) != False:
                    parts['data'] += lookup(chunks[1], namespace_info) + " " + "<" + namespace + chunks[3].split(":")[1] + ">;\n" 
                else:
                    parts['data'] += get_long_rdf(chunks[1], chunks[3].split(":")[1], namespace, namespace_info)
                
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'
            
            elif line[0] == 'T':
                line_string = " ".join(chunks[4:])
            
                parts['data'] += "<" + namespace + chunks[0] + ">\n\ta "
                if lookup(chunks[1], namespace_info) != False:
                    parts['data'] += lookup(chunks[1], namespace_info)
                parts['data'] += " ;\n"
                parts['data'] += '\tcnt:chars "' + line_string.strip() + '" .\n\n'
            
            elif line[0] == 'A':
                parts['data'] += "<" + namespace + chunks[2] + ">\n\ta " + lookup(chunks[3], namespace_info) + ";\n"    
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'     
           
    return parts


def lookup(annotation, namespace_info):

    #conversion = {}
    
    #if annotation in conversion:
    #    annotation = conversion[annotation]

    if annotation in namespace_info['namespaces']:
        return namespace_info['namespaces'][annotation]
    elif annotation in namespace_info['category_map']:
        return namespace_info['category_map'][annotation] + ":" + annotation
    elif annotation in namespace_info['relationship_map']:
        return namespace_info['relationship_map'][annotation] + ":" + annotation
    elif annotation in namespace_info['extended_rdf_map']:
        return False
    return annotation


def get_long_rdf(annotation, entity, namespace, namespace_info):
    ent = ''    
    if entity in namespace_info['category_map']:
        ent = namespace_info['category_map'][entity] + ":" + entity
    else:
        ent = "<" + namespace + entity + ">"

    if annotation in namespace_info['extended_rdf_map']:
        raw = namespace_info['extended_rdf_map'][annotation]
        return raw.replace('{1}', ent)

    return annotation + " " + ent
