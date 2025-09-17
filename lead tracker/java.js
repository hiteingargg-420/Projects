
let myLeads=[];
const inputEl=document.getElementById("input-el");
const ulEl=document.getElementById("list")
const iButton=document.getElementById("input-btn")
const dButton=document.getElementById("delete-btn")
const tButton=document.getElementById("savetab-btn")
const leadsFromLocalStorage = JSON.parse(localStorage.getItem("myLeads"))
if(leadsFromLocalStorage){
        myLeads=leadsFromLocalStorage;
        render(myLeads);
}
else{}

function render(Leads){
let listItems=""
    for(let i=0;i<Leads.length;i++){
         listItems+= `<li>
         <a target='_blank' href='${Leads[i]}'>
          ${Leads[i]}
         </a>
         </li>`
    }
    ulEl.innerHTML=listItems;
}
iButton.addEventListener("click",function(){
    myLeads.push(inputEl.value)
    inputEl.value=""
    localStorage.setItem("myLeads",JSON.stringify(myLeads))
    render(myLeads);
})

tButton.addEventListener("click",function(){
chrome.tabs.query({ active: true, currentWindow: true }, function (tabs) {
   myLeads.push(tabs[0].url);
    localStorage.setItem("myLeads",JSON.stringify(myLeads))
    render(myLeads)
})
   
})
dButton.addEventListener("dblclick",function(){
    localStorage.clear();
    myLeads=[];
    render(myLeads);
})
