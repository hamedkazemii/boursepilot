
async function load(){

let h=await fetch("/api/v1/health");

let health=await h.json();


document.getElementById("health").innerHTML=

JSON.stringify(health.database);



document.getElementById("summary").innerHTML=

JSON.stringify(health.analysis);


}


load();

