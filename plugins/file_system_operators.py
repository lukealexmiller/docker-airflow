import os, fnmatch, re
import logging

from shutil import copyfile
from datetime import datetime

from airflow.plugins_manager import AirflowPlugin
from airflow.contrib.hooks.fs_hook import FSHook
from airflow.models import BaseOperator
from airflow.operators.sensors import BaseSensorOperator
from airflow.utils.decorators import apply_defaults

# You can also make this format a parameter in the Operator, for example
# if you expect that you work with different intervals than "@daily". 
# Then you can introduce time components to have a finer grain for file storage.
DATE_FORMAT = '%Y%m%d'


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
            minimum_number=None,
            maximum_number=None,
            hook=FSHook,
            *args, **kwargs):
        super(FileSystemSensor, self).__init__(*args, **kwargs)
        self.filepath = filepath
        self.fs_conn_id = fs_conn_id
        self.file_size = file_size
        self.accepted_ext = accepted_ext
        self.minimum_number = minimum_number
        self.maximum_number = maximum_number
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

    @staticmethod
    def threshold_on_file_number(files, minimum_number=None, maximum_number=None):
        """
        Threshold based on number of files in directory.

        :param files: (list) of file paths
        :param minimum_number: (int) minimum file number threshold
        :param maximum_number: (int) maximum file number threshold
        :return: (bool) result of thresholding
        """
        if (minimum_number is not None) or (maximum_number is not None):
            if len(files) >= maximum_number:
                logging.info('FileSystemSensor.poke: max. threshold of %d exceeded. Number of files in full_path: %d', 
                            maximum_number, len(files))
                return False

            elif len(files) <= minimum_number:
                logging.info('FileSystemSensor.poke: below threshold of %d. Number of files in full_path: %d', 
                            minimum_number, len(files))
                return False
        logging.info('FileSystemSensor.poke: Thresholds satisfied. Number of files in full_path: %d', 
                            len(files))
        return True

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
            trig = self.threshold_on_file_number(files, self.minimum_number, self.maximum_number)
            return trig
        except:
            logging.exception('')
            return False


class FileToPredictableLocationOperator(BaseOperator):
    """
    Picks up a file from somewhere and lands this in a predictable location elsewhere
    """
    template_fields = ('file_mask',)

    @apply_defaults
    def __init__(self,
                 src_conn_id,
                 dst_conn_id,
                 file_mask,
                 *args,
                 **kwargs):
        """
        :param src_conn_id: Hook with a conn id that points to the source directory.
        :type src_conn_id: string
        :param dst_conn_id: Hook with a conn id that points to the destination directory.
        :type dst_conn_id: string
        """
        super(FileToPredictableLocationOperator, self).__init__(*args, **kwargs)
        self.src_conn_id = src_conn_id
        self.dst_conn_id = dst_conn_id
        self.file_mask = file_mask

    def execute(self, context):
        """
        Picks up all files from a source directory and dumps them into a root directory system,
        organized by dagid, taskid and execution_date
        """
        execution_date = context['execution_date'].strftime(DATE_FORMAT)
        src_hook = FSHook(conn_id=self.src_conn_id)
        source_dir = src_hook.get_path()

        dest_hook = FSHook(conn_id=self.dst_conn_id)
        dest_root_dir = dest_hook.get_path()

        dag_id = self.dag.dag_id
        task_id = self.task_id

        logging.info("Now searching for files like {0} in {1}".format(self.file_mask, source_dir))
        file_names = fnmatch.filter(os.listdir(source_dir), self.file_mask)
        for file_name in file_names:
            full_path = os.path.join(source_dir, file_name)
            dest_dir = os.path.join(dest_root_dir, dag_id, task_id, execution_date)
            logging.info("Now creating path structure {0}".format(dest_dir))
            os.makedirs(dest_dir)
            dest_file_name = os.path.join(dest_dir, os.path.basename(file_name))
            logging.info("Now moving {0} to {1}".format(full_path, dest_file_name))
            copyfile(full_path, dest_file_name)


class PredictableLocationToFinalLocationOperator(BaseOperator):
    """
    Picks up a file from predictable location storage and loads/transfers the results to 
    a target system (in this case another directory, but it could be anywhere).
    """
    @apply_defaults
    def __init__(self,
                 src_conn_id,
                 dst_conn_id,
                 src_task_id,
                 *args,
                 **kwargs):
        """
        :param src_conn_id: Hook with a conn id that points to the source directory.
        :type src_conn_id: string
        :param dst_conn_id: Hook with a conn id that points to the destination directory.
        :type dst_conn_id: string
        :param src_task_id: Source task that produced the file of interest
        :type src_task_id: string
        """
        super(PredictableLocationToFinalLocationOperator, self).__init__(*args, **kwargs)
        self.src_conn_id = src_conn_id
        self.dst_conn_id = dst_conn_id
        self.src_task_id = src_task_id

    def execute(self, context):
        """
        Picks up all files from a source directory and dumps them into a root directory system,
        organized by dagid, taskid and execution_date
        """
        execution_date = context['execution_date'].strftime(DATE_FORMAT)
        src_hook = FSHook(conn_id=self.src_conn_id)
        dest_hook = FSHook(conn_id=self.dst_conn_id)
        dest_dir = dest_hook.get_path()

        dag_id = self.dag.dag_id

        source_dir = os.path.join(src_hook.get_path(), dag_id, self.src_task_id, execution_date)
        if os.path.exists(source_dir):
            for file_name in os.listdir(source_dir):
                full_path = os.path.join(source_dir, file_name)
                dest_file_name = os.path.join(dest_hook.get_path(), file_name)
                logging.info("Now moving {0} to final destination {1}".format(full_path, dest_file_name))
                copyfile(full_path, dest_file_name)


class FileSystemPlugin(AirflowPlugin):
    name = "file_system_plugin"
    operators = [FileSystemSensor, FileToPredictableLocationOperator, PredictableLocationToFinalLocationOperator]