import os
import shutil
import logging

import airflow
from airflow import DAG
from datetime import datetime, timedelta
from airflow.operators.bash_operator import BashOperator
from airflow.operators import ShortCircuitOperator
from airflow.operators.python_operator import PythonOperator

default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'start_date': datetime.now(),
    'email': ['lm@cartwatch.de'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}
dag = DAG(
        dag_id='anonymiser_pipeline',
        default_args=default_args,
        schedule_interval=timedelta(minutes=1))


def identify_raw_data_to_copy(*args, **kwargs):
    raw_data_hdd_dir = kwargs["source_location"]
    logging.info('Accessing raw data on HDD at: {}'.format(raw_data_hdd_dir))
    raw_data_syno_dir = kwargs["target_location"]
    logging.info('Accessing raw data on Synology at: {}'.format(raw_data_syno_dir))
    valid_extension = kwargs["extension"]

    # Create flattened list of all files in raw_data dirs and their subdirectories
    raw_data_hdd_files = [val for sublist in [[os.path.join(i[0].replace(raw_data_hdd_dir+"/",""), j) for j in i[2]] for i in os.walk(raw_data_hdd_dir)] for val in sublist]
    raw_data_syno_files = [val for sublist in [[os.path.join(i[0].replace(raw_data_syno_dir+"/",""), j) for j in i[2]] for i in os.walk(raw_data_syno_dir)] for val in sublist]

    # Filter for files which have not already been moved to the synology
    raw_data_to_move = list(set(raw_data_hdd_files).difference(raw_data_syno_files))
    # Filter for files with correct extension
    logging.info('Filtering files for those with extension: {}'.format(valid_extension))
    raw_data_to_move = [file for file in raw_data_to_move if file.endswith(valid_extension)]
    return raw_data_to_move


def move_data_syno(*args, **kwargs):
    raw_data_hdd_dir = kwargs["source_location"]
    raw_data_syno_dir = kwargs["target_location"]
    ti = kwargs['task_instance']
    logging.info('Connected to XCOM {}'.format(ti))
    raw_data_to_move = ti.xcom_pull(task_ids='sense_raw_data_hdd')
    logging.info('Moving files: {}'.format(map(lambda x: x, raw_data_to_move)))

    # Move files which do not currently exist on the synology
    [shutil.move(os.path.join(raw_data_hdd_dir,file), os.path.join(raw_data_syno_dir,file)) for file in raw_data_to_move if not os.path.exist(os.path.join(raw_data_syno_dir,file))]


def list_jpeg_on_server(*args, **kwargs):
    raw_data_server_dir = kwargs["source_location"]
    raw_data_server_files = [val for sublist in [[os.path.join(i[0].replace(raw_data_server_dir+"/",""), j) for j in i[2]] for i in os.walk(raw_data_server_dir)] for val in sublist]
    return raw_data_server_files


def split_video_to_jpeg_write_to_server(*args, **kwargs):
    """Decode video file and extract frames.
    """
    raw_data_syno_dir = kwargs["source_location"]
    raw_data_server_dir = kwargs["target_location"]
    ti = kwargs['task_instance']
    raw_data_server_files = ti.xcom_pull(task_ids='list_jpeg_on_server')
    logging.info("Number of files currently on the server: {}".format(len(raw_data_server_files)))
    logging.info("Splitting to jpeg.")
    return


t_check_new_data_available = PythonOperator(
        task_id='sense_raw_data_hdd',
        python_callable=identify_raw_data_to_copy,
        op_kwargs={'source_location': '/usr/local/airflow/hdd',
                   'target_location': '/usr/local/airflow/syno',
                   'extension': '.mp4'},
        dag=dag)

t_move_new_data_to_syno = PythonOperator(
        task_id='move_new_data_to_syno',
        python_callable=move_data_syno,
        provide_context=True,
        op_kwargs={'source_location': '/usr/local/airflow/hdd',
                   'target_location': '/usr/local/airflow/syno'},
        dag=dag)

t_count_jpeg_on_server = PythonOperator(
        task_id='list_jpeg_on_server',
        python_callable=list_jpeg_on_server,
        op_kwargs={'source_location': '/usr/local/airflow/server'},
        dag=dag)

t_split_to_jpeg_write_to_server = PythonOperator(
        task_id='split_video_to_jpeg',
        python_callable=split_video_to_jpeg_write_to_server,
        provide_context=True,
        op_kwargs={'source_location': '/usr/local/airflow/syno',
                   'target_location': '/usr/local/airflow/server'},
        dag=dag)

t_move_new_data_to_syno.set_upstream([t_check_new_data_available])
t_split_to_jpeg_write_to_server.set_upstream([t_move_new_data_to_syno,t_count_jpeg_on_server])
