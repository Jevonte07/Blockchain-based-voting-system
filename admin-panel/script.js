const URL = "https://blockchain-based-voting-system-u0pb.onrender.com";

// LOGIN
function login() {

const user = document.getElementById("username").value.trim();
const pass = document.getElementById("password").value.trim();

fetch(URL + "/login", {
method: "POST",
credentials: "include",
headers: {
"Content-Type": "application/json"
},
body: JSON.stringify({
user: user,
pass: pass
})
})
.then(res => res.json())
.then(data => {

if (data.msg === "success") {

document.getElementById("loginPage").style.display = "none";
document.getElementById("dashboard").style.display = "block";

loadCandidates();
loadResults();
updateStatus();

} else {
document.getElementById("loginMsg").innerText = "Wrong Login";
}

})
.catch(err => {
console.log(err);
document.getElementById("loginMsg").innerText = "Server Error";
});

}

// LOGOUT
function logout() {

fetch(URL + "/logout", {
credentials: "include"
}).then(() => location.reload());

}

// ADD CANDIDATE
function addCandidate() {

let name = document.getElementById("candidateName").value.trim();

fetch(URL + "/add_candidate", {
method: "POST",
credentials: "include",
headers: {
"Content-Type": "application/json"
},
body: JSON.stringify({ name: name })
})
.then(res => res.json())
.then(data => {

alert(data.msg);
document.getElementById("candidateName").value = "";
loadCandidates();

});

}

// LOAD CANDIDATES
function loadCandidates() {

fetch(URL + "/candidates")
.then(res => res.json())
.then(data => {

let html = "";

data.forEach(name => {

html += `
<li>
${name}
<button onclick="removeCandidate('${name}')">Delete</button>
</li>
`;

});

document.getElementById("candidateList").innerHTML = html;

});

}

// DELETE
function removeCandidate(name) {

fetch(URL + "/delete/" + name, {
credentials: "include"
})
.then(res => res.json())
.then(() => loadCandidates());

}

// SAVE TIME
function saveTime() {

let startInput =
document.getElementById("startTime").value;

let endInput =
document.getElementById("endTime").value;

if(startInput === "" || endInput === ""){

alert("Select both start and end time");

return;
}

// ✅ Convert local browser time to UTC ISO
let startUTC =
new Date(startInput).toISOString();

let endUTC =
new Date(endInput).toISOString();

fetch(URL + "/set_time", {

method:"POST",

headers:{
"Content-Type":"application/json"
},

body:JSON.stringify({

start:startUTC,

end:endUTC

})

})
.then(res=>res.json())
.then(data=>{

alert(data.msg);

});

}

// RESULTS
function loadResults() {

fetch(URL + "/results")
.then(res => res.json())
.then(data => {

let html = "";

for (let x in data) {
html += `<div class="result-row">${x}: ${data[x]} Votes</div>`;
}

document.getElementById("results").innerHTML = html;

});

}

// STATUS
function updateStatus() {

fetch(URL + "/get_time")
.then(res => res.json())
.then(data => {

const status = document.getElementById("status");
const timer = document.getElementById("timer");

if (data.start === "" || data.end === "") {
status.innerText = "Time Not Set";
timer.innerText = "00:00:00";
return;
}

let start = new Date(data.start);
let end = new Date(data.end);
let now = new Date();

if (now < start) {
status.innerText = "Waiting ⏳";
timer.innerText = format(start - now);
}
else if (now >= start && now <= end) {
status.innerText = "Live Voting ✅";
timer.innerText = format(end - now);
}
else {
status.innerText = "Ended 🛑";
timer.innerText = "00:00:00";
}

});

}

// AUTO REFRESH
setInterval(() => {
updateStatus();
loadResults();
}, 1000);

// FORMAT
function format(ms) {

let total = Math.floor(ms / 1000);

let h = Math.floor(total / 3600);
let m = Math.floor((total % 3600) / 60);
let s = total % 60;

return pad(h) + ":" + pad(m) + ":" + pad(s);

}

function pad(n) {
return n.toString().padStart(2, "0");
}