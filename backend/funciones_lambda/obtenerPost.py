import boto3
        
dynamo = boto3.client('dynamodb',
        region_name='us-east-2')
        
def lambda_handler(event, context):
    lista = dynamo.scan(
        TableName='publicacion'
    )

    return {'items':lista['Items'], 'tam': lista['Count']}