#!/usr/bin/env python

import re

from annotation import open_textfile
from session import get_session
from normdb import get_norm_type_by_id, get_linked_global_entity, get_linked_local_entity

base_namespace = 'http://contextus.net/resource/RRH/'

namespaces = {'rdfs':'http://www.w3.org/2000/01/rdf-schema#','ome':'http://contextus.net/ontology/ontomedia/core/expression#', 'omt':'http://contextus.net/ontology/ontomedia/ext/common/trait#', 'omb':'http://contextus.net/ontology/ontomedia/ext/common/being#', 'omeg':'http://contextus.net/ontology/ontomedia/ext/events/gain#', 'omel':'http://contextus.net/ontology/ontomedia/ext/events/loss#', 'omet':'http://contextus.net/ontology/ontomedia/ext/events/trans#', 'omes':'http://contextus.net/ontology/ontomedia/ext/events/social#', 'omea':'http://contextus.net/ontology/ontomedia/ext/events/action#', 'omj':'http://contextus.net/ontology/ontomedia/ext/events/travel#', 'eprop':'http://contextus.net/ontology/ontomedia/ext/events/eventprop#', 'omf':'http://contextus.net/ontology/ontomedia/ext/fiction/fic#', 'owl':'http://www.w3.org/2002/07/owl#', 'cnt':'http://www.w3.org/2011/content#'}
    
category_map = {'Entity':'ome', 'Being':'ome', 'Character':'ome', 'Item':'ome', 'Abstract-Item':'ome', 'Group':'omb', 'Community':'omb', 'Household':'omb', 'Bonded-Group':'omb', 'Bonded-Pair':'omb', 'Organisation':'omb', 'Company':'omb', 'Government':'omb', 'Context':'ome', 'Physical-Item':'ome', 'Space':'ome','Event':'ome', 'Gain':'ome', 'Creation':'omeg', 'Loss':'ome', 'Destruction':'omel', 'Betrayal':'omel', 'Transformation':'ome', 'Transference':'omet', 'Division':'omet', 'Merge':'omet', 'Degradation':'omet', 'Social':'ome', 'Conversational':'omes', 'Flirtation':'omes', 'Proposition':'omes', 'Political':'omes', 'Academic':'omes', 'Legal':'omes', 'Theological':'omes', 'Philosophical':'omes', 'Action':'ome', 'Violence':'omea', 'Sex':'omea', 'Festivity':'omea', 'Ingestion':'omea', 'Celestial':'omea', 'Environmental':'omea', 'Travel':'omj', 'Describes':'omf', 'Implied':'omf', 'References-Concept':'omf', 'In-Passing':'omf', 'Vague-Description':'omf', 'Detailed-Description':'omf', 'Extremely-Detailed-Description':'omf', 'Fade-To-Black':'omf', 'Extremely-Detailed-Description':'omf', 'Spoiler':'omf', 'Key':'omf', 'Main':'omf', 'Fact':'omf', 'Nitpick':'omf', 'Nitpick':'omf', 'Consent-Given':'eprop', 'Consent-Implied':'eprop', 'Consent-Not-Given':'eprop', 'Consent-Unclear':'eprop', 'Strongly-Positive':'omes','Positive':'omes','Neutral':'omes','Negative':'omes','Strongly-Negative':'omes'}

    
relationship_map = {'is-linked-to':'ome', 'is':'ome', 'is-shadow-of':'ome', 'contains':'ome', 'contained-by':'ome', 'has-subject-entity':'ome', 'has-object-entity':'ome', 'has-subject':'omes', 'to':'ome', 'from':'ome'}
    
