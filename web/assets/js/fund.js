
const params=new URLSearchParams(location.search);

const symbol=params.get("symbol");


async function loadFund(){

let r=await fetch("/api/v1/funds/"+symbol);

let data=await r.json();


document.getElementById("title").innerText=symbol;


document.getElementById("fundCard").innerHTML=`

<h2>${data.symbol}</h2>

امتیاز:
${data.score || "-"}

<br>

توصیه:
${data.recommendation || "-"}

<br><br>

${data.explain_fa || "توضیح موجود نیست"}

`;

}


loadFund();

