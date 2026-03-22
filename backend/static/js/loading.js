function myFunction() {
  alert("Hello from a static file!");
}
function showLoaderOnClick(url) {
      showLoader();
      window.location.href=url;
  }
function showLoader(){
    document.getElementById('loading').style.display = 'flex';
  }