"""
Airflow DAG で GCP VertexAI Pipeline のステータスを監視
すべての running 状態で実行時間が 2 日を超える pipeline を監視し、
Teams Webhook を通じて通知を送信
"""

from datetime import datetime, timedelta
from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.models import Variable
from google.cloud import aiplatform
import requests
import json
from typing import List, Dict
import pendulum

# ============================
# DAG デフォルトパラメータ設定
# ============================
default_args = {
    'owner': 'airflow',
    'depends_on_past': False,
    'email_on_failure': False,
    'email_on_retry': False,
    'retries': 1,
    'retry_delay': timedelta(minutes=5),
}

# ============================
# GCP 設定パラメータ（実際の状況に応じて変更してください）
# ============================
GCP_PROJECT_ID = Variable.get("gcp_project_id", default_var="your-project-id")
GCP_REGION = Variable.get("gcp_region", default_var="us-central1")

# Teams Webhook URL（Airflow Variables で設定してください）
TEAMS_WEBHOOK_URL = Variable.get("teams_webhook_url", default_var="your-webhook-url")

# 監視しきい値：2 日
DURATION_THRESHOLD_DAYS = 2


# ============================
# Task 1: VertexAI Pipeline の監視
# ============================
def monitor_vertex_ai_pipelines(**context):
    """
    すべての running 状態の VertexAI Pipeline を監視
    Duration が 2 日を超えているかチェック
    タイムアウトした pipeline 情報のリストを返す
    """
    print(f"VertexAI Pipeline の監視を開始 - プロジェクト: {GCP_PROJECT_ID}, リージョン: {GCP_REGION}")
    
    # Vertex AI を初期化
    aiplatform.init(project=GCP_PROJECT_ID, location=GCP_REGION)
    
    # すべての Pipeline Jobs を取得
    pipeline_jobs = aiplatform.PipelineJob.list(
        filter='state="PIPELINE_STATE_RUNNING"',
        order_by='create_time desc'
    )
    
    current_time = datetime.now()
    threshold_duration = timedelta(days=DURATION_THRESHOLD_DAYS)
    overtime_pipelines = []
    
    print(f"running 状態の pipeline を {len(pipeline_jobs)} 件発見")
    
    for job in pipeline_jobs:
        try:
            # pipeline 作成時刻を取得
            create_time = job.create_time
            
            # 実行時間を計算
            duration = current_time - create_time.replace(tzinfo=None)
            
            print(f"Pipeline: {job.display_name}")
            print(f"  - 作成時刻: {create_time}")
            print(f"  - 実行時間: {duration}")
            
            # しきい値を超えているかチェック
            if duration > threshold_duration:
                pipeline_info = {
                    'name': job.display_name,
                    'resource_name': job.resource_name,
                    'url': f"https://console.cloud.google.com/vertex-ai/pipelines/runs/{job.name.split('/')[-1]}?project={GCP_PROJECT_ID}",
                    'create_time': create_time.isoformat(),
                    'duration_days': duration.days,
                    'duration_hours': duration.seconds // 3600,
                    'state': job.state.name
                }
                overtime_pipelines.append(pipeline_info)
                print(f"  ⚠️ タイムアウト Pipeline 発見！実行時間: {duration.days} 日 {duration.seconds // 3600} 時間")
        
        except Exception as e:
            print(f"pipeline {job.display_name} の処理中にエラー: {str(e)}")
            continue
    
    print(f"\n要約: タイムアウトした pipeline を {len(overtime_pipelines)} 件発見")
    
    # 結果を XCom にプッシュし、次の task で使用
    context['ti'].xcom_push(key='overtime_pipelines', value=overtime_pipelines)
    
    return overtime_pipelines


