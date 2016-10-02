#!/usr/bin/python
"""
A convenient and fast method to know
the space occupied by a project in the
google cloud storage.

Use cases for GCS:
(1) If only project is provided total
    size of all bucket in that project is
    displayed
(2) If both project and bucket are specified
    total size of specific bucket if exist in 
    the given project would be shown

Use cases for AWS S3:
    Project id is used as a key to retrieve authentication details from
    aws_keys.json. If no bucket is specified the script will login to 
    s3 and retrieve list of all buckets and along with the size of each
    bucket. The aggregate is displayed at the end of the script

    If bucket name specified the script will query only specified bucket

"""

import argparse
import boto

from threading import Thread
from threading import Lock
from threading import Condition
from settings import settings
from settings.Config import Config
from gcloud import storage
from gcloud.storage import Bucket
from oauth2client.service_account import ServiceAccountCredentials

# Define the fields that we really need
# to compuet result
BLOB_FIELDS = 'prefixes,nextPageToken,items/size'
"""
Fetch object's size and prefixes only 
"""
BUCKET_FIELDS = 'nextPageToken,items/name'
"""
Fetch bucket name only
"""

def get_storage_client(project_id=None, credentials=None):
    """
    Create a storage client for the given project and credential
    :type project_id: :string
    :param project_id: google cloud project id

    :type credentials: :oauth2client.client.GoogleCredentials
    :param credentials: google cloud account credentials

    """
    return storage.Client(project=project_id, credentials=credentials)

def credentials_from_json_keyfile_name(key_file, scopes):
    """
    Create credentials from json file
    :type key_file: :string
    :param key_file: location of key file

    :type scopes: :string
    :param scopes: scope of the request
    """
    return ServiceAccountCredentials.from_json_keyfile_name(key_file, scopes)

class SizeTask(object):
    def __init__(self, max_thread, quiet, readable):
        """
        Initialize abstract size task
        :type max_thread: :int
        :param max_thread: Maximum number of launchable threads

        :type quiet: :boolean
        :param quiet: Run silently if true

        :type readable: :boolean
        :param readable: display human readable information when True
        """
        self.quiet = quiet
        self.readable = readable
        self.max_thread = min(max_thread, 1000)
        
        if self.max_thread <= 0:
            self.max_thread = 100

        self._jobs = {}
        self._clients = []

        self.__running = 0
        self.__started = False
        self.__total = 0
        self.__lock = Condition(Lock())
        self.__error = False
        self.__total_objects = 0

    def _after_fetch(self, bucket_name, prefixes, fetched_data):
        try:
            total, count = sum(fetched_data), len(fetched_data)
            self.__lock.acquire()
            self.__total += total
            self.__total_objects += count
            self.__running -= 1
            self._jobs[bucket_name].extend(prefixes)
        except Exception as ex:
            self.__error = True
            print ex
        finally:
            self.__lock.notify()
            self.__lock.release()

    def _fetch(self, bucket_name, client, prefix):
        """
        Implemented by subclass
        """
        pass

    def _before_start(self):
        """
        implemented by subclass
        """
        pass

    def size_readable(self):
        size = self.__total
        unit = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']
        ui = 0
        
        while (size / 1024.0) >= 1.0:
            size /= 1024.0
            ui += 1
        return '%0.3f %s' % (size, unit[ui])

    def start(self):
        """
        Start size task. An exception will be thrown if task has 
        already been started. It will create a number of threads and all
        will run simultaneously to produce output. 
        """
        if self.__started:
            raise Exception('Task has already been started')

        self.__started = True

        self._before_start()

        done = (sum([len(val) for val in self._jobs.values()]) == 0)
        
        while not done and not self.__error:
            task_args = []
            count = 0
            for key in self._jobs:
                prefixes = self._jobs[key]
                
                while len(prefixes) != 0:
                    task_args.append((key, self._clients[count], 
                                      prefixes.pop()))

                    count += 1
                    if count == self.max_thread:
                        break

                if count == self.max_thread:
                    break

            self.__running += count
            for args in task_args:
                task = Thread(target=self._fetch, args=args)
                task.start()

            try:
                print ('Number of threads running in parallel: %d/%d' % (count, 
                    self.max_thread))

                self.__lock.acquire()
                
                while self.__running != 0 and not self.__error:
                    self.__lock.wait()

            except Exception as ex:
                self.__error = True
                print ex
            finally:
                self.__lock.release()

            if self.__error:
                print ('An internal error has occurred')
                break

            done = (sum([len(val) for val in self._jobs.values()]) == 0)

            print ('Total number of objects read so far: %d ' % (
                self.__total_objects))

            print ('Total size of these objects on disk: %s' % (
                self.size_readable()))

            print ('--')

        if not self.__error:
            print 'Summary'
            print '--'
            print 'Total # of objects : %d' % self.__total_objects
            print 'Total raw size     : %d bytes' % self.__total
            print 'Total size         : %s' % self.size_readable()

