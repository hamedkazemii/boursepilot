
function advise(){

let risk=document.getElementById("risk").value;

let capital=document.getElementById("capital").value;


document.getElementById("answer").innerHTML=

`

بر اساس سرمایه ${capital}

و سطح ریسک ${risk}

تحلیل صندوقچی پس از اتصال به موتور AIAdvisor

ارائه خواهد شد.

`;

}

