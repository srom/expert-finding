import time, peewee
from random import randint
import graphmanager as graph
from abc import ABCMeta, abstractmethod

class Crawler(object):
    '''Abstract class handling graph crawling.'''
    __metaclass__ = ABCMeta

    def __init__(self, social_network):
        self.social_network = social_network

    @abstractmethod
    def get_user_resources(self, user):
        '''Get resources from the user. Should not include user profile. 
           Must return a list of resources or None.'''
        pass

    @abstractmethod
    def get_user_profile(self, user):
        '''Get user profile. Must return a resource or None.'''
        pass

    @abstractmethod
    def get_user_followees(self, user):
        '''Get all people that this user follows. 
            Must return a list of users or None.'''
        pass

    @abstractmethod
    def get_first_user(self):
        '''Get the first user to init the graph. Must return a user.'''
        pass

    def run(self):
        '''Start the crawler.'''
        # init graph
        graph.init_graph()

        # init variables
        firstRun = graph.is_first_run(self.social_network)
        active_users = []
        loop = 0
        initial_time = int(round(time.time()))

        # start crawling
        while True:
            if firstRun:
                user = graph.add_user(self.get_first_user())
                firstRun = False
            else:
                if len(active_users) == 0:
                    user = graph.User.get(
                        (graph.User.social_network == self.social_network) 
                        & (graph.User.completed == False))
                elif len(active_users) == 1:
                    user = graph.User.get(
                        (graph.User.social_network == self.social_network) 
                        & (graph.User.completed == False)
                        & (graph.User.uid != active_users[0].uid))
                else:
                    user = graph.User.get(
                        (graph.User.social_network == self.social_network) 
                        & (graph.User.completed == False)
                        & (graph.User.uid != active_users[0].uid)
                        & (graph.User.uid != active_users[1].uid))

            print 'current user: ' + user.username


            active_users.insert(0, user)

            # get user profile
            profile = self.get_user_profile(user)
            # add it to the graph
            if profile is not None:
                resource = graph.add_resource(profile)
                # map resource with active users
                if resource is not None:
                    graph.map_user_with_resource(active_users[0], resource, 0)
                    if len(active_users) >= 2:
                        graph.map_user_with_resource(active_users[1], resource, 1)
                    if len(active_users) == 3:
                        graph.map_user_with_resource(active_users[2], resource, 2)

            # get all media from user and add them to the graph
            resources = self.get_user_resources(user)
            # map resources with active users
            for res in resources:
                resource = graph.add_resource(res)
                if resource is not None:
                    graph.map_user_with_resource(active_users[0], resource, 1)
                    if len(active_users) >= 2:
                        graph.map_user_with_resource(active_users[1], resource, 2)

            # get all people that this user follow and add them to the graph
            for followee in self.get_user_followees(user):
                graph.add_user(followee)

            # oldest user in active_users is completed
            if len(active_users) == 3:
                old_user = active_users.pop()
                old_user.completed = True
                old_user.save()

            # print statistics
            graph.print_statistics()
            elapsed_time = int(round(time.time())) - initial_time
            loop = loop + 1
            print 'Avg. time to complete a loop: ' + str(round(elapsed_time / loop)) + ' seconds\n'
