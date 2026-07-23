const API_BASE = "/api/v1";


async function apiGet(path){

    try{

        const response =
            await fetch(
                API_BASE + path
            );


        if(!response.ok){

            throw new Error(
                "API Error"
            );

        }


        return await response.json();


    }catch(error){

        console.error(
            error
        );


        return null;

    }

}



async function getHealth(){

    return apiGet(
        "/health"
    );

}


async function getMarketSummary(){

    return apiGet(
        "/market/summary"
    );

}


async function getTopFunds(){

    return apiGet(
        "/ranking/top?limit=5"
    );

}


async function getWorstFunds(){

    return apiGet(
        "/ranking/worst?limit=5"
    );

}

