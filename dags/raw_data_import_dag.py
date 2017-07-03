import airflow
from datetime import datetime, timedelta
from airflow.operators import FileToPredictableLocationOperator
from airflow.operators import PredictableLocationToFinalLocationOperator


seven_days_ago = datetime.combine(
    datetime.today() - timedelta(7),
    datetime.min.time())

args = {
    'owner': 'lukealexmiller',
    'start_date': seven_days_ago,
    'provide_context': True
}

dag = airflow.DAG(
    dag_id='raw_data_import_dag',
    schedule_interval="@daily",
    dagrun_timeout=timedelta(minutes=60),
    default_args=args,
    max_active_runs=1)

pick_up_file = FileToPredictableLocationOperator(
    task_id='raw_data_import_to_syno',
    src_conn_id='fs_syno_external_hdd',
    dst_conn_id='fs_syno',
    file_mask="some_file_pattern_{{ ds_nodash }}",
    dag=dag)

load_file = PredictableLocationToFinalLocationOperator(
    task_id='load_file',
    src_conn_id='fs_archive',
    dst_conn_id='fs_target',
    src_task_id='pick_up_file',
    dag=dag)

#pick_up_file >> load_file


if __name__ == "__main__":
    dag.cli()