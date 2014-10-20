BDKD.MAP_SCALE=1;
BDKD.MAP_X_AXIS_OFFSET=104;
BDKD.MAP_X_AXIS_LABEL=64;
BDKD.MAP_Y_AXIS_OFFSET=104;
BDKD.MAP_Y_AXIS_LABEL=16;
BDKD.MAP_BORDER=12;

BDKD.TIME_SERIES_LEFT_OFFSET_PX = 51;
BDKD.TIME_SERIES_WIDTH_PX = 309;
BDKD.TIME_SERIES_RIGHT_PX = (BDKD.TIME_SERIES_LEFT_OFFSET_PX + 
        BDKD.TIME_SERIES_WIDTH_PX);
BDKD.TIME_SERIES_HEIGHT_PX = 300;

BDKD.ZOOM_SIZE = 15;
BDKD.ZOOM_SCALE = 10;

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


function isPositiveInteger(n) {
    return n >>> 0 == parseFloat(n);
};


function getFieldIntValue(selector, description, min_val, max_val, default_val) {
    var field_element = $(selector);
    var field_str = field_element.val()
    var field_val = -1;
    var success = false;
    if ( isPositiveInteger(field_str) ) {
        field_val = Number(field_str);
        if ( field_val < min_val || field_val > max_val ) {
            alert(description + " value out of range");
        }
        else {
            success = true;
        }
    }
    else {
        alert(description + " is not an integer");
    }
    if ( ! success ) {
        field_val = default_val;
        field_element.val(field_val.toString());
    }
    return field_val;
};


function getMapXIndex() {
    return getFieldIntValue('#map_x', BDKD.dataset.x_name, 
            BDKD.map_data.min_x, 
            BDKD.map_data.max_x, 
            BDKD.map_data.min_x);
};


function setMapXIndex(x_index) {
    $('#map_x').val(x_index.toString());
    updateMapInputs();
};


function getMapYIndex() {
    return getFieldIntValue('#map_y', BDKD.dataset.y_name, 
            BDKD.map_data.min_y, 
            BDKD.map_data.max_y, 
            BDKD.map_data.min_y);
};


function setMapYIndex(y_index) {
    $('#map_y').val(y_index.toString());
    updateMapInputs();
};


function onSelectTimeSeries() {
    selectTimeSeries(getMapXIndex(), getMapYIndex());
};


function selectTimeSeries(x, y) {
    BDKD.selection.x_index = x;
    BDKD.selection.y_index = y;
    BDKD.selection.from_time = 0;
    BDKD.selection.to_time = (BDKD.dataset.z_size * BDKD.dataset.z_interval_base
            -1);
    onChangeTimeSeries();
};


function updateMapInputs() {
    var x_index = getMapXIndex();
    var y_index = getMapYIndex();
    var xy_data = BDKD.map_data.data[x_index][y_index];
    $('#map_x_range').html("(" + BDKD.map_data.min_x.toString() + " .. " +
            BDKD.map_data.max_x.toString() + ")");
    $('#map_y_range').html("(" + BDKD.map_data.min_y.toString() + " .. " +
            BDKD.map_data.max_y.toString() + ")");
    $('#x_variable').html(xy_data.x_variable.toString());
    $('#y_variable').html(xy_data.y_variable.toString());
}

function getHeatmapSelection(x_index, y_index) {
    var x_size = BDKD.heatmap.x_columns[0].length;
    var y_size = BDKD.heatmap.x_columns[0][0].__data__.length;
    var offset = Math.floor(BDKD.ZOOM_SIZE / 2);
    var x_left = (x_index - offset) < 0 ? 0 : (x_index - offset);
    var x_right = x_left + BDKD.ZOOM_SIZE;
    if ( x_right > x_size ) {
        x_right = x_size;
        x_left = x_size - BDKD.ZOOM_SIZE;
    }
    var y_top = (y_index - offset) < 0 ? 0 : (y_index - offset);
    var y_bottom = y_top + BDKD.ZOOM_SIZE;
    if ( y_bottom > y_size ) {
        y_bottom = y_size;
        y_top = y_size - BDKD.ZOOM_SIZE;
    }
    var heatmap_data = [];
    for ( x = x_left; x < x_right; x++ ) {
        col_data = BDKD.heatmap.x_columns[0][x].__data__;
        col = [];
        for ( y = y_top; y < y_bottom; y++ ) {
            col.push(col_data[y]);
        }
        heatmap_data.push(col);
    }
    BDKD.heatmap_data = heatmap_data;
    return heatmap_data;
};


