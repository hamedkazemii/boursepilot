
function renderChart(id,data){

const el=document.getElementById(id);

if(!el) return;

if(!data || data.length===0){

el.innerHTML="داده نمودار موجود نیست";

return;

}

el.innerHTML =
data.map(
x=>`${x}`
).join(",");

}

