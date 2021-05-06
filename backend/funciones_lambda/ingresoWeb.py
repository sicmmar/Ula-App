import boto3
import base64
        
dynamo = boto3.client('dynamodb',
        region_name='us-east-2')

rek = boto3.client('rekognition',
        region_name='us-east-2')
        
BUCKET_NAME='imagenes-ula'
        
def lambda_handler(event, context):
    usern = event['username']
    imagen2 = event['foto'] #Foto nueva solo para ingresar.
    starter = imagen2.find(',')
    image_data = imagen2[starter+1:]
    image_data = bytes(image_data, encoding="ascii")

    if not usern:
        return {'status': 404,'Item': ''}

    item = usuarioExistente(usern)
    if item:
        respuesta = rek.compare_faces(
            SourceImage={
                'S3Object':{
                    'Bucket':BUCKET_NAME,'Name': 'fotos_perfil/' + item['nFoto']['S']
                    }
                }, 
            TargetImage={
                'Bytes':base64.b64decode(image_data)
                },
            SimilarityThreshold=81.5)

        if respuesta['FaceMatches'] == []:
            return {'status': 202,'Item':''}
        else:
            if respuesta['FaceMatches'][0]['Similarity'] >= 85:
                return {'status': 202,'Item': item}
            else: return {'status': 202,'Item': ''}

    return {'status': 303,'Item': ""}
    

def usuarioExistente(usernam):
    existe = dynamo.get_item(
        TableName='usuario',
        Key = {
            'username': {'S': usernam}
        }
    )

    return existe.get('Item')