class GCSSizeTask(SizeTask):
    def __init__(self, project_id=None, credentials=None, bucket_name=None,
            max_thread=100, quiet=False, readable=True):
        super(GCSSizeTask, self).__init__(max_thread, quiet, readable)

        self.project_id = project_id
        self.bucket_name = bucket_name
        self.credentials = credentials

    def _before_start(self):
        self._clients = [get_storage_client(project_id=self.project_id,
            credentials=self.credentials) for x in range(self.max_thread)]
        
        if self.bucket_name is None:
            buckets = self._clients[0].list_buckets(fields=BUCKET_FIELDS)
            self._jobs = {bucket.name : [None] for bucket in buckets}
        
        else:
            # Lets make sure that the bucket exists
            bucket = Bucket(self._clients[0], self.bucket_name)
            if not bucket.exists():
                print ("Bucket '%s' does not exist in project '%s'"
                    % (self.bucket_name, self.project))
                return
            self._jobs[bucket.name] = [None]

    def _fetch(self, bucket_name, client, prefix):
        bucket = Bucket(client, bucket_name)

        blobs = bucket.list_blobs(
            prefix=prefix,
            max_results=1000,
            delimiter='/',
            fields=BLOB_FIELDS
        )
        blob_data = []
        # ensure that no network error such as forbidden resource 
        # or has occurred.
        try:
            blob_data = [blob.size for blob in blobs]
        except Exception as ex:
            pass
        
        self._after_fetch(bucket_name, blobs.prefixes, blob_data)

def get_s3_connection(credentials=None):
    if credentials is None:
        return boto.connect_s3()
    else:
        return boto.connect_s3(
            credentials['AWS_ACCESS_KEY_ID'],
            credentials['AWS_SECRET_ACCESS_KEY']
        )

class S3SizeTask(SizeTask):
    def __init__(self, bucket_name=None, max_thread=100, credentials=None,
                 quiet=False, readable=True):
        super(S3SizeTask, self).__init__(max_thread, quiet, readable)
        
        self.bucket_name = bucket_name
        self.credentials = credentials

    def _before_start(self):
        self._clients = [get_s3_connection(self.credentials) for x in range(
            self.max_thread)]

        if self.bucket_name is None:
            buckets = self._clients[0].get_all_buckets()
            self._jobs = {bucket.name: [None] for bucket in buckets}

        else:
            bucket = boto.s3.bucket.Bucket(self._clients[0], self.bucket_name)

            if self._clients[0].lookup(bucket.name) == None:
                print ("Bucket '%s' does not exist"
                    % (self.bucket_name))
                return
            self._jobs[bucket.name] = [None]

    def _fetch(self, bucket_name, client, prefix):
        bucket = boto.s3.bucket.Bucket(client, bucket_name)

        list_request = bucket.list(
            prefix=prefix,
            delimiter='/'
        )
        keys = []
        prefixes = []
        try:
            responses = [resp for resp in list_request]
            
            keys = [resp.size for resp in responses if isinstance(resp, 
                boto.s3.key.Key)]

            prefixes = [resp.name for resp in responses if isinstance(resp, 
                boto.s3.prefix.Prefix)]

        except Exception as ex:
            pass

        self._after_fetch(bucket_name, prefixes, keys)

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)

    parser.add_argument(
        '--project_id', 
        '-p', 
        help='Name of the project'
    )

    parser.add_argument(
        '--bucket_id', 
        '-b',
        help='gcs or aws s3 bucket id'
    )

    parser.add_argument(
        '--max_thread', 
        '-m',
        help='Number of parallel connection that you want to use',
        type=int,
        default=100
    )

    parser.add_argument(
        '--quiet', 
        '-q',
        help="Run in silent mode i.e. display only final result",
        default=False,
        action='store_true'
    )

    parser.add_argument(
        '--human_readable', 
        '-r',
        help='Produce human readble output eg 18 MB or 201 GB',
        default=True,
        action='store_false'
    )

    parser.add_argument(
        '--config', 
        '-c',
        help='Configuration to use',
        type=str,
        choices=['development', 'test', 'production', 'default'],
        default='default'
    )

    parser.add_argument(
        '--server',
        '-s',
        help='Server type (gcs, s3)',
        type=str,
        choices=['gcs', 's3'],
        required=True
    )

    args = parser.parse_args()

    config = Config()
    config.from_object(settings[args.config])

    task = None
    if args.server.lower() == 'gcs':
        key_file = config[args.project_id.upper()]['json_key_file']
        scopes = config['SCOPES']['STORAGE']['READ_ONLY']
        
        credentials = credentials_from_json_keyfile_name(key_file, scopes)

        task = GCSSizeTask(
            project_id=args.project_id.lower(),
            credentials=credentials,
            bucket_name=args.bucket_id,
            max_thread=args.max_thread
        )
    elif args.server.lower() == 's3':
        credentials = config[args.project_id.upper()]

        task = S3SizeTask(
            bucket_name=args.bucket_id,
            max_thread=args.max_thread,
            credentials=credentials
        )

    if task != None: 
        task.start()
