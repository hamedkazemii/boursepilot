

async function loadOverview(){

let r=
await fetch(
"/api/v1/admin/overview"
);


let data=
await r.json();


document
.getElementById("universe")
.innerText=
data.universe_size;



document
.getElementById("gap")
.innerText=
data.gap;



document
.getElementById("quality")
.innerText=
data.sane
?
"OK"
:
"Warning";

}


loadOverview();


