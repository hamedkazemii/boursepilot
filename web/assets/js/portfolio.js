
function getPortfolio(){

return JSON.parse(
localStorage.getItem("portfolio") || "[]"
);

}



function save(){

localStorage.setItem(
"portfolio",
JSON.stringify(getPortfolio())
);

}



function addPortfolio(){

let p=getPortfolio();


p.push({

symbol:
document.getElementById("symbol").value,

units:
document.getElementById("units").value,

price:
document.getElementById("price").value

});


localStorage.setItem(
"portfolio",
JSON.stringify(p)
);


render();

}



function render(){

document.getElementById("portfolioList").innerHTML=

getPortfolio().map(x=>
`
<div class="item">
${x.symbol}
<br>
تعداد:
${x.units}
<br>
قیمت:
${x.price}
</div>
`
).join("");

}


render();

