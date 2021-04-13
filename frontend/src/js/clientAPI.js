const URL = "3.15.161.46:7050";

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