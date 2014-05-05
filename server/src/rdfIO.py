#!/usr/bin/env python

import re

from annotation import open_textfile

namespace = 'http://contextus.net/data/RRH/'

namespaces = {'ome':'http://contextus.net/ontology/ontomedia/core/expression#', 'omt':'http://contextus.net/ontology/ontomedia/ext/common/trait#', 'omb':'http://contextus.net/ontology/ontomedia/ext/common/being#', 'omeg':'http://contextus.net/ontology/ontomedia/ext/events/gain#', 'omel':'http://contextus.net/ontology/ontomedia/ext/events/loss#', 'omet':'http://contextus.net/ontology/ontomedia/ext/events/trans#', 'omes':'http://contextus.net/ontology/ontomedia/ext/events/social#', 'omea':'http://contextus.net/ontology/ontomedia/ext/events/action#', 'omj':'http://contextus.net/ontology/ontomedia/ext/events/travel#', 'eprop':'http://contextus.net/ontology/ontomedia/ext/events/eventprop#', 'omf':'http://contextus.net/ontology/ontomedia/ext/fiction/fic#'}
    
category_map = {'Entity':'ome', 'Being':'ome', 'Character':'ome', 'Item':'ome', 'Abstract-Item':'ome', 'Group':'omb', 'Community':'omb', 'Household':'omb', 'Bonded-Group':'omb', 'Bonded-Pair':'omb', 'Organisation':'omb', 'Company':'omb', 'Government':'omb', 'Context':'ome', 'Physical-Item':'ome', 'Space':'ome','Event':'ome', 'Gain':'ome', 'Creation':'omeg', 'Loss':'ome', 'Destruction':'omel', 'Betrayal':'omel', 'Transformation':'ome', 'Transference':'omet', 'Division':'omet', 'Merge':'omet', 'Degradation':'omet', 'Social':'ome', 'Conversational':'omes', 'Flirtation':'omes', 'Proposition':'omes', 'Political':'omes', 'Academic':'omes', 'Legal':'omes', 'Theological':'omes', 'Philosophical':'omes', 'Action':'ome', 'Violence':'omea', 'Sex':'omea', 'Festivity':'omea', 'Ingestion':'omea', 'Celestial':'omea', 'Environmental':'omea', 'Travel':'omj', 'Describes':'omf', 'Implied':'omf', 'References-Concept':'omf', 'In-Passing':'omf', 'Vague-Description':'omf', 'Detailed-Description':'omf', 'Extremely-Detailed-Description':'omf', 'Fade-To-Black':'omf', 'Extremely-Detailed-Description':'omf', 'Spoiler':'omf', 'Key':'omf', 'Main':'omf', 'Fact':'omf', 'Nitpick':'omf', 'Nitpick':'omf', 'Consent-Given':'eprop', 'Consent-Implied':'eprop', 'Consent-Not-Given':'eprop', 'Consent-Unclear':'eprop'}

    
relationship_map = {'is-linked-to':'ome', 'is':'ome', 'is-shadow-of':'ome', 'contains':'ome', 'contained-by':'ome', 'has-subject-entity':'ome', 'has-object-entity':'ome', 'has-subject':'omes', 'to':'ome', 'from':'ome'}
    
extended_rdf_map = {'bond-with':'omt:has-trait [\n\ta omt:link ; [\n\t\ta omb:Bond;\n\t\tomb:has-bond {1}].\n\t].\n', 'family-of':'omt:has-trait [\n\ta omt:link ; [\n\t\ta omb:Family;\n\t\tomb:is-relation-of {1}].\n\t].\n'}

def convert_to_rdf(fpath):
    
    rdf = ''
    
    for prefix, url in namespaces.items():
        rdf += '@prefix ' + prefix + ': <' + url + '>.\n'

    rdf += '\n'
        
    with open(fpath) as txt_file:
        for line in txt_file:

            chunks = re.split(r'\s+', line)
            
            if line[0] == 'E':
        
                Event = chunks[1]
            
                EventID = Event.split(':')[1]
                EventType = Event.split(':')[0]
            
                rdf += "<" + namespace + EventID + ">\n\ta "
                
                if lookup(EventType) != False:
                    rdf += lookup(EventType) + ";\n"
            
                for chunk in chunks[2:]:
                    if ':' in chunk:
                        rdf += "\t" + chunk.split(':')[0] + " <" + namespace + chunk.split(':')[1] + ">;\n"
                
                rdf += "\trdf:label " + chunks[0] + " .\n\n"
                
            elif line[0] == 'N':        
                rdf += "<" + namespace + chunks[4] + "> owl:sameAs <" + namespace + chunks[3] + ">;\n"
                rdf += "\trdf:seeAlso " + namespace + chunks[0] + " .\n\n"
           
            elif line[0] == 'R':
                
                rdf += "<" + namespace + chunks[2].split(":")[1] + "> "
                    
                if lookup(chunks[1]) != False:
                    rdf += lookup(chunks[1]) + " " + "<" + namespace + chunks[3].split(":")[1] + ">;\n" 
                else:
                    rdf += get_long_rdf(chunks[1], chunks[3].split(":")[1])
                
                rdf += "\trdf:label '" + chunks[0] + "' .\n\n"
            
            elif line[0] == 'T':
                rdf += "<" + namespace + chunks[0] + ">\n\ta <"
                if lookup(chunks[1]) != False:
                    rdf += lookup(chunks[1])
                    rdf += '{' + chunks[1] + '}'
                rdf += "> .\n\n"
            
            elif line[0] == 'A':
                rdf += "<" + namespace + chunks[2] + ">\n\ta <" + lookup(chunks[3]) + ">;\n"    
                rdf += "\trdf:label '" + chunks[0] + "' .\n\n"     
           
    return rdf

def lookup(annotation):
    if annotation in namespaces:
        return namespaces[annotation]
    elif annotation in category_map:
        return category_map[annotation] + ":" + annotation
    elif annotation in relationship_map:
        return relationship_map[annotation] + ":" + annotation
    elif annotation in extended_rdf_map:
        return False
    return annotation


def get_long_rdf(annotation, entity):
    ent = ''    
    if entity in category_map:
        ent = category_map[entity] + ":" + entity
    else:
        ent = "<" + namespace + entity + ">"

    if annotation in extended_rdf_map:
        raw = extended_rdf_map[annotation]
        return raw.replace('{1}', ent)

    return annotation + " " + ent