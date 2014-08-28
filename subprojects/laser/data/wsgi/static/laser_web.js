BDKD.TIME_SERIES_LEFT_OFFSET_PX = 81;
BDKD.TIME_SERIES_WIDTH_PX = 495;
BDKD.TIME_SERIES_RIGHT_PX = (BDKD.TIME_SERIES_LEFT_OFFSET_PX + 
        BDKD.TIME_SERIES_WIDTH_PX);
BDKD.TIME_SERIES_HEIGHT_PX = 480;


function datasetUrl() {
    /**
     * Get the path of the current dataset.
     */

    return('/repositories/' + BDKD.dataset.repository_name +
        '/datasets/' + BDKD.dataset.dataset_name);
};


function mapNamesUrl() {
    return( datasetUrl() + '/map_names');
};


function mapDataUrl(map_name) {
    return( datasetUrl() + '/map_data/' + map_name );
};


function readmeUrl() {
    return( datasetUrl() + '/readme' );
};

function timeSeriesUrl(request_type) {
    return (datasetUrl() +
            '/' + request_type + '?' +
            'x=' + BDKD.selection.x_index + '&' +
            'y=' + BDKD.selection.y_index + '&' +
            'from=' + BDKD.selection.from_time + '&' +
            'to=' + BDKD.selection.to_time
           );
};
    

function timeSeriesDataUrl() {
    return timeSeriesUrl('time_series_data');
};


function timeSeriesPlotUrl() {
    return timeSeriesUrl('time_series_plots');
};


function phasePlotUrl(phase_delay) {
    return ( timeSeriesUrl('phase_plots') +
            '&delay=' + phase_delay );
};


function fftDataUrl() {
    return timeSeriesUrl('fft_data');
};


function fftPlotUrl() {
    return timeSeriesUrl('fft_plots');
};


function onPageLoad() {
    onChangeDataset();
};


function onChangeDataset() {
    updateMapList();
    updateReadme();
};


function selectTimeSeries(x, y) {
    BDKD.selection.x_index = x;
    BDKD.selection.y_index = y;
    BDKD.selection.from_time = 0;
    BDKD.selection.to_time = (BDKD.dataset.z_size * BDKD.dataset.z_interval_base
            -1);
    onChangeTimeSeries();
}


function hoverValue(x_index, x_value, y_index, y_value, value) {
    tooltip = d3.select("div#tooltip");
    tooltip.transition()
        .duration(200)      
        .style("opacity", .9);      
    tooltip.html(
            "X[" + x_index + "]: " + x_value + "<br/>" + 
            "Y[" + y_index + "]: " + y_value + "<br/>" + 
            "Value: " + value)  
        .style("left", (d3.event.pageX) + "px")     
        .style("top", (d3.event.pageY - 42) + "px");    
};


function clearHeatMap() {
    $('#heatmap_display').hide();
    $('#heatmap_spinner').show();

    d3.select("svg#heatmap")
        .attr("width", 0)
        .attr("height", 0)
        .selectAll("*").remove();

    d3.select("div#tooltip")   
        .style("opacity", 0);
};


function drawHeatMap(dataset) {
    heatmap = d3.select("svg#heatmap");

    /* Ensure tooltip exists */
    tooltip = d3.select("div#tooltip");
    if ( tooltip.empty() ) {
        tooltip = d3.select("body").append("div")   
            .attr("id", "tooltip")
            .attr("class", "tooltip")               
            .style("opacity", 0);
    }

    min_value = max_value = max_x = max_y = null;
    for ( i = 0; i < dataset.length; i++ ) {
        if ( min_value == null || dataset[i].value < min_value ) {
            min_value = dataset[i].value;
        }
        if ( max_value == null || dataset[i].value > max_value ) {
            max_value = dataset[i].value;
        }
        if ( max_x == null || dataset[i].x_index > max_x ) {
            max_x = dataset[i].x_index;
        }
        if ( max_y == null || dataset[i].y_index > max_y ) {
            max_y = dataset[i].y_index;
        }
    };

    heatmap
        .attr("width", (max_x + 1) * 3)
        .attr("height", (max_y + 1) * 3)
        .selectAll("rect")
        .data(dataset)    
        .enter().append("rect")
        .attr("x", function(d) { return d.x_index * 3; })
        .attr("y", function(d) { return d.y_index * 3; })
        .attr("width", 3)
        .attr("height", 3)
        .attr("fill", function(d) {
            return "hsl(" + 
                ((d.value - min_value) / (max_value - min_value) * 360)
            .toString() + ",100%, 50%)"; 
        })
        .on("mouseover", function(d) { 
            hoverValue(d.x_index, d.x_variable, d.y_index, d.y_variable, 
                d.value); 
        })
        .on("click", function(d) { 
            selectTimeSeries(d.x_index, d.y_index); 
        })
    ;
    $('#heatmap_spinner').hide();
    $('#heatmap_display').show();
};