function updateHeatmapZoom(x_index, y_index) {
    var heatmap_data = getHeatmapSelection(x_index, y_index);
    var zoom = d3.select("svg#heatmap_zoom");

    zoom
        .attr("width", BDKD.ZOOM_SIZE * BDKD.ZOOM_SCALE)
        .attr("height", BDKD.ZOOM_SIZE * BDKD.ZOOM_SCALE)
        ;

    // Add a vertical group for each X
    zoom.x_columns = zoom.selectAll('g')
        .data(heatmap_data)
        .enter()
        .append("g")
        .attr("transform", function(d, i) {
            return "translate(" + (i * BDKD.ZOOM_SCALE) + 
            "," + 0 + ")";
        })
        .attr("width", BDKD.ZOOM_SCALE)
        .attr("height", BDKD.ZOOM_SIZE * BDKD.ZOOM_SCALE)
        ;

    // Add rectangles for each Y
    zoom.x_columns.selectAll('rect')
        .data( function(d) { return d; })
        .enter()
        .append('rect')
            .attr("y", function(d, i) { return i * BDKD.ZOOM_SCALE; })
            .attr("width", BDKD.ZOOM_SCALE -1)
            .attr("height", BDKD.ZOOM_SCALE -1)
            .attr("fill", function(d) {
                return "hsl(" + 
                    ((d.value - BDKD.map_data.min_value) / 
                     (BDKD.map_data.max_value - BDKD.map_data.min_value) * 360)
                .toString() + ",100%, 50%)"; 
            })
            .attr("class", function(d) {
                // CSS styling for selected & surrounding pixels
                if ( d.x_index == x_index && d.y_index == y_index ) {
                    return "zoom_selected";
                }
                else {
                    return "zoom";
                }
            })
    ;
};


