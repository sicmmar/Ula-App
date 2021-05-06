const URL = "3.21.75.136:7050";
const APIG = "https://ys642emfcc.execute-api.us-east-2.amazonaws.com/ulaApi/"

const connectAPI = async (cuerpo, endpoint) => {
    const response = await fetch("http://" + URL + "/" + endpoint, {
        method: "POST",
        headers: {
            "Content-Type":"application/json",
            Accept : "application/json"
        },
        body : cuerpo
    });

    const respuesta = await response.json();
    return respuesta
}

const getAPI = async (endpoint) => {
    const response = await fetch("http://" + URL + "/" + endpoint, {
        method: "GET",
        headers: {
            "Content-Type":"application/json",
            Accept : "application/json"
        }
    });

    return await response.json();
}

const connectGateway = async (cuerpo, endpoint) =>{
    const respuesta = await superagent
    .post(APIG + endpoint)
    .send(cuerpo)
    .then(res => {
        return JSON.parse(res.text);
    }).catch( error => {
        JSON.parse('{"status":404}');}
    );

    return respuesta;
}

const getGateway = async (endpoint) =>{
    const respuesta = await superagent
    .get(APIG + endpoint)
    .then(res => {
        return JSON.parse(res.text);
    }).catch( error => {
        JSON.parse('{"status":404}');}
    );

    return respuesta;
}