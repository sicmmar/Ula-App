import json
import boto3
        
dynamo = boto3.client('dynamodb',
        region_name='us-east-2')
        
def lambda_handler(event, context):
    # TODO implement
    usern = event['username']
    passw = event['contrasena']

    if not usern or not passw:
        return {'status': 404,'Item': ''}

    item = usuarioExistente(usern)
    if item:
        if item['contrasena']['S'] == passw:
            return {'status': 202,'Item':item}
        
        return {'status': 202,'Item':''}

    return {'status': 303,'Item': ""}
    

def usuarioExistente(usernam):
    existe = dynamo.get_item(
        TableName='usuario',
        Key = {
            'username': {'S': usernam}
        }
    )

    return existe.get('Item')