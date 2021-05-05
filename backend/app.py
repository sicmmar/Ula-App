from credenciales import credenciales
from flask import Flask, request, jsonify
from flask_cors import CORS
from io import BytesIO
from datetime import date, datetime
import boto3,json, base64, uuid, time

app = Flask(__name__)
CORS(app) 

dynamo = boto3.client('dynamodb',
        region_name=credenciales.dynamodb['region'],
        aws_access_key_id=credenciales.dynamodb['accessKeyId'],
        aws_secret_access_key=credenciales.dynamodb['secretAccessKey']
    )

s3 = boto3.client('s3',
        region_name=credenciales.s3['region'],
        aws_access_key_id=credenciales.s3['accessKeyId'],
        aws_secret_access_key=credenciales.s3['secretAccessKey']
    )

rek = boto3.client('rekognition',
        region_name=credenciales.rekognition['region'],
        aws_access_key_id=credenciales.rekognition['accessKeyId'],
        aws_secret_access_key=credenciales.rekognition['secretAccessKey']
    )

translate = boto3.client('translate',
        region_name=credenciales.translate['region'],
        aws_access_key_id=credenciales.translate['accessKeyId'],
        aws_secret_access_key=credenciales.translate['secretAccessKey']
    )

chat = boto3.client('lex-runtime',
        region_name=credenciales.lex['region'],
        aws_access_key_id=credenciales.lex['accessKeyId'],
        aws_secret_access_key=credenciales.lex['secretAccessKey']
    )

transcribe = boto3.client('transcribe',
        region_name=credenciales.transcribe['region'],
        aws_access_key_id=credenciales.transcribe['accessKeyId'],
        aws_secret_access_key=credenciales.transcribe['secretAccessKey']
    )

BUCKET_NAME='imagenes-ula'
BUCKET_AUDIO='audios-ula'
BOT_NAME='UgramPro'
BOT_ALIAS='ugrampro'
URL_BUCKET = 'https://imagenes-ula.s3.us-east-2.amazonaws.com/'

@app.route('/')
def result():
    return str("Jau")

###############################################################################################################################################
# MANEJO DE USUARIOS 

#ingreso a la app
@app.route('/ingresar', methods=['POST'])
def ingresar():
    usern = request.json.get('username')
    passw = request.json.get('contrasena')

    if not usern or not passw:
        return jsonify({'status': 404,'Item': ''})

    item = usuarioExistente(usern)
    if item:
        if item['contrasena']['S'] == passw:
            return jsonify({'status': 202,'Item':item})
        
        return jsonify({'status': 202,'Item':''})

    return jsonify({'status': 303,'Item': ""})

#Comparacion de foto de perfil en Login
@app.route('/ingresarWeb', methods=['POST'])
def ingresarWeb():
    usern = request.json.get('username')
    imagen2 = request.json.get('foto') #Foto nueva solo para ingresar.
    starter = imagen2.find(',')
    image_data = imagen2[starter+1:]
    image_data = bytes(image_data, encoding="ascii")

    if not usern:
        return jsonify({'status': 404,'Item': ''})

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
            SimilarityThreshold=81)

        if respuesta['FaceMatches'] == []:
            return jsonify({'status': 202,'Item':''})
        else:
            if respuesta['FaceMatches'][0]['Similarity'] >= 85:
                return jsonify({'status': 202,'Item': item})
            else: return jsonify({'status': 202,'Item': ''})

    return jsonify({'status': 303,'Item': ""})

#registro de nuevo usuario
@app.route('/registrar', methods=['POST'])
def registrar():
    usern = request.json.get('username')
    nombre = request.json.get('nombre')
    passw = request.json.get('contrasena')
    pais = request.json.get('pais')
    nFoto = request.json.get('nFoto')
    ext = request.json.get('ext')
    b64 = request.json.get('b64')
    uniqueID = str(uuid.uuid1().time_low)

    if not usern or not nombre or not passw or not nFoto:
        return jsonify({'status': 504,'existe': ''})

    if usuarioExistente(usern):
        return jsonify({'status': 404,'existe':'true'})

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

    return jsonify({'status': 202,'existe': "false"})

