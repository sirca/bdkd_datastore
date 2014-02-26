var MAP_X_OFFSET = 52;
var MAP_Y_OFFSET = 75;
var MAX_INJECTION = 250;
var MAX_FEEDBACK = 350;


function coordinates(x, y) {
	var injection = x - MAP_X_OFFSET;
	var feedback = y - MAP_Y_OFFSET;
	if ( injection < 0 ) injection = 0;
	if ( injection > MAX_INJECTION) injection = MAX_INJECTION;
	if ( feedback < 0 ) feedback = 0;
	if ( feedback > MAX_FEEDBACK ) feedback = MAX_FEEDBACK;
	return {
		feedback: feedback,
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
    var map_name = $('#dataset').val() + '/' + $('#map').val();
    var plot_src = '/map_plots/' + map_name;
    var data_src = '/map_data/' + map_name;

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
        var coords = coordinates(x, y);
        var dataset = $('#dataset').val();
        var time_series_name = dataset + "?feedback="+coords.feedback+"&injection="+coords.injection;
        var plot_src = "/time_series_plots/" + time_series_name;
        var data_src = "/time_series_data/" + time_series_name;
        $("#graph1").replaceWith("<img id='graph1' src='"+plot_src+"' />"); 
        $('#time_series_download').html('Data: <a href="' + data_src + '">' + time_series_name + '</a>');
    });

    $('#heatmap_download').html('Data: <a href="' + data_src + '">' + map_name + '</a>');
};


$(document).ready(function() {
    updateMapList();
});