extended_rdf_map = {'bond-with':'omt:has-trait [\n\ta omt:link ;\n\t\tomb:has-bond [\n\t\t\ta omb:Bond;\n\t\t\tome:is-linked-to {1}]\n\t\t];\n', 'family-of':'omt:has-trait [\n\ta omt:link ;\n\t\tomb:has-bond [\n\t\t\ta omb:Family;\n\t\t\tomb:is-relation-of {1}]\n\t\t];\n', 'friend-of':'omt:has-trait [\n\ta omt:link ;\n\t\tomb:has-bond [\n\t\t\ta omb:Friendship;\n\t\t\tome:is-linked-to {1}]\n\t\t];\n', 'enemy-of':'omt:has-trait [\n\ta omt:link ;\n\t\tomb:has-bond [\n\t\t\ta omb:Enmity;\n\t\t\tomb:is-linked-to {1}]\n\t\t];\n'}

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
    
    namespace = base_namespace + user + '/' + document + '/'
    
    for prefix, url in namespaces.items():
        parts['prefixes'].append(prefix + ': <' + url + '>')

    with open(fpath) as txt_file:
        for line in txt_file:

            chunks = re.split(r'\s+', line)
            
            if line[0] == 'E':
        
                Event = chunks[1]
            
                EventID = Event.split(':')[1]
                EventType = Event.split(':')[0]
            
                parts['data'] += "<" + namespace + EventID + ">\n\ta "
                
                if lookup(EventType) != False:
                    parts['data'] += lookup(EventType) + ";\n"
            
                for chunk in chunks[2:]:
                    if ':' in chunk:
                        parts['data'] += "\t" + lookup(chunk.split(':')[0]) + " <" + namespace + chunk.split(':')[1] + ">;\n"
                
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'
                
            elif line[0] == 'N': 
                
                normalised = chunks[3].split(':', 1)[1]
                dbname = chunks[3].split(':', 1)[0]
                
                if get_norm_type_by_id(dbname, normalised) == 'global':
                    # If link is directly to global entity then need to create local entity for sameAs
                    # and the link to global entity with shadow-of relationship
                    
                    entity_name = normalised.split('/')[-1]
                
                    parts['data'] += "<" + namespace + chunks[2] + "> owl:sameAs <" + namespace + entity_name + ">;\n"
                    parts['data'] += "<" + namespace + entity_name + "> ome:shadow-of <" + normalised + ">;\n"
                
                else:
                
                    parts['data'] += "<" + namespace + chunks[2] + "> owl:sameAs <" + normalised + ">;\n"
                    # Check if local entity is linked to global entity - if so add in shadow-of relationship
                    
                    global_id = get_linked_global_entity(dbname, normalised)
                    
                    for uid in global_id:
                        parts['data'] += "<" + normalised + "> ome:shadow-of <" + uid + ">;\n"
                
                parts['data'] += "\trdfs:label '" + chunks[0] + "' .\n\n"
           
            elif line[0] == 'R':
                
                parts['data'] += "<" + namespace + chunks[2].split(":")[1] + "> "
                    
                if lookup(chunks[1]) != False:
                    parts['data'] += lookup(chunks[1]) + " " + "<" + namespace + chunks[3].split(":")[1] + ">;\n" 
                else:
                    parts['data'] += get_long_rdf(chunks[1], chunks[3].split(":")[1], namespace)
                
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'
            
            elif line[0] == 'T':
                parts['data'] += "<" + namespace + chunks[0] + ">\n\ta "
                if lookup(chunks[1]) != False:
                    parts['data'] += lookup(chunks[1])
                parts['data'] += " ;\n"
                parts['data'] += "\tcnt:chars '" + " ".join(chunks[4:]) + "' .\n\n"
            
            elif line[0] == 'A':
                parts['data'] += "<" + namespace + chunks[2] + ">\n\ta " + lookup(chunks[3]) + ";\n"    
                parts['data'] += '\trdfs:label "' + chunks[0] + '" .\n\n'     
           
    return parts

def lookup(annotation):

    #conversion = {}
    
    #if annotation in conversion:
    #    annotation = conversion[annotation]

    if annotation in namespaces:
        return namespaces[annotation]
    elif annotation in category_map:
        return category_map[annotation] + ":" + annotation
    elif annotation in relationship_map:
        return relationship_map[annotation] + ":" + annotation
    elif annotation in extended_rdf_map:
        return False
    return annotation


def get_long_rdf(annotation, entity, namespace):
    ent = ''    
    if entity in category_map:
        ent = category_map[entity] + ":" + entity
    else:
        ent = "<" + namespace + entity + ">"

    if annotation in extended_rdf_map:
        raw = extended_rdf_map[annotation]
        return raw.replace('{1}', ent)

    return annotation + " " + ent