function onChangeMap() {
    clearHeatMap();
    $.ajax({url: mapDataUrl($('#map').val()),
            context: document.body,
            success: function(data) {
                dataset = JSON.parse(data);
                drawHeatMap(dataset);
            }
    });
};


function onChangeTimeSeries() {
    /**
     * Invoked when the user changes the current time series.
     *
     * The from/to times are reset to the defaults (0 - 999999).
     */
    /*
    BDKD.injection = $('#map_injection').val();
    BDKD.feedback = $('#map_feedback').val();
    BDKD.from_time = 0;
    BDKD.to_time = 999999;
    */
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
    BDKD.selection.from_time = parseInt($('#from_time').val());
    BDKD.selection.to_time = parseInt($('#to_time').val());

    updateTimeSeries();
    updatePhaseDiagram();
    updateFFTDiagram();
};


function onResetZoomTimeSeries() {
    /**
     * Invoked when the user resets the current zoom of the time series (resets
     * to 0 - 999999).
     */
    BDKD.selection.from_time = 0;
    BDKD.selection.to_time = (BDKD.dataset.z_size * 
            BDKD.dataset.z_interval_base -1);

    updateTimeSeries();
    updatePhaseDiagram();
    updateFFTDiagram();
};


function onChangePhaseDelay() {
    updatePhaseDiagram();
};


function updateTimeSeries() {
    $('#time_series_plot').replaceWith(
            "<img id='time_series_plot' width=640 height=480 src='" + 
            timeSeriesPlotUrl() + "' />");
    if ( BDKD.ias ) 
        BDKD.ias.setOptions({ hide: true });
    BDKD.ias = $('#time_series_plot').imgAreaSelect({ 
        minHeight: BDKD.TIME_SERIES_HEIGHT_PX, 
        maxHeight: BDKD.TIME_SERIES_HEIGHT_PX, 
        onSelectChange: updateTimeSeriesZoom, 
        instance: true });
    $('#from_time').val(BDKD.selection.from_time);
    $('#to_time').val(BDKD.selection.to_time);
    $('#time_series_download').html('Data: <a href="' + timeSeriesDataUrl() + 
            '">' + timeSeriesDataUrl() + '</a>');
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
    var phase_delay = parseInt($('#phase_delay').val());
    var plot_src = phasePlotUrl(phase_delay);
    $('#phase_plot').replaceWith(
            "<img id='phase_plot' width=640 height=480 src='" +
            phasePlotUrl(phase_delay) + "' />");
};


function updateFFTDiagram() {
    $('#fft_download').html(
            'Data: <a href="' + fftDataUrl() + '">' + fftDataUrl() + '</a>'); 
    $('#fft_plot').replaceWith("<img id='fft_plot' width=640 height=480 src='" +
            fftPlotUrl() + "' />");
};


function updateMapList() {
    var map_options = '';
    $.ajax({url: mapNamesUrl(),
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


function updateReadme() {
    $.ajax({url: readmeUrl(),
            context: document.body,
            success: function(data) {
                $('#readme').html(data);
            }
    });
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
    var range = BDKD.selection.to_time - BDKD.selection.from_time;
    from_time = BDKD.selection.from_time + Math.floor(
            Math.floor(range * x1 / BDKD.TIME_SERIES_WIDTH_PX) / BDKD.dataset.z_interval_base
            ) * BDKD.dataset.z_interval_base;
    to_time = BDKD.selection.from_time + Math.ceil(
            Math.ceil(range * x2 / BDKD.TIME_SERIES_WIDTH_PX) / BDKD.dataset.z_interval_base
            ) * BDKD.dataset.z_interval_base - 1;
    return {from_time: from_time, to_time: to_time};
};

