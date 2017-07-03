from airflow import DAG
from airflow.operators.dagrun_operator import TriggerDagRunOperator
from airflow.operators.python_operator import PythonOperator
from datetime import datetime, timedelta

import pprint

pp = pprint.PrettyPrinter(indent=4)


def conditionally_trigger(context, dag_run_obj):
    #print(context)
    """This function decides whether or not to Trigger the remote DAG"""
    c_p =context['params']['condition_param']
    print("Controller DAG : conditionally_trigger = {}".format(c_p))
    if context['params']['condition_param']:
        dag_run_obj.payload = {'message': context['params']['message']}
        pp.pprint(dag_run_obj.payload)
        return dag_run_obj

def scan_directory():
    pass

seven_days_ago = datetime.combine(datetime.today() - timedelta(1),
                                  datetime.min.time())

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

# Define the DAG
dag = DAG(dag_id='local_directory_controller_dag',
          default_args=default_args,
          schedule_interval='@once')

# Define the single task in this controller DAG
t2 = TriggerDagRunOperator(
    task_id='trigger_dagrun',
    trigger_dag_id="face_blur_dag",
    python_callable=conditionally_trigger,
    params={'condition_param': True,
            'message': 'Hello World'},
    dag=dag)

# Define additional task in controller DAG
t1 = PythonOperator(
    task_id='run_this',
    provide_context=True,
    python_callable=scan_directory,
    dag=dag)
