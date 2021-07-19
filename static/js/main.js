
  $(function () {
    $('[data-toggle="tooltip"]').tooltip()
  })

var page_y = $( document ).scrollTop();
window.location.href = window.location.href + '?page_y=' + page_y;

$(function() {
    if ( window.location.href.indexOf( 'page_y' ) != -1 ) {
        //gets the number from end of url
        var match = window.location.href.split('?')[1].match( /\d+$/ );
        var page_y = match[0];

        //sets the page offset 
        $( 'html, body' ).scrollTop( page_y );
    }
});
  
