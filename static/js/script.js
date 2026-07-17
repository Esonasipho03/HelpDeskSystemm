console.log("Help Desk System Loaded");

document.addEventListener("DOMContentLoaded", function () {

    const inputs = document.querySelectorAll("input");

    inputs.forEach(input => {

        input.addEventListener("focus", function () {

            const help = this.parentElement.querySelector(".help-text");

            if(help){
                help.style.display = "block";
            }

        });

        input.addEventListener("blur", function () {

            const help = this.parentElement.querySelector(".help-text");

            if(help){
                help.style.display = "none";
            }

        });

    });

});