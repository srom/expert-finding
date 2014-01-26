import re, time
import graphmanager as graph
from instagram import client
from crawler import Crawler
from httplib2 import ServerNotFoundError

# constant storing the social network type
SN = 'IG'

MAX_ID_REGEX = re.compile(r'max_id=([^&]+)')
CURSOR_REGEX = re.compile(r'cursor=([^&]+)')

# Instagram API object
api = client.InstagramAPI(client_id='') # add your own client_id

class InstagramCrawler(Crawler):
    '''InstagramCrawler implements abstract methods of Crawler.'''
    def __init__(self, social_network):
        super(InstagramCrawler, self).__init__(social_network)

    def get_first_user(self):
        '''Get the first user to init the graph.'''
        # entry point to the graph: a user named sparrowflu
        # this guy is a photographer in London
        seed_user_id = 4355568
        # create first user and add him to the graph
        # get user info from Instagram
        retry = True
        while retry:
            try:
                time.sleep(0.7)
                user_info = api.user(seed_user_id)
            except ServerNotFoundError as e:
                retry = True
            retry = False
        # create first user
        user = graph.User(
            social_network=self.social_network, 
            external_id=user_info.id, 
            username=user_info.username, 
            url='http://instagram.com/' + user_info.username, 
            completed=False
        )
        return user

    def get_user_profile(self, user):
        '''Get user profile.'''
        # add user profile to the graph as a resource
        retry = True
        while retry:
            try:
                time.sleep(0.7)
                user_info = api.user(user.external_id)
                retry = False
            except ServerNotFoundError as e:
                retry = True
            except:
                return None
        if user_info.bio is not None:
            raw_content = user_info.bio
            if user_info.website:
                raw_content += ' ' + user_info.website

            # create user profile resource and add it to the graph
            resource = graph.Resource(
                social_network=user.social_network,
                external_id=user.external_id,
                url='http://instagram.com/' + user.username,
                raw_content=raw_content,
                location_name=None,
                location_lat=None,
                location_lon=None
            )
            return resource
        else:
            return None

    def get_user_resources(self, user):
        '''Get resources from the user.'''
        resources = []
        max_id = ''
        while True:
            followees_page = []
            next = ''
            retry = True
            error = False
            while retry:
                try:
                    time.sleep(0.7) # be nice with the API
                    if max_id == '':
                        recent_media, next = api.user_recent_media(user_id=user.external_id, count=33)
                    else:
                        recent_media, next = api.user_recent_media(user_id=user.external_id, max_id=max_id, count=33)
                    retry = False
                except ServerNotFoundError as e:
                    retry = True
                except:
                    error = True
                    break;

            if error:
                break;

            for media in recent_media:
                create_resource = False
                if hasattr(media, 'caption') and media.caption is not None:
                    create_resource = True
                    raw_content = media.caption.text
                    if hasattr(media, 'location') and media.location is not None:
                        raw_content = raw_content + '. ' + media.location.name
                elif hasattr(media, 'location') and media.location is not None:
                    create_resource = True
                    raw_content = media.location.name

                if create_resource:
                    try:
                        resource = graph.Resource(
                            social_network=SN,
                            external_id=media.id,
                            url=media.link,
                            raw_content=raw_content,
                            location_name=media.location.name,
                            location_lat=media.location.point.latitude,
                            location_lon=media.location.point.longitude
                        )
                    except AttributeError:
                        resource = graph.Resource(
                            social_network=SN,
                            external_id=media.id,
                            url=media.link,
                            raw_content=raw_content,
                            location_name=None,
                            location_lat=None,
                            location_lon=None
                        )
                    if resource is not None:
                        resources.append(resource)

            if next is None:
                break
            else:
                # get max_id param for the next page of results
                max_id_matcher = MAX_ID_REGEX.search(next)
                if max_id_matcher is not None:
                    max_id = max_id_matcher.group(1)
                else:
                    break
        return resources

    def get_user_followees(self, user):
        '''Get all people that this user follows.'''
        followees = []
        cursor = ''
        while True:
            followees_page = []
            next = ''
            retry = True
            error = False
            while retry:
                try:
                    time.sleep(0.7) # be nice with the API
                    if cursor == '':
                        followees_page, next = api.user_follows(user_id=user.external_id)
                    else:
                        followees_page, next = api.user_follows(user_id=user.external_id, cursor=cursor)
                    retry = False
                except ServerNotFoundError as e:
                    retry = True
                except:
                    error = True
                    break;

            if error:
                break;

            for user_info in followees_page:
                followee = graph.User(
                    social_network=SN, 
                    external_id=user_info.id, 
                    username=user_info.username, 
                    url='http://instagram.com/' + user_info.username, 
                    completed=False
                )
                followees.append(followee)

            if next is None:
                break
            else:
                # get cursor param for the next page of results
                cursor_matcher = CURSOR_REGEX.search(next)
                if cursor_matcher is not None:
                    cursor = cursor_matcher.group(1)
                else:
                    break
        return followees

# let's crawl Instagram!
InstagramCrawler(SN).run()
