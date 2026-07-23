
async function load(){

let r=await fetch("/api/v1/ranking/today");

let data=await r.json();


document.getElementById("ranking").innerHTML=

JSON.stringify(data,null,2);

}


load();

