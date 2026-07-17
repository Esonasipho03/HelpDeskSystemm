function togglePopup(id, e){

    e.stopPropagation();

    const popup=document.getElementById(id);

    const open=!popup.classList.contains("show");

    document.querySelectorAll(".profile-popup,.notif-popup")
        .forEach(p=>p.classList.remove("show"));

    if(open){

        popup.classList.add("show");

        if(id==="notifPopup"){

            markNotificationsRead();

        }

    }

}

function markNotificationsRead(){

    fetch("{% url 'mark_notifications_read' %}",{

        method:"POST",

        headers:{

            "X-CSRFToken":getCookie("csrftoken")

        }

    });

    document.querySelector(".notification-dot")?.remove();

    document.querySelector(".notif-unread-badge")?.remove();

}

function getCookie(name){

    let value="; "+document.cookie;

    let parts=value.split("; "+name+"=");

    if(parts.length===2)

        return parts.pop().split(";").shift();

    return "";

}

document.addEventListener("click",function(){

    document
        .querySelectorAll(".profile-popup,.notif-popup")
        .forEach(p=>p.classList.remove("show"));

});

document.querySelectorAll(".profile-popup,.notif-popup").forEach(function(p){

    p.addEventListener("click",function(e){

        e.stopPropagation();

    });

});