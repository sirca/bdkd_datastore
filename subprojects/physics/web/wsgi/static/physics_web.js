BDKD.MAP_X_OFFSET = 53;
BDKD.MAP_Y_OFFSET = 46;
BDKD.MAX_INJECTION = 250;
BDKD.MAX_FEEDBACK = 350;

BDKD.TIME_SERIES_STEP = 50;

BDKD.TIME_SERIES_LEFT_OFFSET_PX = 81;
BDKD.TIME_SERIES_WIDTH_PX = 495;
BDKD.TIME_SERIES_RIGHT_PX = (BDKD.TIME_SERIES_LEFT_OFFSET_PX + 
        BDKD.TIME_SERIES_WIDTH_PX);
BDKD.TIME_SERIES_HEIGHT_PX = 480;


function coordinates(x, y) {
    /**
     * Get feedback and injection based on the selected pixel of the current
     * map.
     */
    var injection = x - BDKD.MAP_X_OFFSET;
    var feedback = y - BDKD.MAP_Y_OFFSET;
    if ( injection < 0 ) injection = 0;
    if ( injection > BDKD.MAX_INJECTION) injection = BDKD.MAX_INJECTION;
    if ( feedback < 0 ) feedback = 0;
    if ( feedback > BDKD.MAX_FEEDBACK ) feedback = BDKD.MAX_FEEDBACK;
    return {
        feedback: feedback,
        injection: injection
    };
};


function cursorpos(x,y) {
    /**
     * Update the page with the selected feedback/injection position.
     */
    coords = coordinates(x, y);
    $('#map_coords').css('display', 'inline');
    $('#injection_coord').html(BDKD.injection_values[coords.injection] +
            " (" + coords.injection + ")");
    $('#feedback_coord').html(BDKD.feedback_values[coords.feedback] + 
            " (" + coords.feedback + ")");
};


