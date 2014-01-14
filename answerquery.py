import graphmanager as graph
import resourceutil
from peewee import *

# weighting factor between stems and entities in resource score calculation
ALPHA = 0.6

query = 'What are some good place to hang out for a young professional in East London?'

# init
db = MySQLDatabase('expertfinding', host='127.0.0.1', user='root', passwd='T1JeWw3S')
db.connect()
# start fresh
graph.UserScore.create_table(True)
graph.ResourceScore.create_table(True)

def compute_resource_score(resource, query_stems, query_entities):
    stem_score = 0
    for stem in query_stems:
        # term frequency in the resource
        tf = (graph.ResourceStem
            .select()
            .join(graph.Stem)
            .where(
                (graph.ResourceStem.resource == resource) 
                & (graph.Stem.stem == stem))
            .count())
        # inverse resource frequency in all resources
        rf = (graph.ResourceStem
            .select()
            .join(graph.Stem)
            .where(graph.Stem.stem == stem)
            .count())
        if rf > 0:
            irf = 1. / rf
        else:
            irf = 1.
        # compute score
        stem_score = stem_score + tf * (irf * irf)

    entity_score = 0
    for entity in query_entities:
        # entity frequency in the resource
        ef = (graph.ResourceEntity
            .select()
            .join(graph.Entity)
            .where(
                (graph.ResourceEntity.resource == resource) 
                & (graph.Entity.entity == entity['entity']))
            .count())
        # inverse resource frequency in all resources
        rf = (graph.ResourceEntity
            .select()
            .join(graph.Entity)
            .where(graph.Entity.entity == entity['entity'])
            .count())
        if rf > 0:
            eirf = 1. / rf
        else:
            eirf = 1.
        # compute score
        weight = 0.0
        count = 0.0
        for e in graph.ResourceEntity.select().join(graph.Entity).where(
            (graph.ResourceEntity.resource == resource) 
            & (graph.Entity.entity == entity['entity'])):
            count = count + 1
            weight = weight + e.rho
        # average of all rho for a given resource
        if count > 0:
            weight = weight / count
        if weight > 0:
            weight = weight + 1
        entity_score = entity_score + weight * ef * (eirf * eirf)

    # calculate score
    score = ALPHA * stem_score + (1-ALPHA) * entity_score

    # persist score
    graph.ResourceScore(
        resource = resource,
        score = score
    ).save()

def compute_user_score(user):
    score = 0
    for resource in (graph.Resource
        .select()
        .join(graph.ResourceUser)
        .switch(graph.Resource)
        .join(graph.ResourceScore)
        .where(graph.ResourceUser.user == user)
        .order_by(graph.ResourceScore.score.desc())
        .limit(100)):
        resource_score = (graph.ResourceScore
            .select()
            .where(graph.ResourceScore.resource == resource)
            .get()
            .score)
        distance = (graph.ResourceUser
            .select()
            .where(
                (graph.ResourceUser.user == user) 
                & (graph.ResourceUser.resource == resource))
            .get()
            .distance)
        weight = 1.
        if distance == 1:
            weight = 0.75
        elif distance == 2:
            weight = 0.5

        score = score + resource_score * weight

    graph.UserScore(
        owner = user,
        score = score
    ).save()


def get_best_results():
    unique = set()
    best_resources = []
    for user in graph.User.select().join(graph.UserScore).order_by(graph.UserScore.score.desc()).limit(10):
        if len(best_resources) < 10:
            for resource in (graph.Resource.select()
                .join(graph.ResourceUser)
                .switch(graph.Resource)
                .join(graph.ResourceScore)
                .where((graph.ResourceUser.user == user) 
                    & ~(graph.Resource.location_name >> None))
                .order_by(graph.ResourceScore.score.desc())
                .limit(2)):
                if resource.external_id not in unique and resource.location_name.strip() != '':
                    best_resources.append(resource)
                    unique.add(resource.external_id)
    return best_resources

# query_stems = resourceutil.extract_stems(query)
# query_entities = resourceutil.extract_entities(query)

# for resource in graph.Resource.select():
#     print str(resource.uid)
#     compute_resource_score(resource, query_stems, query_entities)

# for user in graph.User.select().where(graph.User.completed == True):
#     compute_user_score(user)

for best_result in get_best_results():
    print best_result.url
