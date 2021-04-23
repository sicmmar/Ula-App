const URL = "localhost:7050";

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