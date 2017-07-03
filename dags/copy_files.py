from __future__ import print_function
import airflow
from datetime import datetime, timedelta
from airflow.operators import FileToPredictableLocationOperator
from airflow.operators import PredictableLocationToFinalLocationOperator


seven_days_ago = datetime.combine(
    datetime.today() - timedelta(7),
    datetime.min.time())

args = {
    'owner': 'airflow',
    'start_date': seven_days_ago,
    'provide_context': True
}

dag = airflow.DAG(
    'file_ingest',
    schedule_interval="@daily",
    dagrun_timeout=timedelta(minutes=60),
    default_args=args,
    max_active_runs=1)

pick_up_file = FileToPredictableLocationOperator(
    task_id='pick_up_file',
    src_conn_id='fs_source_system',
    dst_conn_id='fs_archive',
    file_mask="some_file_pattern_{{ ds_nodash }}",
    dag=dag)

load_file = PredictableLocationToFinalLocationOperator(
    task_id='load_file',
    src_conn_id='fs_archive',
    dst_conn_id='fs_target',
    src_task_id='pick_up_file',
    dag=dag)

pick_up_file >> load_file


if __name__ == "__main__":
    dag.cli()