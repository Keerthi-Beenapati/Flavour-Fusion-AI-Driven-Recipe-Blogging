document.addEventListener("DOMContentLoaded",()=>{
 const toggle=document.querySelector(".menu-toggle"),nav=document.querySelector(".nav-links");
 if(toggle&&nav)toggle.addEventListener("click",()=>{const open=nav.classList.toggle("nav-open");toggle.setAttribute("aria-expanded",String(open));});
 document.querySelectorAll(".favorite-form").forEach(form=>form.addEventListener("submit",async e=>{
   const button=form.querySelector("button"); if(!button)return;
   e.preventDefault();
   try{const response=await fetch(form.action,{method:"POST",headers:{"X-Requested-With":"XMLHttpRequest"}});if(response.status===401){window.location.href="/login";return;}const data=await response.json();if(data.ok){button.classList.toggle("is-saved",data.saved);button.textContent=data.saved?"♥":"♡";button.setAttribute("aria-label",data.saved?"Remove saved recipe":"Save recipe");}}
   catch(err){form.submit();}
 }));
 document.querySelectorAll(".flash").forEach(el=>setTimeout(()=>{if(el.isConnected){el.style.opacity="0";el.style.transform="translateY(-5px)";setTimeout(()=>el.remove(),250)}},6000));
});