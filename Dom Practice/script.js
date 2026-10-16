const button = document.querySelector("#changeBtn");
const colorCode = document.querySelector("#colorCode");
function generateRandomColor(){
const letters = "0123456789ABCDEF";
let color = "#";
for(let i = 0; i < 6; i++){
color += letters[Math.floor(Math.random()*16)];
}
return color;
}
button.addEventListener("click", function(){
const randomColor = generateRandomColor();
document.body.style.backgroundColor = randomColor;
colorCode.textContent = randomColor;
});