function hoverValue(x_index, x_value, y_index, y_value, value) {
    var tooltip = d3.select("div#tooltip");
    tooltip
        .attr("width", BDKD.ZOOM_SIZE * BDKD.ZOOM_SCALE)
        .attr("height", BDKD.ZOOM_SIZE * BDKD.ZOOM_SCALE + 24)
        ;
    
    tooltip.transition()
        .duration(200)      
        .style("opacity", 1.0);
    tooltip.html(
            "<svg id='heatmap_zoom'></svg>" +
            "<div>" +
            "X[" + x_index + "]: " + x_value + "<br/>" + 
            "Y[" + y_index + "]: " + y_value + "<br/>" + 
            "Value: " + value +
            "</div>")  
        .style("left", (d3.event.pageX + BDKD.ZOOM_SIZE) + "px")     
        .style("top", (d3.event.pageY - (BDKD.ZOOM_SIZE * BDKD.ZOOM_SCALE / 2)) + "px");
    updateHeatmapZoom(x_index, y_index);
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


function drawHeatMapAxes(heatmap) {

    // Axes scales: domain based on indexes because the variables are 
    // non-linear
    var xAxisScale = d3.scale.linear()
        .domain([0, BDKD.map_data.max_x])
        .range([0, BDKD.map_data.max_x * BDKD.MAP_SCALE]);

    var yAxisScale = d3.scale.linear()
        .domain([0, BDKD.map_data.max_y])
        .range([0, BDKD.map_data.max_y * BDKD.MAP_SCALE]);
    //Create the Axes
    var xAxis = d3.svg.axis()
        .scale(xAxisScale)
        .orient('bottom')
        .tickFormat(function(d, i) {
            // Look up variable based on x index d
            return BDKD.map_data.data[d][BDKD.map_data.max_y].x_variable;
        });
    var yAxis = d3.svg.axis()
        .scale(yAxisScale)
        .orient('left')
        .tickFormat(function(d, i) {
            // Look up variable based on y index d
            return BDKD.map_data.data[0][d].y_variable;
        });
    // Append X axis
    heatmap
        .append("g")
        .call(xAxis)
        .attr("class", "x axis")
        .attr("transform", "translate(" + (BDKD.MAP_Y_AXIS_OFFSET -1) + ", " + 
                ((BDKD.map_data.max_y + 1) * BDKD.MAP_SCALE + BDKD.MAP_BORDER + 1) 
                + ")")
        .attr("width", (BDKD.map_data.max_x + 1) * BDKD.MAP_SCALE)
        .selectAll("text")
        .style("text-anchor", "end")
        .attr("dx", "-.5em")
        .attr("dy", "-.5em")
        .attr("transform", function(d) {
            return "rotate(-90)"
        })
        ;
    // X axis label
    heatmap
        .append("text")
        .attr("x", ((BDKD.map_data.max_x + 1) / 2 * BDKD.MAP_SCALE) +
                BDKD.MAP_Y_AXIS_OFFSET)
        .attr("y", ((BDKD.map_data.max_y + 1) * BDKD.MAP_SCALE +
                    BDKD.MAP_BORDER + BDKD.MAP_X_AXIS_LABEL))
        .style("text-anchor", "middle")
        .text(BDKD.dataset.x_name)
        ;
    // Append Y axis
    heatmap
        .append("g")
        .call(yAxis)
        .attr("class", "y axis")
        .attr("transform", "translate(" + (BDKD.MAP_Y_AXIS_OFFSET -1) + ", " + 
                (BDKD.MAP_BORDER) + ")")
        .attr("height", (BDKD.map_data.max_y + 1) * BDKD.MAP_SCALE)
        .selectAll("text")
        ;
    // Y axis label
    heatmap
        .append("text")
        .attr("transform", "rotate(-90)")
        .attr("x", -(((BDKD.map_data.max_y + 1) * BDKD.MAP_SCALE)/2 +
                    BDKD.MAP_BORDER))
        .attr("y", BDKD.MAP_Y_AXIS_LABEL)
        .style("text-anchor", "middle")
        .text(BDKD.dataset.y_name)
        ;
};


function drawHeatMap(map_data) {

    /* Ensure tooltip exists */
    var tooltip = d3.select("div#tooltip");
    if ( tooltip.empty() ) {
        tooltip = d3.select("body").append("div")   
            .attr("id", "tooltip")
            .attr("class", "tooltip")               
            .style("opacity", 0);
    }

    BDKD.heatmap = d3.select("svg#heatmap");
    BDKD.heatmap
        .attr("width", (BDKD.map_data.max_x + 1) * BDKD.MAP_SCALE + 
                BDKD.MAP_Y_AXIS_OFFSET + BDKD.MAP_BORDER)
        .attr("height", (BDKD.map_data.max_y + 1) * BDKD.MAP_SCALE + 
                BDKD.MAP_X_AXIS_LABEL + (BDKD.MAP_BORDER * 2))
        ;

    // Add a vertical group for each X
    BDKD.heatmap.x_columns = BDKD.heatmap.selectAll('g')
        .data(BDKD.map_data.data)
        .enter()
        .append("g")
        .attr("transform", function(d, i) {
            return "translate(" + (i * BDKD.MAP_SCALE + BDKD.MAP_Y_AXIS_OFFSET) + 
            "," + BDKD.MAP_BORDER + ")";
        })
        .attr("width", BDKD.MAP_SCALE)
        .attr("height", (BDKD.map_data.max_y + 1) * BDKD.MAP_SCALE)
        ;

    // Add rectangles for each Y
    BDKD.heatmap.x_columns.selectAll('rect')
        .data( function(d) { return d; })
        .enter()
        .append('rect')
            .attr("y", function(d, i) { return i * BDKD.MAP_SCALE; })
            .attr("width", BDKD.MAP_SCALE)
            .attr("height", BDKD.MAP_SCALE)
            .attr("fill", function(d) {
                return "hsl(" +
                    ((d.value - BDKD.map_data.min_value) / 
                     (BDKD.map_data.max_value - BDKD.map_data.min_value) * 360)
                .toString() + ",100%, 50%)"; 
            })
            .on("mouseover", function(d) { 
                tooltip.style("visibility", "visible");
                hoverValue(d.x_index, d.x_variable, d.y_index, d.y_variable, 
                    d.value); 
            })
            .on("mouseout", function(d) {
                tooltip.style("visibility", "hidden");
            })
            .on("click", function(d) { 
                setMapXIndex(d.x_index);
                setMapYIndex(d.y_index);
                selectTimeSeries(d.x_index, d.y_index); 
            })
    ;
    // Draw axes on the heatmap
    drawHeatMapAxes(BDKD.heatmap, BDKD.map_data);
    updateMapInputs();

    // Ready to show
    $('#heatmap_spinner').hide();
    $('#heatmap_display').show();
};


function getMapData(raw_map_data) {

    var data = [];  // Alternative packing of data as 2D array
    min_value = max_value = min_x = max_x = min_y = max_y = null;
    for ( i = 0; i < raw_map_data.length; i++ ) {
        var item = raw_map_data[i];
        if ( min_value == null || item.value < min_value ) {
            min_value = item.value;
        }
        if ( max_value == null || item.value > max_value ) {
            max_value = item.value;
        }
        if ( min_x == null || item.x_index < min_x ) {
            min_x = item.x_index;
        }
        if ( max_x == null || item.x_index > max_x ) {
            max_x = item.x_index;
        }
        if ( min_y == null || item.y_index < min_y ) {
            min_y = item.y_index;
        }
        if ( max_y == null || item.y_index > max_y ) {
            max_y = item.y_index;
        };
        data[item.x_index] = (data[item.x_index] || []);
        data[item.x_index][item.y_index] = item;
    };
    // Assign colours to each item
    for ( var x=0; x < max_x; x++ ) {
        for ( var y=0; y < max_y; y++ ) {
            data[x][y].colour = ((data[x][y].value - min_value) / 
                     (max_value - min_value) * 360);
        }
    }
    return {min_value : min_value,
        max_value : max_value,
        min_x : min_x,
        max_x : max_x,
        min_y : min_y,
        max_y : max_y,
        data : data
    };
};



function onChangeMap() {
    clearHeatMap();
    $.ajax({url: mapDataUrl($('#map').val()),
            context: document.body,
            success: function(data) {
                raw_map_data = JSON.parse(data);
                BDKD.map_data = getMapData(raw_map_data);
                drawHeatMap();
            }
    });
};


function onChangeTimeSeries() {
    /**
     * Invoked when the user changes the current time series.
     *
     * The from/to times are reset to the defaults (0 - 999999).
     */
    $('#time_series_container').css('display', 'block');
    $('#phase_container').css('display', 'block');
    $('#fft_container').css('display', 'block');
    updateTimeSeries();
    updatePhaseDiagram();
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
            "<img id='time_series_plot' width=400 height=300 src='" + 
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
            '">download</a>');
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
            "<img id='phase_plot' width=400 height=300 src='" +
            phasePlotUrl(phase_delay) + "' />");
};


function updateFFTDiagram() {
    $('#fft_download').html(
            'Data: <a href="' + fftDataUrl() + '">download</a>'); 
    $('#fft_plot').replaceWith("<img id='fft_plot' width=400 height=300 src='" +
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
                selectTimeSeries(0, 0);
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

