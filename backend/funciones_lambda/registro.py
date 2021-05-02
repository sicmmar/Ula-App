import boto3
import base64
import uuid
from io import BytesIO
        
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
    usern = event['username']
    nombre = event['nombre']
    passw = event['contrasena']
    pais = event['pais']
    nFoto = event['nFoto']
    ext = event['ext']
    b64 = event['b64']
    uniqueID = str(uuid.uuid1().time_low)

    if not usern or not nombre or not passw or not nFoto:
        return {'status': 504,'existe': ''}

    if usuarioExistente(usern):
        return {'status': 404,'existe':'true'}

    starter = b64.find(',')
    image_data = b64[starter+1:]
    image_data = bytes(image_data, encoding="ascii")
    ubicacion = 'fotos_perfil/' + nFoto + '-' + uniqueID + '.' + ext 

    s3.upload_fileobj(
        BytesIO(base64.b64decode(image_data)),
        BUCKET_NAME,
        ubicacion,
        ExtraArgs={'ACL': 'public-read'}
    )
    #res = s3.upload_file("foto","practica2-g45-imagenes",foto)

    response = rek.detect_faces(Image={
            'S3Object':{
                    'Bucket':BUCKET_NAME,'Name': ubicacion
                }
            },Attributes=['ALL'])
    #response = rek.detect_faces(Image={'S3Object':{'Bucket':BUCKET_NAME, 'Name': nombre[1]}},Attributes=['ALL'])
    etiq = []   
    for aspectos in response['FaceDetails']:
        if aspectos['AgeRange']: etiq.append({'S':str(aspectos['AgeRange']['Low']) + "-" + str(aspectos['AgeRange']['High']) + " años"})
        if aspectos['Beard']: etiq.append({'S':"Con Barba" if aspectos['Beard']['Value'] else "Sin Barba"})
        if aspectos['Eyeglasses']: etiq.append({'S':'Usa Lentes' if aspectos['Eyeglasses']['Value'] else "No usa lentes"})
        if aspectos['EyesOpen']: etiq.append({'S':"Ojos Abiertos" if aspectos['EyesOpen']['Value'] else "Ojos Cerrados"})
        if aspectos['Gender']: etiq.append({'S':translate.translate_text(Text=aspectos['Gender']['Value'],SourceLanguageCode='en',TargetLanguageCode='es')['TranslatedText']})
        if aspectos['Smile']: etiq.append({'S':"Sonriendo" if aspectos['Smile']['Value'] else "Sin Sonreír"})
        if aspectos['Emotions']:
            for emociones in aspectos['Emotions']:
                if emociones['Confidence'] >= 60: etiq.append({'S':translate.translate_text(Text=emociones['Type'],SourceLanguageCode='en',TargetLanguageCode='es')['TranslatedText']})
    
    dynamo.put_item(
        TableName='usuario',
        Item = {
            'username': {'S': usern},
            'nombre': {'S': nombre},
            'pais':{'S': pais},
            'contrasena': {'S': passw},
            'nFoto' : {'S': nFoto + '-' + uniqueID + '.' + ext},
            'foto_perfil': {'S': URL_BUCKET + ubicacion},
            'etiquetas': {'L': etiq},
            'album':{'L':[{'L': [{'S':'Perfil'},{'L':[{'S': URL_BUCKET + ubicacion}]}]}]}       
        }
    )

    return {'status': 202,'existe': "false"}
    

def usuarioExistente(usernam):
    existe = dynamo.get_item(
        TableName='usuario',
        Key = {
            'username': {'S': usernam}
        }
    )

    return existe.get('Item')