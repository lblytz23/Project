import boto3
import os
import datetime
 
FILE_PATH = "/usr/local/wtsbatch/log/MonthlyQueryPrepareBatch.sh.log"
 
def lambda_handler(event, context):
    instance_id = os.environ['INSTANCE_ID']
    check_content_command = f"tail -n 1 {FILE_PATH}"
    current_date = datetime.datetime.now().strftime("%Y/%m/%d")
 
    ssm_client = boto3.client('ssm', region_name='ap-northeast-1')
    try:
        # Check the content of the file
        response = ssm_client.send_command(
            InstanceIds=[instance_id],
            DocumentName="AWS-RunShellScript",
            Parameters={'commands': [check_content_command]}
        )
        command_id = response['Command']['CommandId']
        waiter = ssm_client.get_waiter('command_executed')
        waiter.wait(CommandId=command_id, InstanceId=instance_id, WaiterConfig={'Delay': 15, 'MaxAttempts': 10})
 
        output = ssm_client.get_command_invocation(
            CommandId=command_id,
            InstanceId=instance_id
        )
        content_result = output['StandardOutputContent'].strip()
        print(content_result)
 
        # Check if the first 10 characters of the content match the current date
        print(content_result[:10])
        print('current_date:', current_date)
        if content_result[:10] == current_date:
            if content_result[-1] == "0":
                print("Success: The file content is as expected.")
                return {
                    'statusCode': 200,
                    'body': "Success: The file content is as expected."
                }
            elif content_result[-1] == "1":
                error_message = "Error: Status code is 1, please check the specific situation."
                print(error_message)
                return {
                    'statusCode': 500,
                    'body': error_message
                }
            else:
                error_message = "Error: Unknown status code in the file content."
                print(error_message)
                return {
                    'statusCode': 500,
                    'body': error_message
                }
        else:
            error_message = "Error: The shell script has not been executed."
            print(error_message)
            return {
                'statusCode': 500,
                'body': error_message
            }
    except Exception as e:
        print(f"Error executing command: {str(e)}")
        return {
            'statusCode': 500,
            'body': str(e)
        }