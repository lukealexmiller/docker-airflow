from airflow.operators.bash_operator import BashOperator
from airflow.operators.python_operator import PythonOperator
from airflow.models import DAG
from datetime import datetime,timedelta

import os

args = {'start_date': datetime(2016,1,1),
        'owner': 'airflow',
        'provide_context': True }

dag = DAG(
        dag_id='fs2',
        default_args=args,
        schedule_interval='@once')


def run_this_func(ds, **kwargs):
    print("Remotely received value of {} for key=message".format(kwargs['dag_run'].conf['message']))

t0 = PythonOperator(
    task_id='run_this',
    provide_context=True,
    python_callable=run_this_func,
    dag=dag)

t1 = BashOperator(
        task_id='Bash_Task',
        bash_command='cp ~/airflow/dags/trigger.py ~/airflow/dags/tt.txt',
        dag=dag)

t0.run(start_date=datetime(2016,1,1), end_date=datetime(2016,1,1), 
ignore_ti_state=True)
#t1.set_upstream(t0)