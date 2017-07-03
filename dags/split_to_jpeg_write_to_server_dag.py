import os
#import av

from airflow.models import DAG
from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.operators import FileSystemSensor
from datetime import datetime, timedelta

import pprint
pp = pprint.PrettyPrinter(indent=4)

seven_days_ago = datetime.combine(datetime.today() - timedelta(1),
                                  datetime.min.time())

def split_video_to_jpeg_write_to_server(path_to_video):
	"""Decode video file and extract frames.
	"""
	pass
	
default_args = {
    'owner': 'lukealexmiller',
    'depends_on_past': False,
    'start_date': seven_days_ago,
    'email': ['lm@cartwatch.de'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5)
}

dag = DAG(
	dag_id='split_to_jpeg_write_to_server',
	default_args=default_args,
	schedule_interval=None)

t0 = FileSystemSensor(
        task_id='sense_number_jpeg_files_server',
        poke_interval=10, # adjust according to TF
        timeout=60*60*24*7,
        filepath='',
        fs_conn_id='fs_server_processing',
        file_size=None,
        accepted_ext=['jpg'],
        minimum_number=None,
        maximum_number=1000,
        provide_context=True,
        dag=dag)

t1 = PythonOperator(
    task_id='split_video_to_jpeg_write_to_server',
    provide_context=True,
    python_callable=split_video_to_jpeg_write_to_server,
    dag=dag)

t0 >> t1


#	container = av.open(path_to_video)
#	for frame in container.decode(video=0):
#    	frame.to_image().save('frame-%04d.jpg' % frame.index)