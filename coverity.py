# -*- coding: utf-8 -*-

"""
Coverity Installing
"""
import configparser
from getpass import getpass
from optparse import OptionParser
from urllib.error import URLError, HTTPError

import coverity_operations as wsc
from coverity_services import CoverityConfigurationService
from coverity_services import report_info, report_warning

# Coverity Configuration Operations
# Below OPERATIONS_NAME must use as a function in coverity_operations.py file
OPERATIONS_NAME = {'copyStream', 'createGroup', 'createProject', 'createRole', 'createStream', 'createStreamInProject',
                   'createTriageStore', 'createUser', 'deleteGroup', 'deleteProject', 'deleteRole', 'deleteStream',
                   'deleteTriageStore', 'deleteUser', 'getAllPermissions', 'getAllRoles', 'getGroup', 'getGroups',
                   'getProjects', 'getRole', 'getStreams', 'getTriageStores', 'getUser', 'getUsers',
                   'mergeTriageStores', 'updateGroup', 'updateProject', 'updateRole', 'updateStream',
                   'updateTriageStore', 'updateUser'}


class CoverityConnector:
    """
    Class containing functions and variables for connecting coverity web service.
    """

    def __init__(self):
        """
        Initialize the object by setting error variable to false
        """
        self.configServiceClient = ''
        self.coverity_login_error = False
        self.coverity_login_error_msg = ''

    def initialize_environment(self, coverity_credentials):
        # Login to Coverity Server
        try:
            self.input_credentials(coverity_credentials)
            report_info('Login to Coverity server... ', True)
            coverity_conf_service = CoverityConfigurationService(coverity_credentials['transport'],
                                                                 coverity_credentials['hostname'],
                                                                 coverity_credentials['port'])
            coverity_conf_service.login(coverity_credentials['username'],
                                        coverity_credentials['password'])
            report_info('done')
            self.configServiceClient = coverity_conf_service

        except (URLError, HTTPError, Exception, ValueError) as error_info:
            if isinstance(error_info, EOFError):
                self.coverity_login_error_msg = "Coverity credentials are not configured."
            else:
                self.coverity_login_error_msg = str(error_info)
            report_info('failed with: %s' % error_info)
            self.coverity_login_error = True

    # -- Helper functions of event handlers--------------------------------------------
    @staticmethod
    def input_credentials(config_credentials):
        """ Ask user to input username and/or password if they haven't been configured yet.

        Args:
            config_credentials (dict): Dictionary to store the user's credentials.
        """
        if not config_credentials['username']:
            config_credentials['username'] = input("Coverity username: ")
        if not config_credentials['password']:
            config_credentials['password'] = getpass("Coverity password: ")


if __name__ == '__main__':
    config = configparser.ConfigParser()
    config.read('conf.ini')

    parser = OptionParser()
    parser.add_option("-u", "--user", dest="user", help="Set coverity user", default="DEFAULT")
    options, args = parser.parse_args()
    userType = options.user

    credentials = {
        'transport': config[userType]['transport'],
        'port': config[userType]['port'],
        'hostname': config[userType]['hostname'],
        'password': config[userType]['password'],
    }
    connector = CoverityConnector()
    connector.initialize_environment(credentials)

    for operation in args:
        if operation in OPERATIONS_NAME:
            do = f"{operation}"
            if hasattr(wsc, do) and callable(func := getattr(wsc, do)):
                result = func(connector.configServiceClient)
                print('Operation response: ', result)

            else:
                report_warning('Please add %s function in coverity_operations.py file.' % operation,
                               'coverity_operations.py')
        else:
            report_warning('%s operation is not available!' % operation, 'coverity.py')
