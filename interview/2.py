import boto3
import os
import datetime
def lambda_handler(event, context):
    instance_id = os.environ['INSTANCE_ID']
    current_date = datetime.datetime.now().strftime("%Y/%m")
    directory_path = "/usr/local/wtsbatch/data/WMS/backup/OrderPending/"
    file_patterns = [
        f"AS01_OrderPendingData_{current_date}*.CSV",
        f"MS01_OrderPendingData_{current_date}*.CSV",
        f"MS02_OrderPendingData_{current_date}*.CSV",
        f"MS04_OrderPendingData_{current_date}*.CSV",
        f"MS05_OrderPendingData_{current_date}*.CSV",
        f"MS06_OrderPendingData_{current_date}*.CSV",
        f"MS07_OrderPendingData_{current_date}*.CSV",
        f"HL017HW_MS21_{current_date}*.CSV.csv"
    ]
    ssm_client = boto3.client('ssm', region_name='ap-northeast-1')
    try:
        missing_file_types = []
        for pattern in file_patterns:
            command = f"ls {directory_path} | grep '{pattern}'"
            response = ssm_client.send_command(
                InstanceIds=[instance_id],
                DocumentName="AWS-RunShellScript",
                Parameters={'commands': [command]}
            )
            command_id = response['Command']['CommandId']
            waiter = ssm_client.get_waiter('command_executed')
            waiter.wait(CommandId=command_id, InstanceId=instance_id, WaiterConfig={'Delay': 15, 'MaxAttempts': 10})
            output = ssm_client.get_command_invocation(
                CommandId=command_id,
                InstanceId=instance_id
            )
            result = output['StandardOutputContent'].strip()
            print(result)
            
            if not result:
                missing_file_types.append(pattern.split('_')[0])
        if missing_file_types:
            error_message = f"Error: The following file types do not exist: {', '.join(missing_file_types)}"
            print(error_message)
            return {
                'statusCode': 500,
                'body': error_message
            }
        else:
            print("All file types exist")
            return {
                'statusCode': 200,
                'body': "Success: All file types exist"
            }
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        return {
            'statusCode': 500,
            'body': str(e)
        }