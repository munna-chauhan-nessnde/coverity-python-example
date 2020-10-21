#!/usr/bin/python
# -*- coding: utf-8 -*-

# General
import logging
import re
from urllib.error import URLError

# For Coverity - SOAP
from suds.client import Client
from suds.wsse import Security, UsernameToken

# -- Default values -- and global settings

DEFAULT_WS_VERSION = 'v9'


def compare_strings(str_a, str_b):
    '''Compare strings for equivalence

    some leniency allowed such as spaces and casing
    '''
    if re.match(str_b, str_a, flags=re.IGNORECASE):
        return True
    # ignore embedded spaces and some odd punctuation characters ("todo" = "To-Do")
    str_a2 = re.sub(r'[.:\-_ ]', '', str_a)
    str_b2 = re.sub(r'[:\-_ ]', '', str_b)  # don't remove dot (part of regex?)
    if re.match(str_b2, str_a2, flags=re.IGNORECASE):
        return True
    return False


# -- Services and other utilities for coverity configuration ------------------
class Service:
    """
    Basic endpoint Service
    """

    def __init__(self, transport, hostname, port, ws_version):
        self.ws_version = ws_version
        self.port = port
        self.hostname = hostname
        self.transport = transport
        self.client = None

    def get_transport(self):
        """Get transport protocol"""
        return self.transport

    def get_hostname(self):
        """Get hostname for service"""
        return self.hostname

    def get_port(self):
        """Get port for service"""
        return self.port

    def get_ws_version(self):
        """Get WS version for service"""
        return self.ws_version

    def get_service_url(self, path=''):
        """Get Service url with given path"""
        url = self.transport + '://' + self.hostname
        if bool(self.port):
            url += ':' + self.port
        if path:
            url += path
        return url

    def get_ws_url(self, service):
        """Get WS url with given service"""
        return self.get_service_url('/ws/' + self.ws_version + '/' + service + '?wsdl')

    def login(self, username, password):
        """Login to Coverity using given username and password"""
        security = Security()
        token = UsernameToken(username, password)
        security.tokens.append(token)
        self.client.set_options(wsse=security)

    def validate_presence(self, url, service_name):
        """Initializes the client attribute while validating the presence of the service"""
        try:
            self.client = Client(url)
            logging.info("Validated presence of %s [%s]", service_name, url)
        except URLError:
            self.client = None
            logging.critical("No such %s [%s]", service_name, url)
            raise


class CoverityConfigurationService(Service):
    """
    Coverity Configuration Service (WebServices)
    """

    def __init__(self, transport, hostname, port, ws_version=DEFAULT_WS_VERSION):
        super(CoverityConfigurationService, self).__init__(transport, hostname, port, ws_version)
        self.checkers = None
        url = self.get_ws_url('configurationservice')
        logging.getLogger('suds.client').setLevel(logging.CRITICAL)
        self.validate_presence(url, 'Coverity Configuration Service')

    def login(self, username, password):
        """Login to Coverity Configuration service using given username and password"""
        super(CoverityConfigurationService, self).login(username, password)
        version = self.get_version()
        if version is None:
            raise RuntimeError("Authentication to [%s] FAILED for [%s] account - check password"
                               % (self.get_service_url(), username))
        else:
            logging.info("Authentication to [%s] using [%s] account was OK - version [%s]",
                         self.get_service_url(), username, version.externalVersion)

    def get_version(self):
        """Get the version of the service, can be used as a means to validate access permissions"""
        try:
            return self.client.service.getVersion()
        except URLError:
            return None

    @staticmethod
    def get_project_name(stream):
        """Get the project name from the stream object"""
        return stream.primaryProjectId.name

    @staticmethod
    def get_triage_store(stream):
        """Get the name of the triaging store from the stream object"""
        return stream.triageStoreId.name

    def get_stream(self, stream_name):
        """Get the stream object from the stream name"""
        filter_spec = self.client.factory.create('streamFilterSpecDataObj')

        # use stream name as an initial glob pattern
        filter_spec.namePattern = stream_name

        # get all the streams that match
        streams = self.client.service.getStreams(filter_spec)

        # find the one with a matching name
        for stream in streams:
            if compare_strings(stream.id.name, stream_name):
                return stream
        return None

    # get a list of the snapshots in a named stream
    def get_snapshot_for_stream(self, stream_name):
        """Get snapshot object for given stream name"""
        stream_id = self.client.factory.create('streamIdDataObj')
        stream_id.name = stream_name
        # optional filter specification
        filter_spec = self.client.factory.create('snapshotFilterSpecDataObj')
        # return a list of snapshotDataObj
        return self.client.service.getSnapshotsForStream(stream_id, filter_spec)

    @staticmethod
    def get_snapshot_id(snapshots, idx=1):
        """Get the nth snapshot (base 1) - minus numbers to count from the end backwards (-1 = last)"""
        if bool(idx):
            num_snapshots = len(snapshots)
            if idx < 0:
                required = num_snapshots + idx + 1
            else:
                required = idx

            if 0 < abs(required) <= num_snapshots:
                # base zero
                return snapshots[required - 1].id
        return 0

    def get_snapshot_detail(self, snapshot_id):
        """Get detailed information about a single snapshot"""
        snapshot = self.client.factory.create('snapshotIdDataObj')
        snapshot.id = snapshot_id
        # return a snapshotInfoDataObj
        return self.client.service.getSnapshotInformation(snapshot)

    def get_checkers(self):
        """Get a list of checkers from the service"""
        if not self.checkers:
            self.checkers = self.client.service.getCheckerNames()
        return self.checkers

    @staticmethod
    def add_filter_rqt(name, req_csv, valid_list, filter_list, allow_regex=False):
        """Lookup the list of given filter possibility, add to filter spec and return a validated list"""
        logging.info('Validate required %s [%s]', name, req_csv)
        validated = ""
        delim = ""
        for field in req_csv.split(','):
            if not valid_list or field in valid_list:
                logging.info('Classification [%s] is valid', field)
                filter_list.append(field)
                validated += delim + field
                delim = ","
            elif allow_regex:
                pattern = re.compile(field)
                for element in valid_list:
                    if pattern.search(element) and element not in filter_list:
                        filter_list.append(element)
                        validated += delim + element
                        delim = ","
            else:
                logging.error('Invalid %s filter: %s', name, field)
        return validated


# Start Logging Configuration ------------------------------------------------------------
""" Module to provide functions that accommodate logging. """


def report_warning(msg, docname, lineno=None):
    """Convenience function for logging a warning

    Args:
        msg (str): Message of the warning
        docname (str): Name of the document in which the error occurred
        lineno (str): Line number in the document on which the error occurred
    """
    logger = logging.getLogger(__name__)
    if lineno is not None:
        logger.warning(msg, location=(docname, lineno))
    else:
        logger.warning(msg, location=docname)


def report_info(msg, nonl=False):
    """Convenience function for information printing

    Args:
        msg (str): Message of the warning
        nonl (bool): True when no new line at end
    """
    logger = logging.getLogger(__name__)
    logger.info(msg, nonl=nonl)


# End Logging Configuration ______________________________________________________

if __name__ == '__main__':
    print("Sorry, no main here")
