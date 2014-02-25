var MAP_X_OFFSET = 52;
var MAP_Y_OFFSET = 75;


function coordinates(x, y) {
	var injection = x - MAP_X_OFFSET;
	var feedback = y - MAP_Y_OFFSET;
	if ( injection < 0 ) injection = 0;
	if ( injection > 250) injection = 250;
	if ( feedback < 0 ) feedback = 0;
	if ( feedback > 350 ) feedback = 350;
	return {
		feedback: (350 - feedback),
		injection: injection
	};
};

	
function cursorpos(x,y) {
    coords = coordinates(x, y);
    $("#log").html("Injection: " + coords.injection + " Feedback: " + coords.feedback);
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
            'width=407 height=509/>');

    $('#heatmap').elevateZoom({
        scrollZoom  : true,
        zoomType    : "lens",
        lensSize    : 100,
        cursor      : "crosshair",
        onMousemove : cursorpos
    });
    
    $("#heatmap").click(function(e,x,y) {
        coords = coordinates(x, y);
	dataset = $('#dataset').val();
        src = "/time_series_plot/" + dataset + "?feedback="+coords.feedback+"&injection="+coords.injection;
        $("#graph1").replaceWith("<img id='graph1' src='"+src+"' />"); 
    });
};

$(document).ready(function() {
    updateMapList();
});
