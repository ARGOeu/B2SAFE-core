# !/usr/bin/env python

import sys
import json
import base64
from pprint import pformat
import requests
import fnmatch
import logging

class EudatRemoteSource:

    def __init__(self, main_project, subgroups, conf, role_map, parent_logger=None):
        """initialize the object"""

        if (parent_logger): self.logger = parent_logger
        else: self.logger = logging.getLogger('eudat')

        self.main_project = main_project
        self.subgroups = subgroups

        confkeys = ['host', 'username', 'password', 'carootdn', 'ns_prefix']
        missingp = []
        for key in confkeys:
            if not key in conf: missingp.append(key)
        if len(missingp) > 0:
            self.logger.warning('missing parameters: ' + pformat(missingp))
        self.conf = conf
        self.remote_users_list = self.getRemoteUsers()
        self.roles = self.readRoleMapFile(role_map)


    def readRoleMapFile(self, path):

        try:
            filehandle = open(path, "r")
        except IOError as err:
            print "error: failed to open %s: %s" % (path, err.strerror)
            sys.exit(-1)

        with filehandle:
            return json.loads(filehandle.read())        
    
        
    def queryUnity(self, sublink):
        """
        :param argument: url to unitydb with entity (entityID) or group (groupName)
        :return:
        """
        url = self.conf['host'] + sublink
        try:
            self.logger.debug("Querying the URL: {}".format(url))
            response = requests.get(url, verify=False, auth=(self.conf['username'], self.conf['password']))
        except IOError, e:
            self.logger.error("Wrong username or password", exc_info=True)
            sys.exit(1)
        assert response.status_code == 200
        json_data = (response.text).encode('utf-8')
        self.logger.debug("Response:{}".format(json_data))
        response_dict = json.loads(json_data)

        return response_dict


    def getRemoteUsers(self):
        """
        Get the remote users' list
        """
        self.logger.info("Getting list of users from eudat db...")
        # get list of all groups in Unity
        group_list = self.queryUnity("group/%2F")

        final_list = {}
        list_member = []
        users_map = {}
        attribs_map = {}
        for member_id in group_list['members']:
            attr_list = {}
            user_record = self.queryUnity("entity/"+str(member_id))
            identity_types = {}
            for identity in user_record['identities']:
                self.logger.debug("identity['typeId'] = " + identity['typeId'])
                self.logger.debug("identity['value'] = " + identity['value'])
                identity_types[identity['typeId']] = identity['value']
            user_attrs = self.queryUnity("entity/"+str(member_id)+"/attributes")
            user_cn = None
            for user_attr in user_attrs:
                if user_attr['name'] == 'cn':
                    user_cn = user_attr['values'][0]
                             
            if "userName" in identity_types.keys():
                list_member.append(identity_types['userName'])
                users_map[member_id] = identity_types['userName']
            elif "identifier" in identity_types.keys():
                list_member.append(identity_types['identifier'])
                users_map[member_id] = identity_types['identifier']
            else:
                list_member.append(str(member_id))
                users_map[member_id] = str(member_id)

            if user_cn is None:
                user_cn = users_map[member_id]
            if "persistent" in identity_types.keys():
                # Here we build the DN: the way to build it could change
                # in the future.
#TODO catch unicode error and filter out strange CN, logging the errors
                userDN = self.conf['carootdn'] + '/CN=' + identity['value'] \
                       + '/CN=' + user_cn.encode('ascii', 'replace')
                # Here the DN attribute is considered a list because, 
                # in principle, multiple DNs could be associated to a user
                attr_list['DN'] = [userDN]

            attribs_map[users_map[member_id]] = attr_list

        final_list['members'] = list_member
        final_list['attributes'] = attribs_map

        # Query and get list of all user from Groups in Unity
        list_group = {}
        for group_name in group_list['subGroups']:
            member_list = self.queryUnity("group"+group_name)
            user_list = []
            for member_id in member_list['members']:
                user_list.append(users_map[member_id])
            list_group[group_name[1:]] = user_list

        final_list['groups'] = list_group

        return final_list


    def synchronize_user_db(self, data):
        """
        Synchronize the remote users' list with a local json file (user db)
        """
        # build the remote users list, filtering selected groups, if any
        if self.subgroups is not None:
            filtered_list = {org:members for (org,members)
                             in self.remote_users_list['groups'].iteritems()
                             if org in self.subgroups}
        else:
            filtered_list = self.remote_users_list['groups']

        data = self._userMapper(filtered_list, data, False)
            
        return data


    def synchronize_user_attributes(self, data):
        """
        Synchronize the remote users' attributes with a local json file
        for the time beeing just the DNs are considered
        """
        self.logger.info('Checking user attributes ...')

        if self.subgroups is not None:
            filtered_group_list = {org:members for (org,members)
                             in self.remote_users_list['groups'].iteritems()
                             if org in self.subgroups}
            users = []
            for group in filtered_group_list.keys():
                for user in self.remote_users_list['groups'][group]:
                    self.logger.debug('looking at user ' + user)
                    users.append(user)
                    self.logger.debug('added user to the list ' + str(users))

            filtered_list = {user:attrs for (user,attrs)
                             in self.remote_users_list['attributes'].iteritems()
                             if user in users}
        else:
            filtered_list = self.remote_users_list['attributes']
            filtered_group_list = self.remote_users_list['groups']

        userdict = self._userMapper(filtered_group_list)
            
        for user,attrs in filtered_list.iteritems():
            self.logger.info('Adding DNs belonging to the user ' + user + ' ...')
            #### add its DN to the irods user
            if (user in userdict.keys()):
                u = userdict[user]
                if u not in data.keys():
                    data[u] = []
                data[u] = list(set(data[u] + attrs['DN']))
                self.logger.debug('\tadded user ' + u + '\' DNs: '
                              + pformat(attrs['DN']))            

        return data


    def _userMapper(self, mainDict, data=None, directMap=True):
        """
        Check which of the remote users should be associated to a local user
        according to the local user map
        """
        userdict = None
        if directMap:
            userdict = {}
        else:
            userdict = data[self.main_project]["groups"]
        for org,members in mainDict.iteritems():
            subjectMatch = False
            for iuser in self.roles:
                if not directMap:
                    if iuser not in userdict:
                        userdict[iuser] = []
                subjectMatch = False
                for groupVal in self.roles[iuser]['organization']:
                    subjectMatch = fnmatch.fnmatch(org, groupVal)
                    if subjectMatch:
                        if 'exclude' in self.roles[iuser].keys():
                            remoteUsers = set(members) - set(self.roles[iuser]['exclude'])
                        for member in remoteUsers:
                            if directMap:
                                userdict[member] = iuser
                            else:
                                userdict[iuser].append(member)
                                userdict[iuser] = list(set(userdict[iuser]))
                userMatch = False
                for userVal in self.roles[iuser]['user']:
                    for member in members:
                        userMatch = fnmatch.fnmatch(member, userVal)
                        if userMatch:
                            if directMap:
                                userdict[member] = iuser
                            else:
                                userdict[iuser].append(member)
                                userdict[iuser] = list(set(userdict[iuser]))

        return userdict

