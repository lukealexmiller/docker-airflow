import os
from datetime import datetime,timedelta
import pprint

import airflow
from airflow.models import DAG
from airflow.operators import FileSystemSensor
from airflow.operators.dagrun_operator import TriggerDagRunOperator

pp = pprint.PrettyPrinter(indent=4)

def conditionally_trigger(context, dag_run_obj):
    """This function decides whether or not to trigger the remote DAG"""
    print(context)
    c_p =context['params']['condition_param']
    print("Controller DAG : conditionally_trigger = {}".format(c_p))
    if context['params']['condition_param']:
        dag_run_obj.payload = {'message': context['params']['message']}
        pp.pprint(dag_run_obj.payload)
        return dag_run_obj

default_args = {
    'owner': 'lukealexmiller',
    'depends_on_past': False,
    'start_date': airflow.utils.dates.days_ago(2),
    'email': ['lm@cartwatch.de'],
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=1),
    'provide_context': True
    }

#CHECK THESE
dag = DAG(
        dag_id='sense_raw_data_hdd_and_trigger_import',
        default_args=default_args,
        schedule_interval='@once')

t1 = FileSystemSensor(
        task_id='sense_raw_data_hdd',
        poke_interval=60,
        timeout=60*60*24*7,
        filepath='raw_data',
        fs_conn_id='fs_syno',
        file_size=None,
        minimum_number=None,
        maximum_number=None,
        accepted_ext=['mp4'],
        dag=dag)

t2 = TriggerDagRunOperator(
    task_id='trigger_raw_data_import_dag',
    trigger_dag_id="raw_data_import_dag",
    python_callable=conditionally_trigger,
    params={'condition_param': True,
            'message': 'Hello World'},
    dag=dag)

#t0.run(start_date=datetime(2016,1,1), end_date=datetime(2016,1,1), 
#ignore_ti_state=True)
t2.set_upstream(t1)