function updateMapList() {
    /**
     * Get a list of all available maps for the current dataset and update the
     * maps list control.
     */
    var map_options = '';
    $.ajax({url: '/map_names/' + BDKD.dataset,
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


function updateFeedback() {
    $.ajax({url: '/feedback/' + BDKD.dataset,
            context: document.body,
            success: function(data) {
                var feedback = JSON.parse(data);
                BDKD.feedback_values = new Array();
                var feedback_options = '';
                for ( var i = 0; i < feedback.length; i++ ) {
                    var fb = Number((feedback[i]).toFixed(5));
                    BDKD.feedback_values.push(fb);
                    feedback_options += '<option value="' + i + '">' + fb + ' (' + i + ')</option>';
                }
                $('#map_feedback').html(feedback_options);
            }
    });
};


function updateInjection() {
    $.ajax({url: '/injection/' + BDKD.dataset,
            context: document.body,
            success: function(data) {
                var injection = JSON.parse(data);
                BDKD.injection_values = new Array();
                var injection_options = '';
                for ( var i = 0; i < injection.length; i++ ) {
                    var inj = Number((injection[i]).toFixed(1));
                    BDKD.injection_values.push(inj);
                    injection_options += '<option value="' + i + '">' + inj + ' (' + i + ')</option>';
                }
                $('#map_injection').html(injection_options);
            }
    });
};


function updateDataset() {
    /**
     * On change of selected dataset, update values related to it including the
     * list of maps and the feedback and injection values.
     */
    updateMapList();
    updateFeedback();
    updateInjection();
};


function fixTimeSeriesSelection(selection) {
    /**
     * Force the vertically-selected time series range to fit in the data area
     * of the time series plot.
     */
    var do_fix = false;
    if ( selection.x1 < BDKD.TIME_SERIES_LEFT_OFFSET_PX ) {
        selection.x1 = BDKD.TIME_SERIES_LEFT_OFFSET_PX;
        do_fix = true;
    }
    if ( selection.x1 > (BDKD.TIME_SERIES_RIGHT_PX - 1) ) {
        selection.x1 = (BDKD.TIME_SERIES_RIGHT_PX - 1);
        do_fix = true;
    }
    if ( selection.x2 > BDKD.TIME_SERIES_RIGHT_PX ) {
        selection.x2 = BDKD.TIME_SERIES_RIGHT_PX;
        do_fix = true;
    }
    if ( ! selection.x2 > selection.x1 ) {
        selection.x2 = selection.x1 + 1;
        do_fix = true;
    }
    if ( do_fix ) {
        BDKD.ias.setSelection(selection.x1, selection.y1, 
                selection.x2, selection.y2);
        BDKD.ias.update();
    }
};


function timeSeriesPxNormalise(x) {
    x -= BDKD.TIME_SERIES_LEFT_OFFSET_PX;
    if ( x < 0 ) x = 0;
    if ( x > BDKD.TIME_SERIES_WIDTH_PX ) x = BDKD.TIME_SERIES_WIDTH_PX;
    return x;
};


function timeSeriesPxToTimeRange(x1, x2) {
    var x1 = timeSeriesPxNormalise(x1);
    var x2 = timeSeriesPxNormalise(x2);
    var range = BDKD.to_time - BDKD.from_time;
    from_time = BDKD.from_time + Math.floor(
            Math.floor(range * x1 / BDKD.TIME_SERIES_WIDTH_PX) / BDKD.TIME_SERIES_STEP
            ) * BDKD.TIME_SERIES_STEP;
    to_time = BDKD.from_time + Math.ceil(
            Math.ceil(range * x2 / BDKD.TIME_SERIES_WIDTH_PX) / BDKD.TIME_SERIES_STEP
            ) * BDKD.TIME_SERIES_STEP - 1;
    return {from_time: from_time, to_time: to_time};
};


function updateTimeSeriesZoom(img, selection) {
    fixTimeSeriesSelection(selection);
    time_range = timeSeriesPxToTimeRange(selection.x1, selection.x2);
    $('#from_time').val(time_range.from_time);
    $('#to_time').val(time_range.to_time);
};


function updateTimeSeries(from_time, to_time) {
    var time_series_name = BDKD.dataset + "?feedback="+BDKD.feedback+"&injection="+BDKD.injection +
        "&from=" + from_time + "&to=" + to_time;
    var plot_src = "/time_series_plots/" + time_series_name;
    var data_src = "/time_series_data/" + time_series_name;
    $('#graph1').replaceWith("<img id='graph1' src='"+plot_src+"' />");
    if ( BDKD.ias ) 
        BDKD.ias.setOptions({ hide: true });
    BDKD.ias = $('#graph1').imgAreaSelect({ 
        minHeight: BDKD.TIME_SERIES_HEIGHT_PX, 
        maxHeight: BDKD.TIME_SERIES_HEIGHT_PX, 
        onSelectChange: updateTimeSeriesZoom, 
        instance: true });
    BDKD.from_time = from_time;  $('#from_time').val(from_time);
    BDKD.to_time = to_time;  $('#to_time').val(to_time);
    $('#time_series_download').html('Data: <a href="' + data_src + '">' + time_series_name + '</a>'); 
};


function displayTimeSeries() {
    BDKD.injection = $('#map_injection').val();
    BDKD.feedback = $('#map_feedback').val();
    $('#time_series_panel').slideDown();
    updateTimeSeries(0, 999999);
};


function zoomTimeSeries() {
        updateTimeSeries(parseInt($('#from_time').val()), 
                parseInt($('#to_time').val()));
};


function updateMapPlot() {
    var map_name = $('#dataset').val() + '/' + $('#map').val();
    var plot_src = '/map_plots/' + map_name;
    var data_src = '/map_data/' + map_name;

    $('#heatmap').replaceWith('<img id="heatmap" src="' + plot_src +
            '" data-zoom-image="' + plot_src + '?size=large" ' +
            'width=407 height=440/>');
    $('#heatmap').elevateZoom({
        scrollZoom  : true,
        zoomType    : "lens",
        lensSize    : 100,
        cursor      : "crosshair",
        onMousemove : cursorpos
    });
    $("#heatmap").click(function(e,x,y) {
        var coords = coordinates(x, y);
        BDKD.injection = coords.injection;
        $('#map_injection').val(coords.injection);
        BDKD.feedback = coords.feedback;
        $('#map_feedback').val(coords.feedback);
    });

    $('#heatmap_download').html('Data: <a href="' + data_src + '">' + map_name + '</a>');
};


$(document).ready(function() {
    updateDataset();
});
