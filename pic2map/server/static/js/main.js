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
    console.log(markersData);
    markersData.forEach(function(markerData) {
        let marker = L.marker([markerData.latitude, markerData.longitude]);
        let filename = markerData.filepath.split('/').pop();
        let text = `<a href="image?id=${markerData.id}"><img alt="${filename}" src="image?id=${markerData.id}" width="200px"/></a>`;

        text += `<br>Album: <b>${markerData.album}</b>`;
        text += `<br>File: <b>${filename}</b>`;
        if (markerData.datetime) {
          text += `<br>GPS datetime <b>${markerData.datetime}</b>`;
        }

        marker.bindPopup(text);
        this.markerCluster.addLayer(marker);
    }, this);
  }
};
