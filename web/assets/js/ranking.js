
const API="/api/v1";


async function loadRanking(type="today"){

let url="/ranking/"+type;

let r=await fetch(API+url);

let data=await r.json();


let items=data.items || data.top || [];


document.getElementById("rankingList").innerHTML=

items.map(x=>`

<div class="item">

<b>${x.symbol || "-"}</b>

<br>

امتیاز:
${x.score || "-"}

<br>

رتبه:
${x.rank || "-"}

</div>

`).join("");

}


loadRanking();

