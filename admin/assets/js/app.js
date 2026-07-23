
async function loadOverview(){

try{

const r = await fetch("/api/v1/health");

const data = await r.json();

document.getElementById("quality").innerText =
data.status || "--";

}
catch(e){

console.log(e);

}

}

loadOverview();

