import os
import re
import logging

from airflow.plugins_manager import AirflowPlugin
from airflow.operators.sensors import BaseSensorOperator
from airflow.contrib.hooks.fs_hook import FSHook
from airflow.utils.decorators import apply_defaults

#TODO: Is the class FileSystemPlugin(): usage correct?

class FileSystemSensor(BaseSensorOperator):
    """
    Waits for the existence of a file in a directory on a filesystem

    :param fs_conn_id: connection ID defined in Admin/Connections (Webserver)
    :type fs_conn_id: string
    :param filepath: folder name (relative to the base path associated with fs_conn_id)
    :type filepath: string
    :param accepted_ext: accepted file extensions
    :type accepted_ext: list (strings)
    :param file_size: minimum file size
    :type file_size: float
    :param hook: enables interfacing with filesystem
    :type hook: class
    """
    template_fields = tuple()
    ui_color = '#91818a'

    @apply_defaults
    def __init__(
            self,
            filepath='',
            fs_conn_id='fs_default',
            accepted_ext=None,
            file_size=None,
            hook=FSHook,
            *args, **kwargs):
        super(FileSystemSensor, self).__init__(*args, **kwargs)
        self.filepath = filepath
        self.fs_conn_id = fs_conn_id
        self.file_size = file_size
        self.accepted_ext = accepted_ext
        self.hook = hook

    @staticmethod
    def filter_for_filesize(files, file_size=None):
        """
        Filter the files by checking if size >= self.filesize

        :param files: (list) of file paths
        :param size: (float) defining minimum file size in MB
        :return: (list) of file paths which have minimum file size
        """
        if file_size is not None:
            logging.debug('Filtering for file size >= %s MB in files: %s', file_size, map(lambda x: x, files))
            # Convert from MB to bytes. Note this is in powers of 2
            file_size *= 2**10
            files = [x for x in files if os.path.getsize(x) >= file_size]
        logging.info('FileSystemSensor.poke: number of files after size filter is %d', len(files))
        return files

    @staticmethod
    def filter_for_accepted_ext(files, accepted_ext=None):
        """
        Filter the files by checking if file has accepted extension(s) (if defined)

        :param files: (list) of file paths
        :param ignored_ext: (list) of accepted file extensions
        :return: (list) of file paths which have accepted extension(s)
        """
        if accepted_ext is not None:
            regex_builder = "^.*\.(%s$)$" % '$|'.join(accepted_ext)
            accepted_extensions_regex = re.compile(regex_builder)
            logging.debug('Filtering files for accepted extentions: %s in files: %s', accepted_extensions_regex.pattern,
                          map(lambda x: x, files))
            files = [x for x in files if accepted_extensions_regex.match(x)]
        logging.info('FileSystemSensor.poke: number of files after ext filter is %d', len(files))
        return files

    def poke(self, context):
        fs = self.hook(self.fs_conn_id)
        basepath = fs.get_path()
        full_path = "/".join([basepath, self.filepath])
        logging.info('Poking for file {full_path} '.format(**locals()))
        try:
            # Create flattened list of all files in full_path and its subdirectories
            files = [val for sublist in [[os.path.join(i[0], j) for j in i[2]] for i in os.walk(full_path)] for val in sublist]
            logging.info('FileSystemSensor.poke: number of files is %d', len(files))
            files = self.filter_for_accepted_ext(files, self.accepted_ext)
            files = self.filter_for_filesize(files, self.file_size)
            return bool(files)
        except:
            logging.exception('')
            return False

class FileSystemPlugin(AirflowPlugin):
    name = "file_system_plugin"
    operators = [FileSystemSensor]