#editar datos del perfil de usuario
@app.route('/editarPerfil', methods=['POST'])
def editarPerfil():
    usern = request.json.get('username')
    nombre = request.json.get('nombre')
    passw = request.json.get('contrasena')
    nFoto = request.json.get('nFoto')
    ext = request.json.get('ext')
    b64 = request.json.get('b64')
    uniqueID = str(uuid.uuid1().time_low)

    if not usern or not nombre or not passw or not nFoto:
        return jsonify({'status': 504,'Item': ''})

    if usuarioExistente(usern): 
        if passw == usuarioExistente(usern)['contrasena']['S']:
            starter = b64.find(',')
            image_data = b64[starter+1:]
            image_data = bytes(image_data, encoding="ascii")
            ubicacion = 'fotos_perfil/' + nFoto + '-' + uniqueID + '.' + ext 

            album_perfil = usuarioExistente(usern)['album']
            for alb in album_perfil['L']:
                #aca es cada album
                if alb['L'][0]['S'] == 'Perfil':
                    alb['L'][1]['L'].append({'S': URL_BUCKET + ubicacion})
                    break

            s3.upload_fileobj(
                BytesIO(base64.b64decode(image_data)),
                BUCKET_NAME,
                ubicacion,
                ExtraArgs={'ACL': 'public-read'}
            )

            response = rek.detect_faces(Image={
            'S3Object':{
                    'Bucket':BUCKET_NAME,'Name': ubicacion
                }
            },Attributes=['ALL'])
            
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

            dynamo.update_item(
                TableName='usuario',
                Key = {
                    'username': {'S': usern}
                },
                UpdateExpression = 'set nombre=:n, nFoto=:nf, foto_perfil=:fp, album=:prof, etiquetas=:et',
                ExpressionAttributeValues = {
                    ':n': {'S': nombre},
                    ':nf': {'S': nFoto + '-' + uniqueID + '.' + ext},
                    ':fp': {'S': URL_BUCKET + ubicacion},
                    ':prof':album_perfil,
                    ':et':{'L': etiq}
                }
            )
            return jsonify({'status': 202,'Item': usuarioExistente(usern)})
        
        else: return jsonify({'status': 303,'Item': usuarioExistente(usern)})

    return jsonify({'status': 202,'Item': ''})

###############################################################################################################################################
# PUBLICACIONES
@app.route('/newPost', methods=['POST'])
def newPost():
    hoy = datetime.now()
    username = request.json.get('username')
    descripcion = request.json.get('descripcion')
    departamento = request.json.get('departamento')
    lugar = request.json.get('lugar')
    pais = request.json.get('pais')
    nFoto = request.json.get('nFoto')
    ext = request.json.get('ext')
    b64 = request.json.get('b64')
    guardar = request.json.get('guardar')
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

    return jsonify({'hoy': fechahora, 'status': 202})

@app.route('/getPost', methods=['GET'])
def getPost():
    lista = dynamo.scan(
        TableName='publicacion'
    )

    return jsonify({'items':lista['Items'], 'tam': lista['Count']})

###############################################################################################################################################
# TRANSCRIBE
@app.route('/hablar', methods=['POST'])
def hablar():
    nombre_audio = request.json.get('nombre')
    time.sleep(2)
    s3.upload_file('/tmp/' + str(nombre_audio).replace(':','_'), BUCKET_AUDIO, str(nombre_audio))
    transcribe.start_transcription_job(
        TranscriptionJobName='job' + str(nombre_audio).replace(':','').replace('-',''),
        MediaFormat='wav',
        Media={
            'MediaFileUri': 's3://audios-ula/' + str(nombre_audio)
        },
        OutputBucketName=BUCKET_AUDIO,
        OutputKey='out' + str(nombre_audio).replace(':','').replace('-','').replace('.','') + '.json',
        IdentifyLanguage=True,
        LanguageOptions=[
            'en-US','es-ES','es-US'
        ]
    )
    completed = False
    while not completed:
        response = transcribe.get_transcription_job(
            TranscriptionJobName='job' + str(nombre_audio).replace(':','').replace('-','')
        )
        completed = True if response['TranscriptionJob']['TranscriptionJobStatus'] == 'COMPLETED' else False
        if completed:
            print(response)

    return jsonify({'res':'holis'})

###############################################################################################################################################
# MANEJO DE ALBUM

# Nuevo album
@app.route('/newAlbum', methods=['POST'])
def newAlbum():
    usern = request.json.get('username')
    nombre_album = request.json.get('album')

    if not usern or not nombre_album:
        return jsonify({'status': 504,'existe': ''})

    item = usuarioExistente(usern)
    if item:
        albumes = usuarioExistente(usern)['album']
        albumes['L'].append({'L': [{'S':nombre_album},{'L':[]}]})
        
        dynamo.update_item(
            TableName='usuario',
            Key = {
                'username': {'S': usern}
            },
            UpdateExpression = 'set album=:nal',
            ExpressionAttributeValues = {
                ':nal': albumes
            }
        )
        
        return jsonify({'status': 202,'existe': usuarioExistente(usern)})

    return jsonify({'status': 404,'existe':'true'})

# Eliminar album
@app.route('/deleteAlbum', methods=['POST'])
def deleteAlbum():
    usern = request.json.get('username')
    nombre_album = request.json.get('album')

    if not usern or not nombre_album:
        return jsonify({'status': 504,'existe': ''})

    item = usuarioExistente(usern)
    if item:
        albumes = usuarioExistente(usern)['album']
        pos = 0
        for x in range(0,len(albumes['L'])):
            if albumes['L'][x]['L'][0]['S'] == nombre_album:
                pos = x
                break
        
        albumes['L'].pop(pos)
        
        dynamo.update_item(
            TableName='usuario',
            Key = {
                'username': {'S': usern}
            },
            UpdateExpression = 'set album=:nal',
            ExpressionAttributeValues = {
                ':nal': albumes
            }
        )
        
        return jsonify({'status': 202,'existe': usuarioExistente(usern)})

    return jsonify({'status': 404,'existe':'true'})