# ============================
# Task 2: Teams 通知を送信
# ============================
def send_teams_notification(**context):
    """
    XCom からタイムアウトした pipeline 情報を取得
    Teams Webhook を通じて通知を送信
    """
    # 前の task からデータを取得
    ti = context['ti']
    overtime_pipelines = ti.xcom_pull(task_ids='monitor_pipelines', key='overtime_pipelines')
    
    if not overtime_pipelines:
        print("タイムアウトした pipeline はありません、通知送信不要")
        return "No overtime pipelines"
    
    print(f"{len(overtime_pipelines)} 件のタイムアウト pipeline の通知を送信準備中")
    
    # Teams メッセージカードを構築
    message_card = create_teams_message_card(overtime_pipelines)
    
    # Teams Webhook に送信
    try:
        response = requests.post(
            TEAMS_WEBHOOK_URL,
            headers={'Content-Type': 'application/json'},
            data=json.dumps(message_card),
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Teams 通知の送信成功")
            return f"Successfully sent notification for {len(overtime_pipelines)} pipelines"
        else:
            print(f"❌ Teams 通知の送信失敗: {response.status_code} - {response.text}")
            raise Exception(f"Teams webhook failed with status {response.status_code}")
    
    except Exception as e:
        print(f"Teams 通知送信中にエラー: {str(e)}")
        raise


# ============================
# ヘルパー関数: Teams メッセージカードを作成
# ============================
def create_teams_message_card(pipelines: List[Dict]) -> Dict:
    """
    フォーマット済みの Teams メッセージカードを作成
    """
    # pipeline リストの HTML フォーマットを構築
    pipeline_details = ""
    for idx, pipeline in enumerate(pipelines, 1):
        pipeline_details += f"""
**{idx}. {pipeline['name']}**  
- 🕐 実行時間: {pipeline['duration_days']} 日 {pipeline['duration_hours']} 時間  
- 📅 作成時刻: {pipeline['create_time']}  
- 🔗 [Pipeline を表示]({pipeline['url']})  
- 📊 ステータス: {pipeline['state']}  

---
"""
    
    message_card = {
        "@type": "MessageCard",
        "@context": "https://schema.org/extensions",
        "summary": "VertexAI Pipeline タイムアウト警告",
        "themeColor": "FF0000",  # 赤色は警告を表す
        "title": "⚠️ VertexAI Pipeline 実行タイムアウト警告",
        "sections": [
            {
                "activityTitle": "長時間実行中の Pipeline を検出",
                "activitySubtitle": f"{DURATION_THRESHOLD_DAYS} 日を超えて実行中の Pipeline を {len(pipelines)} 件発見",
                "facts": [
                    {
                        "name": "プロジェクト",
                        "value": GCP_PROJECT_ID
                    },
                    {
                        "name": "リージョン",
                        "value": GCP_REGION
                    },
                    {
                        "name": "検出時刻",
                        "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    },
                    {
                        "name": "タイムアウトしきい値",
                        "value": f"{DURATION_THRESHOLD_DAYS} 日"
                    }
                ],
                "text": pipeline_details
            }
        ],
        "potentialAction": [
            {
                "@type": "OpenUri",
                "name": "Vertex AI Console を表示",
                "targets": [
                    {
                        "os": "default",
                        "uri": f"https://console.cloud.google.com/vertex-ai/pipelines?project={GCP_PROJECT_ID}"
                    }
                ]
            }
        ]
    }
    
    return message_card


# ============================
# DAG 定義
# ============================
# 東京タイムゾーンを設定
tokyo_tz = pendulum.timezone('Asia/Tokyo')

with DAG(
    dag_id='vertexai_pipeline_monitor',
    default_args=default_args,
    description='VertexAI Pipeline のステータスを監視し Teams 通知を送信',
    schedule_interval='0 16 * * *',  # 毎日午後 4 時に実行 (cron 形式: 分 時 日 月 曜日)
    start_date=datetime(2025, 10, 1, tzinfo=tokyo_tz),
    catchup=False,
    tags=['vertexai', 'monitoring', 'teams'],
    default_view='graph',
    timezone=tokyo_tz,  # 東京時間（JST UTC+9）で午後 4 時に実行
) as dag:
    
    # Task 1: VertexAI Pipeline の監視
    monitor_task = PythonOperator(
        task_id='monitor_pipelines',
        python_callable=monitor_vertex_ai_pipelines,
        provide_context=True,
    )
    
    # Task 2: Teams 通知を送信
    notify_task = PythonOperator(
        task_id='send_teams_notification',
        python_callable=send_teams_notification,
        provide_context=True,
    )
    
    # タスク依存関係を定義
    monitor_task >> notify_task


# ============================
# 説明ドキュメント
# ============================
"""
設定説明：
==========

1. 依存パッケージのインストール：
   pip install apache-airflow google-cloud-aiplatform requests

2. Airflow Variables で以下の変数を設定：
   - gcp_project_id: あなたの GCP プロジェクト ID
   - gcp_region: VertexAI のリージョン（例：us-central1）
   - teams_webhook_url: Teams Webhook URL

3. GCP 認証：
   Airflow 実行環境が GCP VertexAI にアクセスできる権限を確保
   以下のいずれかの方法で：
   - GOOGLE_APPLICATION_CREDENTIALS 環境変数を設定
   - GCP Composer のデフォルトサービスアカウントを使用
   - Airflow Connection を設定

4. Teams Webhook 設定：
   Microsoft Teams で：
   - 対象チャネルに入る
   - "..." をクリック -> "コネクタ" -> "受信 Webhook"
   - Webhook を作成して URL をコピー
   - Airflow Variables で teams_webhook_url として設定

5. スケジュール時間：
   現在は毎日東京時間（JST）午後 4 時（16:00）に実行するよう設定
   タイムゾーンは pendulum.timezone('Asia/Tokyo') で指定
   変更する場合は schedule_interval パラメータまたは timezone を変更

使用例：
==========

# Airflow Variables を設定（Web UI またはコマンドラインで）
airflow variables set gcp_project_id "your-project-id"
airflow variables set gcp_region "us-central1"
airflow variables set teams_webhook_url "https://outlook.office.com/webhook/..."

# DAG をテスト
airflow dags test vertexai_pipeline_monitor 2025-10-29

# 手動実行をトリガー
airflow dags trigger vertexai_pipeline_monitor
"""

