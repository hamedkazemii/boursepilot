document.addEventListener(
"DOMContentLoaded",
async function(){


    const health =
        await getHealth();


    const market =
        await getMarketSummary();


    const top =
        await getTopFunds();


    const worst =
        await getWorstFunds();



    const source =
        document.getElementById(
            "source"
        );


    if(source && market){

        source.innerText =
            market.source || "unknown";

    }



    const quality =
        document.getElementById(
            "quality"
        );


    if(quality && market){

        quality.innerText =
            market.sane
            ?
            "OK"
            :
            "Warning";

    }




    renderFunds(
        "top-list",
        top
    );


    renderFunds(
        "worst-list",
        worst
    );


});




function renderFunds(
    id,
    data
){

    const box =
        document.getElementById(
            id
        );


    if(!box || !data)
        return;


    const items =
        data.items || [];


    box.innerHTML =
        items.map(
            item => `

            <div class="fund-card">

            <strong>
            ${item.symbol}
            </strong>

            <br>

            امتیاز:
            ${item.score}

            <br>

            ${item.recommendation}

            </div>

            `
        ).join("");

}

