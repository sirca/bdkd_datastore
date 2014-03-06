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


function onChangeDataset() {
    /**
     * On change of selected dataset, update values related to it including the
     * list of maps and the feedback and injection values.
     */
    BDKD.dataset = $('#dataset').val();
    updateMapList();
    updateFeedback();
    updateInjection();
};


function onChangeMap() {
    /**
     * Invoked when a different map is selected from the map list.
     */
    BDKD.map = $('#map').val();

    var plot_src = '/map_plots/' + BDKD.dataset + '/' + BDKD.map;
    var data_src = '/map_data/' + BDKD.dataset + '/' + BDKD.map;

    $('#heatmap').replaceWith('<img id="heatmap" src="' + plot_src +
            '" data-zoom-image="' + plot_src + '?size=large" ' +
            'width=407 height=440/>');
    $('#heatmap').elevateZoom({
        scrollZoom  : true,
        zoomType    : "lens",
        lensSize    : 100,
        cursor      : "crosshair",
        onMousemove : mapCursorPos
    });
    $("#heatmap").click(function(e,x,y) {
        var coords = mapCoordinates(x, y);
        BDKD.injection = coords.injection;
        $('#map_injection').val(coords.injection);
        BDKD.feedback = coords.feedback;
        $('#map_feedback').val(coords.feedback);
    });

    $('#heatmap_download').html('Data: <a href="' + data_src + '">' + BDKD.map + '</a>');
};


function onChangeTimeSeries() {
    /**
     * Invoked when the user changes the current time series.
     *
     * The from/to times are reset to the defaults (0 - 999999).
     */
    BDKD.injection = $('#map_injection').val();
    BDKD.feedback = $('#map_feedback').val();
    BDKD.from_time = 0;
    BDKD.to_time = 999999;
    $('#time_series_panel').slideDown();
    updateTimeSeries();
    $('#phase_panel').slideDown();
    updatePhaseDiagram();
    $('#fft_panel').slideDown();
    updateFFTDiagram();
};

function onZoomTimeSeries() {
    /**
     * Invoked when the user zooms in on the current time series.
     */
    BDKD.from_time = parseInt($('#from_time').val());
    BDKD.to_time = parseInt($('#to_time').val());

    updateTimeSeries();
    updatePhaseDiagram();
    updateFFTDiagram();
};


function onResetZoomTimeSeries() {
    /**
     * Invoked when the user resets the current zoom of the time series (resets
     * to 0 - 999999).
     */
    BDKD.from_time = 0;
    BDKD.to_time = 999999;

    updateTimeSeries();
    updatePhaseDiagram();
    updateFFTDiagram();
};


function onChangePhaseDelay() {
    updatePhaseDiagram();
};


function updateTimeSeries() {
    var time_series_name = BDKD.dataset + "?feedback="+BDKD.feedback+"&injection="+BDKD.injection +
        "&from=" + BDKD.from_time + "&to=" + BDKD.to_time;
    var plot_src = "/time_series_plots/" + time_series_name;
    var data_src = "/time_series_data/" + time_series_name;
    $('#time_series_plot').replaceWith("<img id='time_series_plot' width=640 height=480 src='"+plot_src+"' />");
    if ( BDKD.ias ) 
        BDKD.ias.setOptions({ hide: true });
    BDKD.ias = $('#time_series_plot').imgAreaSelect({ 
        minHeight: BDKD.TIME_SERIES_HEIGHT_PX, 
        maxHeight: BDKD.TIME_SERIES_HEIGHT_PX, 
        onSelectChange: updateTimeSeriesZoom, 
        instance: true });
    $('#from_time').val(BDKD.from_time);
    $('#to_time').val(BDKD.to_time);
    $('#time_series_download').html('Data: <a href="' + data_src + '">' + time_series_name + '</a>'); 

};


function updateTimeSeriesZoom(img, selection) {
    /**
     * Called by ImgAreaSelect when the selected area of the time series is
     * changed, this function sets the from- and to-times.
     */
    fixTimeSeriesSelection(selection);
    time_range = timeSeriesPxToTimeRange(selection.x1, selection.x2);
    $('#from_time').val(time_range.from_time);
    $('#to_time').val(time_range.to_time);
};


function updatePhaseDiagram() {
    BDKD.phase_delay = parseInt($('#phase_delay').val());
    var plot_src = "/phase_plots/" + BDKD.dataset + 
        "?feedback=" + BDKD.feedback +
        "&injection=" + BDKD.injection + 
        "&from=" + BDKD.from_time + 
        "&to=" + BDKD.to_time + 
        "&delay=" + BDKD.phase_delay;
    $('#phase_plot').replaceWith("<img id='phase_plot' width=640 height=480 src='"+plot_src+"' />");
};


function updateFFTDiagram() {
    var params = BDKD.dataset + 
        "?feedback=" + BDKD.feedback +
        "&injection=" + BDKD.injection + 
        "&from=" + BDKD.from_time + 
        "&to=" + BDKD.to_time;
    var data_src = "/fft_data/" + params;
    var plot_src = "/fft_plots/" + params;
    $('#fft_download').html('Data: <a href="' + data_src + '">' + data_src + '</a>'); 
    $('#fft_plot').replaceWith("<img id='fft_plot' width=640 height=480 src='"+plot_src+"' />");
};


function updateMapList() {
    /**
     * Get a list of all available maps for the current dataset and update the
     * maps list control.
     *
     * The first map is selected by default, and displayed.
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
                onChangeMap();
            }
    });
};


function updateFeedback() {
    /**
     * Get all the feedback values for the current dataset and keep them.
     *
     * Also updates the drop-down list containing available feedback options.
     */
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
    /**
     * Get all the injection values for the current dataset and keep them.
     *
     * Also updates the drop-down list containing available injection options.
     */
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


function mapCoordinates(x, y) {
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


function mapCursorPos(x,y) {
    /**
     * Update the page with the selected feedback/injection position.
     */
    coords = mapCoordinates(x, y);
    $('#map_coords').css('display', 'inline');
    $('#injection_coord').html(BDKD.injection_values[coords.injection] +
            " (" + coords.injection + ")");
    $('#feedback_coord').html(BDKD.feedback_values[coords.feedback] + 
            " (" + coords.feedback + ")");
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
    /**
     * Get a time series pixel's X position within the selectable range.
     */
    x -= BDKD.TIME_SERIES_LEFT_OFFSET_PX;
    if ( x < 0 ) x = 0;
    if ( x > BDKD.TIME_SERIES_WIDTH_PX ) x = BDKD.TIME_SERIES_WIDTH_PX;
    return x;
};


function timeSeriesPxToTimeRange(x1, x2) {
    /**
     * Convert a pixel X range to a time range.
     */
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


$(document).ready(function() {
    onChangeDataset();
});