# Subir foto nueva en un album
@app.route('/nuevaFoto', methods=['POST'])
def nuevaFoto():
    usern = request.json.get('username')
    nombre_foto = request.json.get('nFoto')
    extension = request.json.get('ext')
    b64 = request.json.get('b64')
    uniqueID = str(uuid.uuid1().time_low)
    descr = request.json.get('descripcion')

    if not usern:
        return jsonify({'status': 504,'existe': ''})

    item = usuarioExistente(usern)
    if item:
        starter = b64.find(',')
        image_data = b64[starter+1:]
        image_data = bytes(image_data, encoding="ascii")
        ubicacion = 'fotos_publicadas/' + nombre_foto + '-' + uniqueID + '.' + extension

        s3.upload_fileobj(
            BytesIO(base64.b64decode(image_data)),
            BUCKET_NAME,
            ubicacion,
            ExtraArgs={'ACL': 'public-read'}
        )

        respuesta = rek.detect_labels(
            Image={
                'S3Object':{
                        'Bucket':BUCKET_NAME,'Name': ubicacion
                    }
                },
            MaxLabels=3)
        
        etiq = []
        for x in respuesta['Labels']:
            response = translate.translate_text(Text=x['Name'],SourceLanguageCode='en',TargetLanguageCode='es')
            etiq.append(response['TranslatedText'])


        albumes = usuarioExistente(usern)['album']
        
        for label in etiq:
            existe = False
            x = 0
            while not existe and x < len(albumes['L']):
                if albumes['L'][x]['L'][0]['S'] == label:
                    existe = True
                    albumes['L'][x]['L'][1]['L'].append({'L':[{'S':nombre_foto},{'S': descr},{'S': URL_BUCKET + ubicacion}]})
                x+=1
            
            if not existe:
                albumes['L'].append({'L': [{'S':label},{'L':[{'L':[{'S':nombre_foto},{'S': descr},{'S': URL_BUCKET + ubicacion}]}]}]})

                
        dynamo.update_item(
            TableName='usuario',
            Key = {
                'username': {'S': usern}
            },
            UpdateExpression = 'set album=:nal',
            ExpressionAttributeValues = {
                ':nal': albumes
            }
        )
        
        return jsonify({'status': 202,'existe': usuarioExistente(usern)})

    return jsonify({'status': 404,'existe':'true'})


###############################################################################################################################################
# FUNCIONES EXTRAS

#extraer texto desde una imagen
@app.route('/extraerTexto', methods=['POST'])
def extraerTexto():
    b64 = request.json.get('imagen')
    starter = b64.find(',')
    image_data = b64[starter+1:]
    image_data = bytes(image_data, encoding="ascii")
    
    textoResultante = []
    response = rek.detect_text(Image={'Bytes':base64.b64decode(image_data)})
    for x in response['TextDetections']:
        if x['Type'] == "LINE":
            textoResultante.append(x['DetectedText'])

    return jsonify({'texto': textoResultante})

#traduccion de cualquier idioma a ingles, portugues o ruso
@app.route('/traducir', methods=['POST'])
def traducir():
    idioma_destino = request.json.get('destino')
    texto = request.json.get('texto')

    response = translate.translate_text(Text=texto,SourceLanguageCode='auto',TargetLanguageCode=idioma_destino)

    return jsonify({'texto':response['TranslatedText']})

###############################################################################################################################################
# CHATBOT

#iniciar una sesión con el chat
@app.route('/iniciarChat', methods=['POST'])
def inicioChat():
    user = request.json.get('username')

    response = chat.put_session(
        botName=BOT_NAME,
        botAlias=BOT_ALIAS,
        userId=user,
        accept='text/plain; charset=utf-8'
    )

    return jsonify(response['ResponseMetadata'])

#finalizar chat
@app.route('/finChat', methods=['POST'])
def finChat():
    user = request.json.get('username')

    response = chat.delete_session(
        botName=BOT_NAME,
        botAlias=BOT_ALIAS,
        userId=user
    )

    return jsonify(response['ResponseMetadata'])

#conversar con el chat
@app.route('/conversarChat', methods=['POST'])
def conversarChat():
    user = request.json.get('username')
    mensaje = request.json.get('mensaje')

    response = chat.post_text(
        botName=BOT_NAME,
        botAlias=BOT_ALIAS,
        userId=user,
        inputText=mensaje
    )

    return jsonify(response)

###############################################################################################################################################

def usuarioExistente(usernam):
    existe = dynamo.get_item(
        TableName='usuario',
        Key = {
            'username': {'S': usernam}
        }
    )

    return existe.get('Item')

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=7050)