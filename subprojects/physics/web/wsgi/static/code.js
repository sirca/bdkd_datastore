function cursorpos(x,y) {
    $("#log").html("X: " + x + " Y: " + y);
};

function updateMapList() {
    var map_options = '';
    $.ajax({url: '/map_names/' + $('#dataset').val(),
            context: document.body,
            success: function(data) {
                map_names = JSON.parse(data);
                map_options = '';
                for ( var i = 0; i < map_names.length; i++ ) {
                    map_options += '<option>' + map_names[i] + '</option>';
                }
                $('#map').html(map_options);
                updateMapPlot();
            }
    });
};

function updateMapPlot() {
    var plot_src = '/map_plots/' + $('#dataset').val() + '/' + $('#map').val();
    $('#heatmap').replaceWith('<img id="heatmap" src="' + plot_src +
            '" data-zoom-image="' + plot_src + '?size=large" ' +
            'width=351 height=251/>');

    $('#heatmap').elevateZoom({
        scrollZoom  : true,
        zoomType    : "lens",
        lensSize    : 100,
        cursor      : "crosshair",
        onMousemove : cursorpos
    });
    
    $("#heatmap").click(function(e,x,y) { 
	dataset = $('#dataset').val();
        src = "/time_series_plot/" + dataset + "?feedback="+x+"&injection="+y;
        $("#graph1").replaceWith("<img id='graph1' src='"+src+"' />"); 
    });
};

$(document).ready(function() {
    updateMapList();
});
