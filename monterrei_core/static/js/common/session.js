// Session helper: lee cookie monterrei_sid, expón window.MSID
(function() {
  function getCookie(name) {
    const m = document.cookie.match(new RegExp('(^| )' + name + '=([^;]+)'));
    return m ? decodeURIComponent(m[2]) : null;
  }
  window.MSID = getCookie('monterrei_sid');
})();
