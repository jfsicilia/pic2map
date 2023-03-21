// Avoid jslint errors for known globals
/*global L*/
var LocationMap = {
  'initialize': function initialize(elementId, initialCenter) {
    this.map = L.map(elementId).setView(initialCenter, 3);
    this.markerCluster = L.markerClusterGroup();

    L.tileLayer('http://{s}.tile.osm.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(this.map);
    this.map.addLayer(this.markerCluster);
  },
  'addMarkers': function addMarkers(markersData) {
    console.log('Adding ' + markersData.length + ' markers');
    markersData.forEach(function(markerData) {
        var marker = L.marker([markerData.latitude, markerData.longitude]);
        var text = '<b>Filename:</b> ' + markerData.filename;
        if (markerData.datetime) {
          text += '<br><b>GPS datetime:</b> ' + markerData.datetime;
        }
        text += '<img width="100% !important" src="/get_image?filename=' + encodeURIComponent(markerData.filename) + '" />'

        marker.bindPopup(text, {maxWidth: 700});
        this.markerCluster.addLayer(marker);
    }, this);
  }
};
