import re
import resourceutil
from peewee import *

# pattern to match some unicode characters non recognized by mysql
SANITIZE_UNICODE = re.compile(u'[^\u0000-\uD7FF\uE000-\uFFFF]', re.UNICODE)

db = MySQLDatabase('expertfinding', host='127.0.0.1', user='root', passwd='T1JeWw3S')

class BaseModel(Model):
    class Meta:
        database = db

class User(BaseModel):
    uid = PrimaryKeyField()
    external_id = IntegerField()
    username = CharField()
    url = CharField()
    social_network = CharField()
    completed = BooleanField()

class Resource(BaseModel):
    uid = PrimaryKeyField()
    external_id = CharField()
    url = CharField()
    social_network = CharField()
    raw_content = TextField()
    location_name = CharField(null=True)
    location_lat = FloatField(null=True)
    location_lon = FloatField(null=True)

class ResourceUser(BaseModel):
    '''Intermediary table for many to many relationship between Resource and User.
       Contains a distance between the resource and the user.'''
    uid = PrimaryKeyField()
    user = ForeignKeyField(User)
    resource = ForeignKeyField(Resource)
    distance = IntegerField()

class Stem(BaseModel):
    uid = PrimaryKeyField()
    stem = CharField()

class Entity(BaseModel):
    uid = PrimaryKeyField()
    entity = CharField()

class ResourceStem(BaseModel):
    '''Intermediary table for many to many relationship between Resource and Stem'''
    uid = PrimaryKeyField()
    stem = ForeignKeyField(Stem)
    resource = ForeignKeyField(Resource)

class ResourceEntity(BaseModel):
    '''Intermediary table for many to many relationship between Resource and Entity.
       Contains a weight rho used for entity score calculation. '''
    uid = PrimaryKeyField()
    entity = ForeignKeyField(Entity)
    resource = ForeignKeyField(Resource)
    rho = FloatField()

class UserScore(BaseModel):
    uid = PrimaryKeyField()
    score = FloatField()
    owner = ForeignKeyField(User, related_name='scores')

class ResourceScore(BaseModel):
    uid = PrimaryKeyField()
    score = FloatField()
    resource = ForeignKeyField(Resource, related_name='scores')

def init_graph():
    # connect to the database
    db.connect()

    # create tables if necessary
    User.create_table(True)
    Resource.create_table(True)
    ResourceUser.create_table(True)
    Stem.create_table(True)
    Entity.create_table(True)
    ResourceStem.create_table(True)
    ResourceEntity.create_table(True)
    UserScore.create_table(True)
    ResourceScore.create_table(True)

def is_first_run(social_network):
    '''Check if there is at least one user in the graph. If yes, return false.'''
    return User.select().where(User.social_network == social_network).count() == 0

def add_user(user):
    # add user to the db
    query = User.select().where((User.social_network == user.social_network) & (User.external_id == user.external_id))
    if not query.exists():
        # persist
        user.save()
        return user
    else:
        # return user from db
        return query.get()

def add_resource(resource):
    query = Resource.select().where(
        (Resource.social_network == resource.social_network) & (Resource.external_id == resource.external_id))
    if not query.exists():
        # remove invalid Unicode characters with a white square to avoid errors while persisting
        resource.raw_content = re.sub(SANITIZE_UNICODE, u'\u25FD', resource.raw_content)

        if resource.location_name is not None:
            resource.location_name = re.sub(SANITIZE_UNICODE, u'\u25FD', resource.location_name)

        # extract content from (eventual) http links, replace links with actual content
        content = resourceutil.extract_content_from_url(resource.raw_content)

        # check wether the resource is in english before persisting it
        if resourceutil.is_english(content):
            # persist resource
            resource.save()

            # entities
            entities = resourceutil.extract_entities(content)
            for entity in entities:
                entity_query = Entity.select().where(Entity.entity == entity['entity'])
                if not entity_query.exists():
                    # entity does not exist yet
                    entity_object = Entity(entity=entity['entity'])
                    entity_object.save()
                else:
                    entity_object = entity_query.get()

                # map resource and entity
                ResourceEntity(
                    entity = entity_object,
                    resource = resource,
                    rho = entity['rho']
                ).save()

            # stems
            stems = resourceutil.extract_stems(content)
            for stem in stems:
                stem_query = Stem.select().where(Stem.stem == stem)
                if not stem_query.exists():
                    # stem does not exist yet
                    stem_object = Stem(stem=stem)
                    stem_object.save()
                else:
                    stem_object = stem_query.get()

                # map resource and stem
                ResourceStem(
                    stem = stem_object,
                    resource = resource
                ).save()
        else:
            return None # resource not in English, return None

        return resource # return newly created resource
    else:
        return query.get() # return resource from the db


def map_user_with_resource(user, resource, distance):
    ResourceUser(
        user = user,
        resource = resource,
        distance = distance
    ).save()

def print_statistics():
    query = User.select()
    print 'number of users: ' + str(query.count()) + '\n'
    completed_users_query = query.where(User.completed == True)
    if completed_users_query.exists():
        print 'number of completed users: ' + str(completed_users_query.count()) + '\n'
    else:
        print 'number of completed users: 0\n'
    print 'number of resources: ' + str(Resource.select().count()) + '\n'
     