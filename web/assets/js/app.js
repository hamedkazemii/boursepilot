
const API="/api/v1";


async function loadJSON(url){

    const res = await fetch(API+url);

    return await res.json();

}



function renderFunds(target,items){

    const el=document.getElementById(target);

    if(!items || items.length===0){

        el.innerHTML="داده‌ای موجود نیست";
        return;

    }


    el.innerHTML=items.map(f=>`

    <div class="fund">

        <div>
            <b>${f.symbol || "-"}</b>
            <div>${f.name || ""}</div>
        </div>


        <div class="score">

        ${f.score || "-"} 
        
        </div>


    </div>

    `).join("");

}



async function loadDashboard(){


    try {


        const summary =
        await loadJSON("/market/summary");


        document
        .getElementById("marketSummary")
        .innerHTML=`

        منبع:
        ${summary.source || "-"}

        <br>

        فاصله رتبه‌ها:
        ${summary.gap || 0}

        <br>

        وضعیت:
        ${summary.sane ? "معتبر":"نیازمند بررسی"}

        `;



        const top =
        await loadJSON("/ranking/top");


        renderFunds(
            "topFunds",
            top.items
        );



        const worst =
        await loadJSON("/ranking/worst");


        renderFunds(
            "worstFunds",
            worst.items
        );



    }

    catch(e){

        console.log(e);

    }


}



document
.getElementById("themeToggle")
.onclick=()=>{

document.body.classList.toggle("light");

};



loadDashboard();

