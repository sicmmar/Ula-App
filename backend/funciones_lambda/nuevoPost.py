import boto3
import base64
import uuid
from io import BytesIO
from datetime import date, datetime
        
dynamo = boto3.client('dynamodb',
        region_name='us-east-2')

rek = boto3.client('rekognition',
        region_name='us-east-2')
        
s3 = boto3.client('s3',
        region_name='us-east-2')
        
translate = boto3.client('translate',
        region_name='us-east-2')
        
BUCKET_NAME='imagenes-ula'
URL_BUCKET = 'https://imagenes-ula.s3.us-east-2.amazonaws.com/'
        
def lambda_handler(event, context):
    hoy = datetime.now()
    username = event['username']
    descripcion = event['descripcion']
    departamento = event['departamento']
    lugar = event['lugar']
    pais = event['pais']
    nFoto = event['nFoto']
    ext = event['ext']
    b64 = event['b64']
    guardar = event['guardar']
    fechahora = str(hoy.strftime("%B %d, %Y %H:%M:%S"))
    uniqueID = uuid.uuid1().time_low

    starter = b64.find(',')
    image_data = b64[starter+1:]
    image_data = bytes(image_data, encoding="ascii")
    ubicacion = 'fotos_publicadas/' + nFoto + '-' + str(uniqueID) + '.' + ext 

    s3.upload_fileobj(
        BytesIO(base64.b64decode(image_data)),
        BUCKET_NAME,
        ubicacion,
        ExtraArgs={'ACL': 'public-read'}
    )

    dynamo.put_item(
        TableName='publicacion',
        Item = {
            'id_pub': {'N': str(uniqueID)},
            'username': {'S': username},
            'descripcion' : {'S': descripcion},
            'departamento': {'S': departamento},
            'pais':{'S': pais},
            'lugar': {'S': lugar},
            'foto': {'S': URL_BUCKET + ubicacion},
            'fechahora': {'S': fechahora}
        }
    )

    #se guarda en el album personal
    if guardar:
        respuesta = rek.detect_labels(
            Image={
                'S3Object':{
                        'Bucket':BUCKET_NAME,'Name': ubicacion
                    }
                },
            MaxLabels=2)
        
        etiq = []
        for x in respuesta['Labels']:
            response = translate.translate_text(Text=x['Name'],SourceLanguageCode='en',TargetLanguageCode='es')
            etiq.append(response['TranslatedText'])


        albumes = usuarioExistente(username)['album']
        
        for label in etiq:
            existe = False
            x = 0
            while not existe and x < len(albumes['L']):
                if albumes['L'][x]['L'][0]['S'] == label:
                    existe = True
                    albumes['L'][x]['L'][1]['L'].append({'L':[{'S':nFoto},{'S': descripcion},{'S': URL_BUCKET + ubicacion}]})
                x+=1
            
            if not existe:
                albumes['L'].append({'L': [{'S':label},{'L':[{'L':[{'S':nFoto},{'S': descripcion},{'S': URL_BUCKET + ubicacion}]}]}]})

                
        dynamo.update_item(
            TableName='usuario',
            Key = {
                'username': {'S': username}
            },
            UpdateExpression = 'set album=:nal',
            ExpressionAttributeValues = {
                ':nal': albumes
            }
        )

    return {'hoy': fechahora, 'status': 202}
    

def usuarioExistente(usernam):
    existe = dynamo.get_item(
        TableName='usuario',
        Key = {
            'username': {'S': usernam}
        }
    )

    return existe.get('Item')